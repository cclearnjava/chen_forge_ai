from datetime import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.models import (
    Artifact, AuditLog, Conversation, Customer,
    Decision, DecisionStatus, DeliveryChannel, DeliveryJob, DeliveryStatus,
    Message, MessageSenderType, Opportunity,
)
from app.schemas import DecisionAction

router = APIRouter(prefix="/decisions", tags=["decisions"])


def _decision_to_dict(d: Decision) -> dict:
    return {
        "id": d.id, "lead_id": d.lead_id, "agent_run_id": d.agent_run_id,
        "opportunity_id": d.opportunity_id,
        "artifact_id": d.artifact_id, "question": d.question,
        "recommendation": d.recommendation,
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


def _guard_waiting(d: Decision | None, decision_id: str) -> Decision:
    if not d:
        raise HTTPException(status_code=404, detail="Decision not found")
    if d.status != DecisionStatus.waiting:
        raise HTTPException(status_code=409, detail=f"Decision is already {d.status.value}")
    return d


@router.post("/{decision_id}/approve")
def approve_decision(
    decision_id: str,
    req: DecisionAction = DecisionAction(),
    db: Session = Depends(get_db),
    admin: str = Depends(get_admin_email),
):
    d = db.query(Decision).filter(Decision.id == decision_id).first()
    _guard_waiting(d, decision_id)

    artifact = db.query(Artifact).filter(Artifact.id == d.artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=422, detail="Decision has no linked artifact")

    opp = db.query(Opportunity).filter(Opportunity.id == d.opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=422, detail="Decision has no linked opportunity")
    if not d.lead_id:
        raise HTTPException(status_code=422, detail="Decision has no linked lead")
    if not opp.conversation_id:
        raise HTTPException(status_code=422, detail="Opportunity has no linked conversation")

    # Resolve the decision
    d.status = DecisionStatus.approved
    d.operator_note = req.operator_note
    d.resolved_at = dt.utcnow()

    # Determine recipient from primary_contact or customer
    recipient = "unknown"
    if opp.primary_contact_id:
        from app.models import Contact
        contact = db.query(Contact).filter(Contact.id == opp.primary_contact_id).first()
        if contact:
            recipient = contact.email or contact.name or "unknown"
    if recipient == "unknown" and opp.customer_id:
        customer = db.query(Customer).filter(Customer.id == opp.customer_id).first()
        if customer:
            recipient = customer.owner_email

    # Create DeliveryJob
    job = DeliveryJob(
        lead_id=d.lead_id,
        artifact_id=artifact.id,
        channel=DeliveryChannel.manual_copy,
        recipient=recipient,
        subject=f"ChenForge AI 回复：{opp.title}",
        body_markdown=artifact.content_markdown or "",
        status=DeliveryStatus.draft,
    )
    db.add(job)
    db.flush()

    # Write Message to conversation
    message = Message(
        conversation_id=opp.conversation_id,
        customer_id=opp.customer_id,
        contact_id=opp.primary_contact_id,
        sender_type=MessageSenderType.owner,
        sender_label=admin,
        body_markdown=artifact.content_markdown or "",
        source="delivery",
    )
    db.add(message)
    db.flush()

    # Write AuditLog
    db.add(AuditLog(
        lead_id=d.lead_id,
        actor=admin,
        action="decision_approved",
        details_json={
            "decision_id": d.id,
            "artifact_id": artifact.id,
            "opportunity_id": opp.id,
            "delivery_job_id": job.id,
            "message_id": message.id,
        },
    ))

    db.commit()
    return {"decision": _decision_to_dict(d)}


@router.post("/{decision_id}/defer")
def defer_decision(
    decision_id: str,
    req: DecisionAction = DecisionAction(),
    db: Session = Depends(get_db),
    admin: str = Depends(get_admin_email),
):
    d = db.query(Decision).filter(Decision.id == decision_id).first()
    _guard_waiting(d, decision_id)

    d.status = DecisionStatus.deferred
    d.operator_note = req.operator_note
    d.resolved_at = dt.utcnow()

    db.add(AuditLog(
        lead_id=d.lead_id,
        actor=admin,
        action="decision_deferred",
        details_json={
            "decision_id": d.id,
            "artifact_id": d.artifact_id,
            "opportunity_id": d.opportunity_id,
        },
    ))

    db.commit()
    return {"decision": _decision_to_dict(d)}


@router.post("/{decision_id}/request-rewrite")
def request_rewrite(
    decision_id: str,
    req: DecisionAction = DecisionAction(),
    db: Session = Depends(get_db),
    admin: str = Depends(get_admin_email),
):
    d = db.query(Decision).filter(Decision.id == decision_id).first()
    _guard_waiting(d, decision_id)

    d.status = DecisionStatus.rewrite_requested
    d.operator_note = req.operator_note
    d.resolved_at = dt.utcnow()

    # Write AuditLog only — no DeliveryJob, no Message
    db.add(AuditLog(
        lead_id=d.lead_id,
        actor=admin,
        action="decision_rewrite_requested",
        details_json={
            "decision_id": d.id,
            "artifact_id": d.artifact_id,
            "opportunity_id": d.opportunity_id,
        },
    ))

    db.commit()
    return {"decision": _decision_to_dict(d)}
