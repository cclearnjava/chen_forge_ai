"""Knowledge Change Validation service (P6.16).

Runs active RetrievalEvalCase rows related to a KnowledgeItem after a guided
edit/create/reindex flow, so the operator can verify retrieval quality.
"""

from sqlalchemy.orm import Session

from app.models import KnowledgeItem, RetrievalEvalCase
from app.services.retrieval_evaluation import run_retrieval_evaluation


def _related_eval_cases(db: Session, workspace_id: str, knowledge_item_id: str) -> list[RetrievalEvalCase]:
    cases = db.query(RetrievalEvalCase).filter(
        RetrievalEvalCase.workspace_id == workspace_id,
        RetrievalEvalCase.status == "active",
    ).order_by(RetrievalEvalCase.created_at.asc()).all()
    return [
        case for case in cases
        if knowledge_item_id in (case.expected_knowledge_item_ids or [])
    ]


def validate_knowledge_change(db: Session, workspace_id: str, knowledge_item_id: str, data: dict | None = None) -> dict:
    data = data or {}
    item = db.query(KnowledgeItem).filter(
        KnowledgeItem.workspace_id == workspace_id,
        KnowledgeItem.id == knowledge_item_id,
    ).first()
    if not item:
        raise ValueError("Knowledge item not found")
    cases = _related_eval_cases(db, workspace_id, knowledge_item_id)
    if not cases:
        raise ValueError("No active retrieval eval cases for this KnowledgeItem")
    k = data.get("k") or 5
    run = run_retrieval_evaluation(db, workspace_id, case_ids=[case.id for case in cases], k=k)
    results = list(run.results or [])
    summary = {
        "passed_count": sum(1 for result in results if result.status == "passed"),
        "missed_count": sum(1 for result in results if result.status in ("missed", "empty")),
        "error_count": sum(1 for result in results if result.status == "error"),
        "average_recall_at_k": run.average_recall_at_k,
        "average_precision_at_k": run.average_precision_at_k,
    }
    return {
        "knowledge_item_id": knowledge_item_id,
        "case_ids": [case.id for case in cases],
        "case_count": len(cases),
        "run": run,
        "results": results,
        "summary": summary,
    }
