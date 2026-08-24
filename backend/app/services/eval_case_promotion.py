"""Eval Case Promotion service (P6.13).

Turns retrieval feedback or promote_eval_case suggestions into active
RetrievalEvalCase rows. This is deterministic and does not call external LLMs.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    KnowledgeImprovementSuggestion,
    KnowledgeRetrievalFeedback,
    RetrievalEvalCase,
)
from app.services.retrieval_evaluation import create_eval_case


def _normalize_query(query: str | None) -> str:
    return " ".join((query or "").strip().lower().split())


def _normalize_expected_ids(ids: list[str]) -> list[str]:
    return sorted(list(dict.fromkeys(ids or [])))


def _existing_active_case(
    db: Session,
    workspace_id: str,
    *,
    query: str,
    expected_ids: list[str],
) -> RetrievalEvalCase | None:
    normalized = _normalize_query(query)
    expected = _normalize_expected_ids(expected_ids)
    cases = db.query(RetrievalEvalCase).filter(
        RetrievalEvalCase.workspace_id == workspace_id,
        RetrievalEvalCase.status == "active",
    ).all()
    for case in cases:
        if _normalize_query(case.query) == normalized and _normalize_expected_ids(case.expected_knowledge_item_ids) == expected:
            return case
    return None


def _case_candidate_from_feedback(feedback: KnowledgeRetrievalFeedback) -> dict:
    if not feedback.query or not feedback.query.strip():
        raise ValueError("feedback query is required for eval case promotion")
    if feedback.feedback_type == "missing":
        expected_id = feedback.expected_knowledge_item_id
    else:
        expected_id = feedback.knowledge_item_id
    if not expected_id:
        raise ValueError("expected knowledge item is required for eval case promotion")
    return {
        "query": feedback.query.strip(),
        "expected_knowledge_item_ids": [expected_id],
        "tags_json": ["promoted", "retrieval_feedback", feedback.feedback_type],
        "notes": f"Promoted from retrieval feedback {feedback.id}.",
        "source_feedback_ids": [feedback.id],
    }


def _feedbacks_for_ids(db: Session, workspace_id: str, feedback_ids: list[str]) -> list[KnowledgeRetrievalFeedback]:
    ids = list(dict.fromkeys(feedback_ids or []))
    if not ids:
        return []
    feedbacks = db.query(KnowledgeRetrievalFeedback).filter(
        KnowledgeRetrievalFeedback.workspace_id == workspace_id,
        KnowledgeRetrievalFeedback.id.in_(ids),
    ).all()
    by_id = {fb.id: fb for fb in feedbacks}
    missing = [fid for fid in ids if fid not in by_id]
    if missing:
        raise ValueError("retrieval feedback not found")
    return [by_id[fid] for fid in ids]


def _load_suggestion(db: Session, workspace_id: str, suggestion_id: str | None) -> KnowledgeImprovementSuggestion | None:
    if not suggestion_id:
        return None
    suggestion = db.query(KnowledgeImprovementSuggestion).filter(
        KnowledgeImprovementSuggestion.workspace_id == workspace_id,
        KnowledgeImprovementSuggestion.id == suggestion_id,
    ).first()
    if not suggestion:
        raise ValueError("Knowledge improvement suggestion not found")
    if suggestion.suggestion_type != "promote_eval_case":
        raise ValueError("Only promote_eval_case suggestions can create eval cases")
    return suggestion


def _candidates_from_suggestion(
    db: Session,
    workspace_id: str,
    suggestion: KnowledgeImprovementSuggestion,
) -> list[dict]:
    feedbacks = _feedbacks_for_ids(db, workspace_id, suggestion.source_feedback_ids or [])
    if feedbacks:
        return [_case_candidate_from_feedback(fb) for fb in feedbacks]

    expected_id = suggestion.knowledge_item_id or suggestion.expected_knowledge_item_id
    if not expected_id:
        raise ValueError("expected knowledge item is required for eval case promotion")
    evidence = suggestion.evidence_json or {}
    queries = evidence.get("sample_queries") or []
    if not queries:
        raise ValueError("suggestion sample query is required for eval case promotion")
    return [
        {
            "query": str(query).strip(),
            "expected_knowledge_item_ids": [expected_id],
            "tags_json": ["promoted", "knowledge_suggestion", suggestion.suggestion_type],
            "notes": f"Promoted from knowledge improvement suggestion {suggestion.id}.",
            "source_feedback_ids": suggestion.source_feedback_ids or [],
        }
        for query in queries
        if str(query).strip()
    ]


def promote_eval_cases(db: Session, workspace_id: str, data: dict, actor: str | None = None) -> dict:
    suggestion = _load_suggestion(db, workspace_id, data.get("suggestion_id"))
    feedback_ids = data.get("feedback_ids") or []
    if suggestion:
        candidates = _candidates_from_suggestion(db, workspace_id, suggestion)
    else:
        feedbacks = _feedbacks_for_ids(db, workspace_id, feedback_ids)
        candidates = [_case_candidate_from_feedback(fb) for fb in feedbacks]

    if not candidates:
        raise ValueError("feedback_ids or suggestion_id is required")

    cases: list[RetrievalEvalCase] = []
    skipped_count = 0
    for candidate in candidates:
        existing = _existing_active_case(
            db,
            workspace_id,
            query=candidate["query"],
            expected_ids=candidate["expected_knowledge_item_ids"],
        )
        if existing:
            cases.append(existing)
            skipped_count += 1
            continue
        case = create_eval_case(db, workspace_id, candidate)
        case.tags_json = list(dict.fromkeys((case.tags_json or []) + ["eval_case_promotion"]))
        meta = f" actor={actor}" if actor else ""
        case.notes = f"{case.notes or ''}{meta}".strip()
        cases.append(case)

    created_count = len(cases) - skipped_count
    if suggestion and created_count > 0:
        suggestion.status = "applied"
        if not suggestion.applied_at:
            suggestion.applied_at = datetime.utcnow()
        metadata = dict(suggestion.metadata_json or {})
        existing_ids = metadata.get("promoted_eval_case_ids") or []
        metadata["promoted_eval_case_ids"] = list(dict.fromkeys(existing_ids + [c.id for c in cases]))
        suggestion.metadata_json = metadata
    db.flush()
    return {"created_count": created_count, "skipped_count": skipped_count, "cases": cases}
