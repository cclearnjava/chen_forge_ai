"""Knowledge Vector Service — content hash, index, reindex, vector search (P6.5).

All operations are workspace-scoped. draft / archived items are never indexed.
Vector search uses Python cosine similarity over JSON-stored vectors (SQLite-friendly).
Production pgvector replaces `search_vectors` internally — the caller contract stays the same.
"""

import hashlib
import math
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import KnowledgeItem, KnowledgeVector
from app.services.embedding_provider import embed_text, MOCK_MODEL, MOCK_PROVIDER_NAME


def knowledge_item_embedding_text(item: KnowledgeItem) -> str:
    """Concatenate the fields that contribute to the embedding vector."""
    parts = [
        item.title or "",
        item.summary or "",
        " ".join(item.tags_json) if item.tags_json else "",
        item.source_type or "",
        item.content_markdown or "",
    ]
    return " ".join(p for p in parts if p)


def compute_content_hash(item: KnowledgeItem) -> str:
    """Stable hash of the content-relevant fields. Changes when the item should be re-indexed."""
    raw = "|".join([
        item.title or "",
        item.summary or "",
        item.content_markdown or "",
        " ".join(item.tags_json) if item.tags_json else "",
        item.source_type or "",
        item.service_id or "",
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── status / upsert ──

def get_vector_status(db: Session, workspace_id: str, item_id: str) -> dict:
    """Return a status dict for one KnowledgeItem's vector metadata."""
    item = db.query(KnowledgeItem).filter(
        KnowledgeItem.id == item_id, KnowledgeItem.workspace_id == workspace_id,
    ).first()
    if not item:
        raise ValueError(f"Knowledge item {item_id} not found")

    vec = db.query(KnowledgeVector).filter(
        KnowledgeVector.workspace_id == workspace_id,
        KnowledgeVector.knowledge_item_id == item_id,
        KnowledgeVector.embedding_model == MOCK_MODEL,
    ).first()

    if not vec:
        return {
            "knowledge_item_id": item_id,
            "status": "not_indexed",
            "provider": None, "embedding_model": None,
            "vector_dim": None, "content_hash": None,
            "stale": False, "indexed_at": None, "error_message": None,
        }

    stale = vec.content_hash != compute_content_hash(item) if vec.status == "indexed" else False
    return {
        "knowledge_item_id": item_id,
        "status": "stale" if stale else vec.status,
        "provider": vec.provider, "embedding_model": vec.embedding_model,
        "vector_dim": vec.vector_dim, "content_hash": vec.content_hash,
        "stale": stale, "indexed_at": vec.indexed_at, "error_message": vec.error_message,
    }


def index_knowledge_item(db: Session, workspace_id: str, item_id: str) -> KnowledgeVector:
    """Index a single active KnowledgeItem. Raises ValueError for workspace/draft/archived."""
    item = db.query(KnowledgeItem).filter(
        KnowledgeItem.id == item_id, KnowledgeItem.workspace_id == workspace_id,
    ).first()
    if not item:
        raise ValueError(f"Knowledge item {item_id} not found or not in this workspace")
    if item.status != "active":
        raise ValueError(f"Knowledge item {item_id} is not active (status={item.status})")

    text = knowledge_item_embedding_text(item)
    if not text.strip():
        raise ValueError("Empty embedding text")

    try:
        vector = embed_text(text)
    except ValueError as exc:
        raise ValueError(str(exc))

    content_hash = compute_content_hash(item)

    vec = db.query(KnowledgeVector).filter(
        KnowledgeVector.workspace_id == workspace_id,
        KnowledgeVector.knowledge_item_id == item_id,
        KnowledgeVector.embedding_model == MOCK_MODEL,
    ).first()

    if vec:
        vec.provider = MOCK_PROVIDER_NAME
        vec.content_hash = content_hash
        vec.vector_json = vector
        vec.vector_dim = MOCK_MODEL_DIM
        vec.status = "indexed"
        vec.error_message = None
        vec.indexed_at = datetime.now(timezone.utc)
    else:
        vec = KnowledgeVector(
            workspace_id=workspace_id,
            knowledge_item_id=item_id,
            provider=MOCK_PROVIDER_NAME,
            embedding_model=MOCK_MODEL,
            content_hash=content_hash,
            vector_json=vector,
            vector_dim=MOCK_MODEL_DIM,
            status="indexed",
            indexed_at=datetime.now(timezone.utc),
        )
        db.add(vec)
    db.flush()
    return vec


MOCK_MODEL_DIM = 64


def reindex_active_knowledge(db: Session, workspace_id: str, limit: int = 100) -> dict:
    """Batch reindex active KnowledgeItems that are missing or stale."""
    items = db.query(KnowledgeItem).filter(
        KnowledgeItem.workspace_id == workspace_id,
        KnowledgeItem.status == "active",
    ).all()

    indexed, skipped, failed = 0, 0, 0
    for it in items:
        if indexed >= limit:
            break
        try:
            new_hash = compute_content_hash(it)
            vec = db.query(KnowledgeVector).filter(
                KnowledgeVector.workspace_id == workspace_id,
                KnowledgeVector.knowledge_item_id == it.id,
                KnowledgeVector.embedding_model == MOCK_MODEL,
            ).first()
            if vec and vec.status == "indexed" and vec.content_hash == new_hash:
                skipped += 1
                continue
            index_knowledge_item(db, workspace_id, it.id)
            indexed += 1
        except ValueError:
            failed += 1

    return {"indexed_count": indexed, "skipped_count": skipped, "failed_count": failed}


# ── vector search ──

def _cosine(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_vectors(
    db: Session,
    workspace_id: str,
    query_text: str,
    *,
    max_hits: int = 5,
) -> list[dict]:
    """Cosine-similarity vector search over indexed, non-stale KnowledgeVectors.

    Filters at the db level: only vectors in the current workspace whose corresponding
    KnowledgeItem is active and not archived. Returns list of {knowledge_item_id, score}.
    """
    if not query_text or not query_text.strip():
        return []

    try:
        query_vec = embed_text(query_text)
    except ValueError:
        return []

    active_ids = {
        it.id for it in db.query(KnowledgeItem).filter(
            KnowledgeItem.workspace_id == workspace_id,
            KnowledgeItem.status == "active",
        ).all()
    }
    if not active_ids:
        return []

    vectors = db.query(KnowledgeVector).filter(
        KnowledgeVector.workspace_id == workspace_id,
        KnowledgeVector.status == "indexed",
        KnowledgeVector.embedding_model == MOCK_MODEL,
        KnowledgeVector.knowledge_item_id.in_(active_ids),
    ).all()

    scored = []
    for v in vectors:
        if not v.vector_json:
            continue
        sim = _cosine(query_vec, v.vector_json)
        if sim > 0:
            scored.append({"knowledge_item_id": v.knowledge_item_id, "score": sim})

    scored.sort(key=lambda h: -h["score"])
    return scored[:max_hits]
