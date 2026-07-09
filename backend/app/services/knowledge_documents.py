"""Knowledge document processing — extract text, chunk, and generate draft
KnowledgeItems from an uploaded .txt / .md file (P6).

No embeddings / vectors here — this is the structured-ingest stage that feeds the
existing Knowledge Engine. Generated items are always draft + source_type=external_doc,
so Context Builder (active-only) is never affected until a human reviews them.
"""

import os
import re
from sqlalchemy.orm import Session
from app.config import settings
from app.models import KnowledgeDocument, KnowledgeItem, KnowledgeSource
from app.services.events import record_event
from app.services.knowledge_document_storage import save_knowledge_document_file

SUPPORTED_EXTS = {".txt": "text_v1", ".md": "markdown_text_v1"}
EXTERNAL_DOC_SOURCE_NAME = "外部文档"

MAX_CHUNK_CHARS = 1200
OVERLAP_CHARS = 120
MIN_CHUNK_CHARS = 40

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")


def extract_text_from_upload(filename: str, content_type: str | None, content_bytes: bytes) -> tuple[str, str]:
    """Return (parser_name, text). Raises ValueError for unsupported/empty/non-UTF-8 input."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in SUPPORTED_EXTS:
        raise ValueError(f"Unsupported file type: {ext or 'unknown'} (only .txt / .md)")
    if not content_bytes:
        raise ValueError("File is empty")
    if len(content_bytes) > settings.knowledge_document_max_size_bytes:
        raise ValueError(f"File exceeds {settings.knowledge_document_max_size_mb}MB limit")
    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("File is not valid UTF-8 text")
    if not text.strip():
        raise ValueError("File is empty")
    return SUPPORTED_EXTS[ext], text


def _derive_title(content: str) -> str:
    stripped = content.strip()
    first = stripped.splitlines()[0] if stripped else ""
    first = re.sub(r"^#{1,6}\s*", "", first).strip()
    return first[:60] or "文档片段"


def _split_by_headings(text: str) -> list[tuple[str | None, str]]:
    """Split into (title, section_text) on markdown headings (#/##/###).
    Returns [] if no headings found. Section text includes its heading line."""
    sections: list[tuple[str | None, list[str]]] = []
    cur_title: str | None = None
    cur_lines: list[str] = []
    found = False
    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            found = True
            if cur_lines or cur_title is not None:
                sections.append((cur_title, cur_lines))
            cur_title = m.group(2).strip()
            cur_lines = [line]
        else:
            cur_lines.append(line)
    if cur_lines or cur_title is not None:
        sections.append((cur_title, cur_lines))
    if not found:
        return []
    return [(t, "\n".join(ls)) for t, ls in sections]


def _split_by_length(text: str) -> list[tuple[str | None, str]]:
    text = text.strip()
    chunks: list[tuple[str | None, str]] = []
    start, n = 0, len(text)
    while start < n:
        end = min(start + MAX_CHUNK_CHARS, n)
        chunks.append((None, text[start:end]))
        if end >= n:
            break
        start = end - OVERLAP_CHARS
    return chunks


def chunk_document(text: str) -> list[dict]:
    raw = _split_by_headings(text) or _split_by_length(text)
    result: list[dict] = []
    idx = 0
    for title, section in raw:
        content = section.strip()
        if len(content) < MIN_CHUNK_CHARS:
            continue
        summary = re.sub(r"^#{1,6}\s*", "", content).strip().replace("\n", " ")[:120]
        result.append({
            "title": (title or _derive_title(content))[:255],
            "summary": summary,
            "content_markdown": content,
            "chunk_index": idx,
        })
        idx += 1
    return result


def _ensure_external_doc_source(db: Session, workspace_id: str) -> KnowledgeSource:
    src = db.query(KnowledgeSource).filter(
        KnowledgeSource.workspace_id == workspace_id,
        KnowledgeSource.name == EXTERNAL_DOC_SOURCE_NAME,
    ).first()
    if src:
        return src
    src = KnowledgeSource(workspace_id=workspace_id, name=EXTERNAL_DOC_SOURCE_NAME,
                          description="文档上传自动生成的知识来源")
    db.add(src)
    db.flush()
    return src


def process_uploaded_knowledge_document(
    db: Session, workspace_id: str, filename: str, content_type: str | None, content_bytes: bytes,
) -> dict:
    """Full ingest: create document → extract → save → chunk → draft items.

    Never raises for bad input: records a failed KnowledgeDocument + event and
    returns {"ok": False, "error": ...}. The caller (API) commits and returns 422.
    """
    ext = os.path.splitext(filename or "")[1].lower()
    doc = KnowledgeDocument(
        workspace_id=workspace_id,
        filename=os.path.basename(filename or "upload"),
        content_type=content_type,
        file_ext=ext,
        storage_path="",
        status="uploaded",
    )
    db.add(doc)
    db.flush()

    try:
        # Validate BEFORE touching disk — invalid uploads never get written.
        parser, text = extract_text_from_upload(filename, content_type, content_bytes)

        storage_path = save_knowledge_document_file(workspace_id, doc.id, filename, content_bytes)
        doc.storage_path = storage_path
        doc.parser = parser
        doc.status = "processing"
        db.flush()

        source = _ensure_external_doc_source(db, workspace_id)
        doc.source_id = source.id

        chunks = chunk_document(text)
        if not chunks:
            raise ValueError("No extractable content in document")

        items = []
        for ch in chunks:
            item = KnowledgeItem(
                workspace_id=workspace_id, source_id=source.id,
                title=ch["title"], summary=ch["summary"], content_markdown=ch["content_markdown"],
                source_type="external_doc", status="draft",
                metadata_json={"document_id": doc.id, "chunk_index": ch["chunk_index"]},
            )
            db.add(item)
            items.append(item)
        db.flush()

        doc.item_count = len(items)
        doc.text_excerpt = text[:500]
        doc.status = "processed"

        record_event(
            db, workspace_id=workspace_id, type="knowledge_document.processed", source="knowledge_api",
            subject_type="knowledge_document", subject_id=doc.id,
            title=f"文档已解析: {doc.filename}",
            payload_json={"document_id": doc.id, "filename": doc.filename,
                          "item_count": len(items), "parser": parser},
        )
        return {"ok": True, "document": doc, "items": items}

    except ValueError as exc:
        doc.status = "failed"
        doc.error_message = str(exc)
        record_event(
            db, workspace_id=workspace_id, type="knowledge_document.failed", source="knowledge_api",
            subject_type="knowledge_document", subject_id=doc.id,
            title=f"文档解析失败: {doc.filename}",
            payload_json={"document_id": doc.id, "filename": doc.filename, "error": str(exc)},
        )
        return {"ok": False, "document": doc, "items": [], "error": str(exc)}


def list_knowledge_documents(db: Session, workspace_id: str) -> list[KnowledgeDocument]:
    return db.query(KnowledgeDocument).filter(
        KnowledgeDocument.workspace_id == workspace_id,
    ).order_by(KnowledgeDocument.created_at.desc()).all()


def get_knowledge_document_or_none(db: Session, workspace_id: str, document_id: str) -> KnowledgeDocument | None:
    return db.query(KnowledgeDocument).filter(
        KnowledgeDocument.id == document_id, KnowledgeDocument.workspace_id == workspace_id,
    ).first()
