from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.models import Decision, DecisionStatus
from app.schemas import DecisionAction

router = APIRouter(prefix="/decisions", tags=["decisions"])


def _decision_to_dict(d: Decision) -> dict:
    return {
        "id": d.id, "lead_id": d.lead_id, "artifact_id": d.artifact_id,
        "question": d.question, "recommendation": d.recommendation,
        "status": d.status.value if hasattr(d.status, 'value') else d.status,
        "operator_note": d.operator_note,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
    }


@router.get("")
def list_decisions(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    query = db.query(Decision)
    if status:
        query = query.filter(Decision.status == status)
    items = query.order_by(Decision.created_at.desc()).all()
    return {"items": [_decision_to_dict(d) for d in items]}


def _resolve_decision(db: Session, decision_id: str, new_status: DecisionStatus, note: str = ""):
    d = db.query(Decision).filter(Decision.id == decision_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Decision not found")
    d.status = new_status
    d.operator_note = note
    from datetime import datetime as dt
    d.resolved_at = dt.utcnow()
    db.commit()
    return d


@router.post("/{decision_id}/approve")
def approve_decision(
    decision_id: str,
    req: DecisionAction = DecisionAction(),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    d = _resolve_decision(db, decision_id, DecisionStatus.approved, req.operator_note)
    return {"decision": _decision_to_dict(d)}


@router.post("/{decision_id}/defer")
def defer_decision(
    decision_id: str,
    req: DecisionAction = DecisionAction(),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    d = _resolve_decision(db, decision_id, DecisionStatus.deferred, req.operator_note)
    return {"decision": _decision_to_dict(d)}


@router.post("/{decision_id}/request-rewrite")
def request_rewrite(
    decision_id: str,
    req: DecisionAction = DecisionAction(),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    d = _resolve_decision(db, decision_id, DecisionStatus.rewrite_requested, req.operator_note)
    return {"decision": _decision_to_dict(d)}
