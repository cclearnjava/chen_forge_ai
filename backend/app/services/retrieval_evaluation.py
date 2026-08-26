"""Knowledge Retrieval Evaluation service (P6.9)."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    KnowledgeItem,
    RetrievalEvalCase,
    RetrievalEvalResult,
    RetrievalEvalRun,
)
from app.services.embedding_provider import get_embedding_provider
from app.services.knowledge_retriever import (
    RETRIEVER_VERSION,
    retrieve_knowledge_for_sales_reply,
)


def compute_retrieval_metrics(expected_ids: list[str], actual_ids: list[str]) -> dict:
    expected = list(dict.fromkeys(expected_ids or []))
    actual = list(dict.fromkeys(actual_ids or []))
    matched = [iid for iid in expected if iid in actual]
    missed = [iid for iid in expected if iid not in actual]
    extra = [iid for iid in actual if iid not in expected]
    recall = len(matched) / len(expected) if expected else 0.0
    precision = len(matched) / len(actual) if actual else 0.0
    return {
        "matched_expected_ids": matched,
        "missed_expected_ids": missed,
        "extra_hit_ids": extra,
        "recall_at_k": recall,
        "precision_at_k": precision,
        "hit_count": len(actual),
    }


def _validate_expected_items(db: Session, workspace_id: str, item_ids: list[str]) -> list[str]:
    ids = list(dict.fromkeys(item_ids or []))
    if not ids:
        raise ValueError("expected_knowledge_item_ids must not be empty")

    items = db.query(KnowledgeItem).filter(KnowledgeItem.id.in_(ids)).all()
    by_id = {it.id: it for it in items}
    for iid in ids:
        item = by_id.get(iid)
        if not item:
            raise ValueError(f"Knowledge item {iid} not found")
        if item.workspace_id != workspace_id:
            raise ValueError(f"Knowledge item {iid} does not belong to this workspace")
        if item.status != "active":
            raise ValueError(f"Knowledge item {iid} is not active")
    return ids


def create_eval_case(db: Session, workspace_id: str, data: dict) -> RetrievalEvalCase:
    expected_ids = _validate_expected_items(db, workspace_id, data.get("expected_knowledge_item_ids") or [])
    case = RetrievalEvalCase(
        workspace_id=workspace_id,
        query=(data.get("query") or "").strip(),
        expected_knowledge_item_ids=expected_ids,
        tags_json=data.get("tags_json") or [],
        notes=data.get("notes"),
        status="active",
    )
    if not case.query:
        raise ValueError("query must not be empty")
    db.add(case)
    db.flush()
    return case


def update_eval_case(db: Session, workspace_id: str, case_id: str, data: dict) -> RetrievalEvalCase:
    case = db.query(RetrievalEvalCase).filter(
        RetrievalEvalCase.id == case_id,
        RetrievalEvalCase.workspace_id == workspace_id,
    ).first()
    if not case:
        raise ValueError("Retrieval eval case not found")
    if "query" in data and data["query"] is not None:
        query = data["query"].strip()
        if not query:
            raise ValueError("query must not be empty")
        case.query = query
    if "expected_knowledge_item_ids" in data and data["expected_knowledge_item_ids"] is not None:
        case.expected_knowledge_item_ids = _validate_expected_items(
            db, workspace_id, data["expected_knowledge_item_ids"],
        )
    if "tags_json" in data and data["tags_json"] is not None:
        case.tags_json = data["tags_json"]
    if "notes" in data:
        case.notes = data["notes"]
    if "status" in data and data["status"] is not None:
        if data["status"] not in ("active", "archived"):
            raise ValueError(f"Invalid status: {data['status']}")
        case.status = data["status"]
    db.flush()
    return case


def archive_eval_case(db: Session, workspace_id: str, case_id: str) -> RetrievalEvalCase:
    return update_eval_case(db, workspace_id, case_id, {"status": "archived"})


def list_eval_cases(db: Session, workspace_id: str, status: str | None = None) -> list[RetrievalEvalCase]:
    q = db.query(RetrievalEvalCase).filter(RetrievalEvalCase.workspace_id == workspace_id)
    if status:
        q = q.filter(RetrievalEvalCase.status == status)
    return q.order_by(RetrievalEvalCase.updated_at.desc()).all()


def _load_cases(db: Session, workspace_id: str, case_ids: list[str] | None) -> list[RetrievalEvalCase]:
    q = db.query(RetrievalEvalCase).filter(RetrievalEvalCase.workspace_id == workspace_id)
    if case_ids:
        if len(case_ids) > 100:
            raise ValueError("At most 100 eval cases can be run at once")
        q = q.filter(RetrievalEvalCase.id.in_(case_ids))
    else:
        q = q.filter(RetrievalEvalCase.status == "active")
    cases = q.order_by(RetrievalEvalCase.created_at.asc()).all()
    if not cases:
        raise ValueError("No retrieval eval cases to run")
    return cases


def _result_status(metrics: dict, error: str | None = None) -> str:
    if error:
        return "error"
    if metrics["hit_count"] == 0:
        return "empty"
    if metrics["missed_expected_ids"]:
        return "missed"
    return "passed"


def run_retrieval_evaluation(
    db: Session,
    workspace_id: str,
    *,
    case_ids: list[str] | None = None,
    k: int = 5,
    trigger_source: str | None = None,
    knowledge_item_id: str | None = None,
) -> RetrievalEvalRun:
    if k < 1 or k > 20:
        raise ValueError("k must be between 1 and 20")
    cases = _load_cases(db, workspace_id, case_ids)
    provider = get_embedding_provider()
    run = RetrievalEvalRun(
        workspace_id=workspace_id,
        status="running",
        case_count=len(cases),
        k=k,
        trigger_source=trigger_source,
        knowledge_item_id=knowledge_item_id,
        retriever_version=RETRIEVER_VERSION,
        vector_store=settings.vector_store,
        embedding_model=provider.model,
        reranker_enabled=settings.reranker_provider != "none",
        reranker_provider=settings.reranker_provider,
        reranker_model=settings.reranker_model,
        started_at=datetime.utcnow(),
    )
    db.add(run)
    db.flush()

    results: list[RetrievalEvalResult] = []
    for case in cases:
        error = None
        citation_pack = None
        actual_ids: list[str] = []
        try:
            expected_ids = _validate_expected_items(db, workspace_id, case.expected_knowledge_item_ids)
            citation_pack = retrieve_knowledge_for_sales_reply(
                db,
                workspace_id=workspace_id,
                query_text=case.query,
                max_hits=k,
            )
            actual_ids = [h["knowledge_item_id"] for h in citation_pack.get("hits", [])]
            metrics = compute_retrieval_metrics(expected_ids, actual_ids)
        except Exception as exc:
            error = str(exc)
            expected_ids = case.expected_knowledge_item_ids or []
            metrics = compute_retrieval_metrics(expected_ids, [])

        result = RetrievalEvalResult(
            workspace_id=workspace_id,
            run_id=run.id,
            case_id=case.id,
            query=case.query,
            expected_knowledge_item_ids=expected_ids,
            actual_knowledge_item_ids=actual_ids,
            matched_expected_ids=metrics["matched_expected_ids"],
            missed_expected_ids=metrics["missed_expected_ids"],
            extra_hit_ids=metrics["extra_hit_ids"],
            recall_at_k=metrics["recall_at_k"],
            precision_at_k=metrics["precision_at_k"],
            hit_count=metrics["hit_count"],
            citation_pack_json=citation_pack,
            status=_result_status(metrics, error),
            error_message=error,
        )
        db.add(result)
        results.append(result)

    db.flush()
    run.results = results
    run.zero_hit_count = sum(1 for r in results if r.hit_count == 0)
    run.miss_count = sum(1 for r in results if r.status in ("missed", "empty"))
    run.error_count = sum(1 for r in results if r.status == "error")
    run.average_recall_at_k = sum(r.recall_at_k for r in results) / len(results)
    run.average_precision_at_k = sum(r.precision_at_k for r in results) / len(results)
    run.status = "completed"
    run.completed_at = datetime.utcnow()
    db.flush()
    return run


def list_eval_runs(db: Session, workspace_id: str) -> list[RetrievalEvalRun]:
    return db.query(RetrievalEvalRun).filter(
        RetrievalEvalRun.workspace_id == workspace_id,
    ).order_by(RetrievalEvalRun.created_at.desc()).all()


def get_eval_run(db: Session, workspace_id: str, run_id: str) -> RetrievalEvalRun | None:
    return db.query(RetrievalEvalRun).filter(
        RetrievalEvalRun.id == run_id,
        RetrievalEvalRun.workspace_id == workspace_id,
    ).first()
