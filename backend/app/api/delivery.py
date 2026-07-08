from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.workspace import get_default_workspace_id
from app.services.events import record_event
from app.services.workspace_guard import get_scoped_or_404
from app.auth.middleware import get_admin_email
from app.models import (
    Artifact, ArtifactType, AuditLog, DeliveryChannel, DeliveryJob,
    DeliveryStatus, Message, MessageSenderType, Opportunity, OpportunityStage,
)
from app.schemas import DeliveryJobCreate, DeliveryJobMarkSentIn, DeliveryJobMarkSentOut
from app.config import settings

router = APIRouter(prefix="/delivery-jobs", tags=["delivery"])


def _job_to_dict(j: DeliveryJob) -> dict:
    return {
        "id": j.id, "workspace_id": j.workspace_id, "lead_id": j.lead_id, "artifact_id": j.artifact_id,
        "channel": j.channel.value if hasattr(j.channel, 'value') else j.channel,
        "recipient": j.recipient, "subject": j.subject,
        "body_markdown": j.body_markdown,
        "status": j.status.value if hasattr(j.status, 'value') else j.status,
        "provider_message_id": j.provider_message_id,
        "error_message": j.error_message,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "sent_at": j.sent_at.isoformat() if j.sent_at else None,
    }


@router.post("", status_code=201)
def create_delivery_job(
    req: DeliveryJobCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    artifact = get_scoped_or_404(db, Artifact, req.artifact_id, label="Artifact")
    if not artifact:
        raise HTTPException(status_code=422, detail="Artifact not found")
    if artifact.lead_id != req.lead_id:
        raise HTTPException(status_code=400, detail="Artifact does not belong to this lead")
    if artifact.requires_approval:
        raise HTTPException(status_code=422, detail="Artifact must be approved before delivery")

    wid = artifact.workspace_id or get_default_workspace_id(db)
    job = DeliveryJob(
        workspace_id=wid,
        lead_id=req.lead_id,
        artifact_id=req.artifact_id,
        channel=DeliveryChannel(req.channel),
        recipient=req.recipient,
        subject=req.subject,
        body_markdown=artifact.content_markdown or "",
    )
    db.add(job)
    db.commit()
    return {"delivery_job": _job_to_dict(job)}


@router.post("/{delivery_job_id}/send", status_code=202)
def send_delivery_job(
    delivery_job_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    job = get_scoped_or_404(db, DeliveryJob, delivery_job_id, label="DeliveryJob")

    job.status = DeliveryStatus.sending
    db.commit()

    try:
        # Mock email send — in production this calls Resend API
        from datetime import datetime as dt
        job.status = DeliveryStatus.sent
        job.provider_message_id = f"mock-email-{delivery_job_id[:8]}"
        job.sent_at = dt.utcnow()
        db.commit()
    except Exception as e:
        job.status = DeliveryStatus.failed
        job.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Delivery failed: {e}")

    return {"delivery_job": _job_to_dict(job)}


@router.get("/{delivery_job_id}")
def get_delivery_job(
    delivery_job_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    job = get_scoped_or_404(db, DeliveryJob, delivery_job_id, label="DeliveryJob")
    return {"delivery_job": _job_to_dict(job)}


@router.post("/{delivery_job_id}/mark-sent", response_model=DeliveryJobMarkSentOut)
def mark_delivery_job_sent(
    delivery_job_id: str,
    req: DeliveryJobMarkSentIn = DeliveryJobMarkSentIn(),
    db: Session = Depends(get_db),
    admin: str = Depends(get_admin_email),
):
    job = get_scoped_or_404(db, DeliveryJob, delivery_job_id, label="DeliveryJob")
    if job.status != DeliveryStatus.draft:
        raise HTTPException(status_code=409, detail=f"DeliveryJob is already {job.status.value}")

    from datetime import datetime as dt
    job.status = DeliveryStatus.sent
    job.sent_at = dt.utcnow()

    mark_wid = job.workspace_id or get_default_workspace_id(db)

    db.add(AuditLog(
        workspace_id=mark_wid,
        lead_id=job.lead_id,
        actor=admin,
        action="delivery_job_marked_sent",
        details_json={
            "delivery_job_id": job.id,
            "artifact_id": job.artifact_id,
            "channel": job.channel.value if hasattr(job.channel, "value") else str(job.channel),
            "recipient": job.recipient,
            "operator_note": req.operator_note,
        },
    ))

    # BE-03: If this is a proposal delivery, write Conversation Message + proposal_sent AuditLog
    artifact = get_scoped_or_404(db, Artifact, job.artifact_id, label="Artifact")
    if artifact and artifact.type == ArtifactType.proposal_draft:
        if artifact.opportunity_id:
            opp = db.query(Opportunity).filter(Opportunity.id == artifact.opportunity_id).first()
            if opp and opp.conversation_id:
                db.add(Message(
                    workspace_id=mark_wid,
                    conversation_id=opp.conversation_id,
                    customer_id=opp.customer_id,
                    contact_id=opp.primary_contact_id,
                    sender_type=MessageSenderType.owner,
                    sender_label=admin,
                    body_markdown=f"已发送 PoC Proposal PDF：{job.subject}",
                    source="delivery",
                ))

        db.add(AuditLog(
            workspace_id=mark_wid,
            lead_id=job.lead_id,
            actor=admin,
            action="proposal_sent",
            details_json={
                "delivery_job_id": job.id,
                "artifact_id": job.artifact_id,
                "opportunity_id": artifact.opportunity_id,
                "recipient": job.recipient,
                "operator_note": req.operator_note,
            },
        ))

    # BE-04: Quote/SOW delivery — write Message, AuditLog, advance to contracting
    if artifact and artifact.type == ArtifactType.quote_draft:
        if artifact.opportunity_id:
            opp = db.query(Opportunity).filter(Opportunity.id == artifact.opportunity_id).first()
            if opp:
                opp.stage = OpportunityStage.contracting
                opp.next_step = "Wait for customer confirmation or prepare contract draft"
                if opp.conversation_id:
                    db.add(Message(
                        workspace_id=mark_wid,
                        conversation_id=opp.conversation_id, customer_id=opp.customer_id,
                        contact_id=opp.primary_contact_id, sender_type=MessageSenderType.owner,
                        sender_label=admin,
                        body_markdown=f"已发送 Quote / SOW 确认材料：{job.subject}",
                        source="delivery",
                    ))
        db.add(AuditLog(
            workspace_id=mark_wid,
            lead_id=job.lead_id, actor=admin, action="quote_sow_sent",
            details_json={
                "delivery_job_id": job.id, "quote_artifact_id": job.artifact_id,
                "opportunity_id": artifact.opportunity_id,
                "recipient": job.recipient, "operator_note": req.operator_note,
            },
        ))

    record_event(db, workspace_id=job.workspace_id, type="delivery_job.sent", source="delivery_api",
                  subject_type="delivery_job", subject_id=job.id,
                  title=f"已发送: {job.subject}",
                  summary=job.body_markdown[:100] if job.body_markdown else None)
    db.commit()
    return {"delivery_job": _job_to_dict(job)}
