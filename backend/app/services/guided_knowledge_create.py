"""Guided Knowledge Create service (P6.15).

Creates a human-authored KnowledgeItem from a create_knowledge suggestion.
No LLM auto-writing is performed here.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import KnowledgeImprovementSuggestion
from app.services.knowledge import create_knowledge_item
from app.services.knowledge_vectors import get_vector_status, index_knowledge_item


def _clean_item(data: dict | None) -> dict:
    data = dict(data or {})
    if not str(data.get("title") or "").strip():
        raise ValueError("title must not be empty")
    if not str(data.get("content_markdown") or "").strip():
        raise ValueError("content_markdown must not be empty")
    data["title"] = str(data["title"]).strip()
    data["content_markdown"] = str(data["content_markdown"]).strip()
    data["summary"] = str(data["summary"]).strip() if data.get("summary") else None
    data.setdefault("source_type", "manual")
    data.setdefault("status", "draft")
    data.setdefault("visibility", "internal")
    data["tags_json"] = [str(t).strip() for t in (data.get("tags_json") or []) if str(t).strip()]
    return data


def apply_guided_knowledge_create(
    db: Session,
    workspace_id: str,
    suggestion_id: str,
    data: dict,
    actor: str | None = None,
) -> dict:
    suggestion = db.query(KnowledgeImprovementSuggestion).filter(
        KnowledgeImprovementSuggestion.workspace_id == workspace_id,
        KnowledgeImprovementSuggestion.id == suggestion_id,
    ).first()
    if not suggestion:
        raise ValueError("Knowledge improvement suggestion not found")
    if suggestion.status in ("dismissed", "applied", "archived"):
        raise ValueError(f"Knowledge improvement suggestion status does not allow guided create: {suggestion.status}")
    if suggestion.suggestion_type != "create_knowledge":
        raise ValueError(f"Suggestion type {suggestion.suggestion_type} does not support guided create")

    item_data = _clean_item(data.get("item"))
    metadata = dict(item_data.get("metadata_json") or {})
    metadata["guided_create"] = {
        "suggestion_id": suggestion.id,
        "source_feedback_ids": suggestion.source_feedback_ids or [],
        "actor": actor,
    }
    item_data["metadata_json"] = metadata
    item = create_knowledge_item(db, workspace_id, item_data)

    suggestion.status = "applied"
    if not suggestion.applied_at:
        suggestion.applied_at = datetime.utcnow()
    suggestion_meta = dict(suggestion.metadata_json or {})
    suggestion_meta["guided_create"] = {
        "knowledge_item_id": item.id,
        "actor": actor,
        "reindex_requested": bool(data.get("reindex")),
    }
    suggestion.metadata_json = suggestion_meta

    vector_status = None
    if data.get("reindex"):
        if item.status != "active":
            raise ValueError("Only active KnowledgeItem can be reindexed")
        index_knowledge_item(db, workspace_id, item.id)
        vector_status = get_vector_status(db, workspace_id, item.id)

    db.flush()
    return {"item": item, "suggestion": suggestion, "vector_status": vector_status}
