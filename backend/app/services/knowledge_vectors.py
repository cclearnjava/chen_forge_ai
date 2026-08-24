"""Knowledge Vector Service — content hash, index, reindex, vector search (P6.6).

All operations are workspace-scoped. draft / archived items are never indexed.
Vector search uses Python cosine similarity over JSON-stored vectors (SQLite-friendly).
Production pgvector replaces `search_vectors` internally — the caller contract stays the same.
"""

import hashlib
import math
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.models import KnowledgeItem, KnowledgeVector
from app.services.embedding_provider import (
    EmbeddingProviderError, embed_text, get_embedding_provider,
)


# ── vector store selection (P6.8) ──

def _is_pgvector_mode() -> bool:
    return settings.vector_store == "pgvector"


def _dialect_name(db: Session) -> str:
    return db.get_bind().dialect.name


def _validate_pgvector_config(db: Session) -> None:
    """Fail-fast on pgvector misconfiguration. Raises ValueError with a clear, secret-free message."""
    dialect = _dialect_name(db)
    if dialect != "postgresql":
        raise ValueError(f"VECTOR_STORE=pgvector requires PostgreSQL (current dialect: {dialect})")
    if settings.embedding_dim <= 0:
        raise ValueError("VECTOR_STORE=pgvector requires EMBEDDING_DIM > 0")


