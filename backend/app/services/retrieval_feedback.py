"""Retrieval Feedback Loop service (P6.11)."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    Artifact,
    KNOWLEDGE_RETRIEVAL_FEEDBACK_SOURCES,
    KNOWLEDGE_RETRIEVAL_FEEDBACK_STATUSES,
    KNOWLEDGE_RETRIEVAL_FEEDBACK_TYPES,
    KnowledgeItem,
    KnowledgeRetrievalFeedback,
    Opportunity,
    RetrievalEvalResult,
)


def _validate_enum(name: str, value: str, allowed: tuple[str, ...]) -> str:
    if value not in allowed:
        raise ValueError(f"Invalid {name}: {value}")
    return value


def _require_workspace(db: Session, model, workspace_id: str, object_id: str, field: str):
    obj = db.query(model).filter(model.id == object_id).first()
    if not obj:
        raise ValueError(f"{field} not found")
    if obj.workspace_id != workspace_id:
        raise ValueError(f"{field} does not belong to this workspace")
    return obj


def _validate_links(db: Session, workspace_id: str, data: dict) -> None:
    feedback_type = data.get("feedback_type")
    knowledge_item_id = data.get("knowledge_item_id")
    expected_item_id = data.get("expected_knowledge_item_id")

    if feedback_type != "missing" and not knowledge_item_id:
        raise ValueError("knowledge_item_id is required for non-missing feedback")
    if feedback_type == "missing" and not expected_item_id:
        raise ValueError("expected_knowledge_item_id is required for missing feedback")

    if knowledge_item_id:
        _require_workspace(db, KnowledgeItem, workspace_id, knowledge_item_id, "knowledge_item_id")
    if expected_item_id:
        _require_workspace(db, KnowledgeItem, workspace_id, expected_item_id, "expected_knowledge_item_id")
    if data.get("artifact_id"):
        _require_workspace(db, Artifact, workspace_id, data["artifact_id"], "artifact_id")
    if data.get("retrieval_eval_result_id"):
        _require_workspace(
            db,
            RetrievalEvalResult,
            workspace_id,
            data["retrieval_eval_result_id"],
            "retrieval_eval_result_id",
        )
    if data.get("opportunity_id"):
        _require_workspace(db, Opportunity, workspace_id, data["opportunity_id"], "opportunity_id")


def create_retrieval_feedback(
    db: Session,
    workspace_id: str,
    data: dict,
    *,
    actor: str | None = None,
) -> KnowledgeRetrievalFeedback:
    feedback_type = _validate_enum(
        "feedback_type",
        data.get("feedback_type"),
        KNOWLEDGE_RETRIEVAL_FEEDBACK_TYPES,
    )
    source = _validate_enum("source", data.get("source"), KNOWLEDGE_RETRIEVAL_FEEDBACK_SOURCES)
    _validate_links(db, workspace_id, data)

    feedback = KnowledgeRetrievalFeedback(
        workspace_id=workspace_id,
        feedback_type=feedback_type,
        status="open",
        source=source,
        query=(data.get("query") or None),
        note=data.get("note"),
        knowledge_item_id=data.get("knowledge_item_id"),
        expected_knowledge_item_id=data.get("expected_knowledge_item_id"),
        artifact_id=data.get("artifact_id"),
        retrieval_eval_result_id=data.get("retrieval_eval_result_id"),
        opportunity_id=data.get("opportunity_id"),
        citation_hit_json=data.get("citation_hit_json"),
        metadata_json=data.get("metadata_json"),
        created_by=actor,
    )
    db.add(feedback)
    db.flush()
    return feedback


def list_retrieval_feedback(db: Session, workspace_id: str, filters: dict | None = None) -> list[KnowledgeRetrievalFeedback]:
    filters = filters or {}
    q = db.query(KnowledgeRetrievalFeedback).filter(
        KnowledgeRetrievalFeedback.workspace_id == workspace_id,
    )
    if filters.get("status"):
        status = _validate_enum("status", filters["status"], KNOWLEDGE_RETRIEVAL_FEEDBACK_STATUSES)
        q = q.filter(KnowledgeRetrievalFeedback.status == status)
    if filters.get("feedback_type"):
        feedback_type = _validate_enum("feedback_type", filters["feedback_type"], KNOWLEDGE_RETRIEVAL_FEEDBACK_TYPES)
        q = q.filter(KnowledgeRetrievalFeedback.feedback_type == feedback_type)
    if filters.get("knowledge_item_id"):
        q = q.filter(KnowledgeRetrievalFeedback.knowledge_item_id == filters["knowledge_item_id"])
    return q.order_by(KnowledgeRetrievalFeedback.created_at.desc()).all()


def update_retrieval_feedback(
    db: Session,
    workspace_id: str,
    feedback_id: str,
    data: dict,
) -> KnowledgeRetrievalFeedback:
    feedback = db.query(KnowledgeRetrievalFeedback).filter(
        KnowledgeRetrievalFeedback.id == feedback_id,
        KnowledgeRetrievalFeedback.workspace_id == workspace_id,
    ).first()
    if not feedback:
        raise ValueError("Retrieval feedback not found")

    if "status" in data and data["status"] is not None:
        status = _validate_enum("status", data["status"], KNOWLEDGE_RETRIEVAL_FEEDBACK_STATUSES)
        feedback.status = status
        now = datetime.utcnow()
        if status in ("reviewed", "resolved") and not feedback.reviewed_at:
            feedback.reviewed_at = now
        if status == "resolved" and not feedback.resolved_at:
            feedback.resolved_at = now
    if "note" in data:
        feedback.note = data["note"]
    db.flush()
    return feedback
