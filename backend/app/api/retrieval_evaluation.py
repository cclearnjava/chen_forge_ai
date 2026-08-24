from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.middleware import get_admin_email
from app.db import get_db
from app.schemas import (
    RetrievalEvalCaseCreate,
    RetrievalEvalCaseOut,
    RetrievalEvalCaseUpdate,
    RetrievalEvalResultOut,
    RetrievalEvalRunCreate,
    RetrievalEvalRunDetailOut,
    RetrievalEvalRunOut,
)
from app.services.retrieval_evaluation import (
    archive_eval_case,
    create_eval_case,
    get_eval_run,
    list_eval_cases,
    list_eval_runs,
    run_retrieval_evaluation,
    update_eval_case,
)
from app.services.workspace_guard import get_current_workspace_id

router = APIRouter(prefix="/admin/knowledge/evaluations", tags=["knowledge-evaluations"])


@router.get("/cases")
def list_cases_api(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    cases = list_eval_cases(db, wid, status=status)
    return {
        "items": [RetrievalEvalCaseOut.model_validate(c).model_dump(mode="json") for c in cases],
        "total": len(cases),
    }


@router.post("/cases", status_code=201)
def create_case_api(
    req: RetrievalEvalCaseCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    try:
        case = create_eval_case(db, wid, req.model_dump())
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    return RetrievalEvalCaseOut.model_validate(case).model_dump(mode="json")


@router.patch("/cases/{case_id}")
def update_case_api(
    case_id: str,
    req: RetrievalEvalCaseUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    try:
        case = update_eval_case(db, wid, case_id, req.model_dump(exclude_unset=True))
        db.commit()
    except ValueError as exc:
        db.rollback()
        status = 404 if "not found" in str(exc).lower() else 422
        raise HTTPException(status_code=status, detail=str(exc))
    return RetrievalEvalCaseOut.model_validate(case).model_dump(mode="json")


@router.delete("/cases/{case_id}")
def archive_case_api(
    case_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    try:
        case = archive_eval_case(db, wid, case_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        status = 404 if "not found" in str(exc).lower() else 422
        raise HTTPException(status_code=status, detail=str(exc))
    return RetrievalEvalCaseOut.model_validate(case).model_dump(mode="json")


@router.get("/runs")
def list_runs_api(db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    runs = list_eval_runs(db, wid)
    return {
        "items": [RetrievalEvalRunOut.model_validate(r).model_dump(mode="json") for r in runs],
        "total": len(runs),
    }


@router.post("/runs", status_code=201)
def run_evaluation_api(
    req: RetrievalEvalRunCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    try:
        run = run_retrieval_evaluation(db, wid, case_ids=req.case_ids, k=req.k)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    return RetrievalEvalRunOut.model_validate(run).model_dump(mode="json")


@router.get("/runs/{run_id}")
def get_run_detail_api(
    run_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    run = get_eval_run(db, wid, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Retrieval eval run not found")
    return RetrievalEvalRunDetailOut(
        run=RetrievalEvalRunOut.model_validate(run),
        results=[RetrievalEvalResultOut.model_validate(r) for r in run.results],
    ).model_dump(mode="json")