def _vector_to_pg_literal(vec: list[float]) -> str:
    """Render a float list as a pgvector text literal: [0.1,0.2,0.3]."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def _upsert_failed_vector(db: Session, workspace_id: str, item_id: str, provider, error_msg: str) -> KnowledgeVector:
    vec = db.query(KnowledgeVector).filter(
        KnowledgeVector.workspace_id == workspace_id,
        KnowledgeVector.knowledge_item_id == item_id,
        KnowledgeVector.embedding_model == provider.model,
    ).first()
    if vec:
        vec.status = "failed"
        vec.error_message = error_msg[:500]
        vec.vector_json = None
        vec.indexed_at = None
    else:
        vec = KnowledgeVector(
            workspace_id=workspace_id,
            knowledge_item_id=item_id,
            provider=provider.name,
            embedding_model=provider.model,
            content_hash="",  # unknown for a failed index; overwritten on later success
            vector_dim=provider.dim or 0,
            status="failed",
            error_message=error_msg[:500],
        )
        db.add(vec)
    db.flush()
    return vec


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
    provider = get_embedding_provider()
    item = db.query(KnowledgeItem).filter(
        KnowledgeItem.id == item_id, KnowledgeItem.workspace_id == workspace_id,
    ).first()
    if not item:
        raise ValueError(f"Knowledge item {item_id} not found")

    vec = db.query(KnowledgeVector).filter(
        KnowledgeVector.workspace_id == workspace_id,
        KnowledgeVector.knowledge_item_id == item_id,
        KnowledgeVector.embedding_model == get_embedding_provider().model,
    ).first()

    if not vec:
        return {
            "knowledge_item_id": item_id,
            "status": "not_indexed",
            "provider": None, "embedding_model": None,
            "vector_dim": None, "content_hash": None,
            "stale": False, "indexed_at": None, "error_message": None,
            "vector_store": settings.vector_store,
        }

    stale = vec.content_hash != compute_content_hash(item) if vec.status == "indexed" else False
    return {
        "knowledge_item_id": item_id,
        "status": "stale" if stale else vec.status,
        "provider": provider.name, "embedding_model": provider.model,
        "vector_dim": vec.vector_dim, "content_hash": vec.content_hash,
        "stale": stale, "indexed_at": vec.indexed_at, "error_message": vec.error_message,
        "vector_store": settings.vector_store,
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

    text_input = knowledge_item_embedding_text(item)
    if not text_input.strip():
        raise ValueError("Empty embedding text")

    provider = get_embedding_provider()

    # pgvector mode: fail-fast on misconfiguration before doing any work,
    # but persist a failed vector row so the error is visible in the UI.
    if _is_pgvector_mode():
        try:
            _validate_pgvector_config(db)
        except ValueError as exc:
            _upsert_failed_vector(db, workspace_id, item_id, provider, str(exc))
            raise

    try:
        vector = embed_text(text_input)
    except (ValueError, EmbeddingProviderError) as exc:
        # Write failed status so the error is visible in frontend vector badges
        _upsert_failed_vector(db, workspace_id, item_id, provider, str(exc))
        raise

    content_hash = compute_content_hash(item)
    pgvector_mode = _is_pgvector_mode()

    vec = db.query(KnowledgeVector).filter(
        KnowledgeVector.workspace_id == workspace_id,
        KnowledgeVector.knowledge_item_id == item_id,
        KnowledgeVector.embedding_model == provider.model,
    ).first()

    if vec:
        vec.provider = provider.name
        vec.content_hash = content_hash
        # sqlite_json keeps the JSON vector; pgvector stores it in embedding_vector instead
        vec.vector_json = None if pgvector_mode else vector
        vec.vector_dim = provider.dim or settings.embedding_dim
        vec.status = "indexed"
        vec.error_message = None
        vec.indexed_at = datetime.now(timezone.utc)
    else:
        vec = KnowledgeVector(
            workspace_id=workspace_id,
            knowledge_item_id=item_id,
            provider=provider.name,
            embedding_model=provider.model,
            content_hash=content_hash,
            vector_json=None if pgvector_mode else vector,
            vector_dim=provider.dim or settings.embedding_dim,
            status="indexed",
            indexed_at=datetime.now(timezone.utc),
        )
        db.add(vec)
    db.flush()

    if pgvector_mode:
        try:
            with db.begin_nested():
                _upsert_pgvector_embedding(db, vec.id, vector)
        except Exception as exc:
            msg = f"pgvector write failed: {exc}"
            _upsert_failed_vector(db, workspace_id, item_id, provider, msg)
            raise ValueError(msg) from exc
    return vec


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
                KnowledgeVector.embedding_model == get_embedding_provider().model,
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


def _upsert_pgvector_embedding(db: Session, vec_id: str, vector: list[float]) -> None:
    """Write the embedding into the Postgres-only `embedding_vector` column via raw SQL.

    The column is not declared in the ORM model (it does not exist on SQLite); it is
    created by scripts/setup_pgvector.py. We bind the vector as a text literal and cast.
    """
    db.execute(
        text("UPDATE knowledge_vectors SET embedding_vector = CAST(:v AS vector) WHERE id = :id"),
        {"v": _vector_to_pg_literal(vector), "id": vec_id},
    )


def _pgvector_search_sql() -> str:
    """SQL for pgvector nearest-neighbour search. Extracted for testability.

    Filters at the DB level by workspace / model / status and joins active items.
    No content_hash / stale filter — parity with the sqlite_json path (stale is a
    display concern computed in get_vector_status, not a search filter).
    """
    return (
        "SELECT kv.knowledge_item_id AS knowledge_item_id, "
        "1 - (kv.embedding_vector <=> CAST(:q AS vector)) AS score "
        "FROM knowledge_vectors kv "
        "JOIN knowledge_items ki ON ki.id = kv.knowledge_item_id "
        "WHERE kv.workspace_id = :ws "
        "AND kv.status = 'indexed' "
        "AND kv.embedding_model = :model "
        "AND kv.embedding_vector IS NOT NULL "
        "AND ki.workspace_id = :ws "
        "AND ki.status = 'active' "
        "ORDER BY kv.embedding_vector <=> CAST(:q AS vector) "
        "LIMIT :limit"
    )


def _search_pgvector(db: Session, workspace_id: str, query_vec: list[float], model: str, max_hits: int) -> list[dict]:
    rows = db.execute(
        text(_pgvector_search_sql()),
        {"q": _vector_to_pg_literal(query_vec), "ws": workspace_id, "model": model, "limit": max_hits},
    ).all()
    return [{"knowledge_item_id": r.knowledge_item_id, "score": float(r.score)} for r in rows if r.score and r.score > 0]


def search_vectors(
    db: Session,
    workspace_id: str,
    query_text: str,
    *,
    max_hits: int = 5,
) -> list[dict]:
    """Vector search over indexed KnowledgeVectors in the current workspace.

    Dispatches to pgvector (SQL nearest-neighbour) or sqlite_json (Python cosine)
    based on settings.vector_store. Any store-level failure returns an empty list so
    the Hybrid Retriever can fall back to keyword search and Sales Reply never breaks.
    Only the current provider/model's vectors participate; active-only, workspace-scoped.
    """
    if not query_text or not query_text.strip():
        return []

    try:
        query_vec = embed_text(query_text)
    except (ValueError, EmbeddingProviderError):
        return []

    model = get_embedding_provider().model

    if _is_pgvector_mode():
        try:
            return _search_pgvector(db, workspace_id, query_vec, model, max_hits)
        except Exception:
            # pgvector unavailable / misconfigured / query error → fallback keyword
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
        KnowledgeVector.embedding_model == model,
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
