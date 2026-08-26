"""Guided Knowledge Edit service (P6.14).

Applies a human-provided KnowledgeItem patch from an improvement suggestion.
This service is deterministic and never asks an LLM to edit user data.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import KnowledgeImprovementSuggestion
from app.services.knowledge import get_knowledge_item_or_none, update_knowledge_item
from app.services.knowledge_vectors import get_vector_status, index_knowledge_item

EDITABLE_SUGGESTION_TYPES = (
    "update_content",
    "improve_metadata",
    "improve_retrievability",
    "split_knowledge",
)

EDITABLE_FIELDS = (
    "title",
    "summary",
    "content_markdown",
    "source_type",
    "tags_json",
    "service_id",
    "visibility",
    "confidence",
    "metadata_json",
)


def _clean_patch(patch: dict | None) -> dict:
    patch = patch or {}
    cleaned = {k: v for k, v in patch.items() if k in EDITABLE_FIELDS and v is not None}
    if not cleaned:
        raise ValueError("knowledge edit patch must include at least one editable field")
    for field in ("title", "content_markdown"):
        if field in cleaned and not str(cleaned[field]).strip():
            raise ValueError(f"{field} must not be empty")
    if "tags_json" in cleaned:
        cleaned["tags_json"] = [str(t).strip() for t in (cleaned["tags_json"] or []) if str(t).strip()]
    return cleaned


def apply_guided_knowledge_edit(
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
        raise ValueError(f"Knowledge improvement suggestion status does not allow guided edit: {suggestion.status}")
    if suggestion.suggestion_type not in EDITABLE_SUGGESTION_TYPES:
        raise ValueError(f"Suggestion type {suggestion.suggestion_type} does not support guided edit")
    if not suggestion.knowledge_item_id:
        raise ValueError("knowledge_item_id is required for guided edit")

    item = get_knowledge_item_or_none(db, workspace_id, suggestion.knowledge_item_id)
    if not item:
        raise ValueError("Knowledge item not found")

    patch = _clean_patch(data.get("patch"))
    before = {field: getattr(item, field, None) for field in patch}
    updated = update_knowledge_item(db, workspace_id, item.id, patch)
    if not updated:
        raise ValueError("Knowledge item not found")

    suggestion.status = "applied"
    if not suggestion.applied_at:
        suggestion.applied_at = datetime.utcnow()
    metadata = dict(suggestion.metadata_json or {})
    metadata["guided_edit"] = {
        "knowledge_item_id": item.id,
        "changed_fields": list(patch.keys()),
        "before": before,
        "after": {field: getattr(updated, field, None) for field in patch},
        "actor": actor,
        "reindex_requested": bool(data.get("reindex")),
    }
    suggestion.metadata_json = metadata

    vector_status = None
    if data.get("reindex"):
        index_knowledge_item(db, workspace_id, item.id)
        vector_status = get_vector_status(db, workspace_id, item.id)

    db.flush()
    return {"item": updated, "suggestion": suggestion, "vector_status": vector_status}
