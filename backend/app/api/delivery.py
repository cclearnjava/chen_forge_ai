from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.models import AuditLog, DeliveryJob, Artifact, DeliveryStatus, DeliveryChannel
from app.schemas import DeliveryJobCreate, DeliveryJobMarkSentIn, DeliveryJobMarkSentOut
from app.config import settings

router = APIRouter(prefix="/delivery-jobs", tags=["delivery"])


def _job_to_dict(j: DeliveryJob) -> dict:
    return {
        "id": j.id, "lead_id": j.lead_id, "artifact_id": j.artifact_id,
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
    artifact = db.query(Artifact).filter(Artifact.id == req.artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if artifact.lead_id != req.lead_id:
        raise HTTPException(status_code=400, detail="Artifact does not belong to this lead")
    if artifact.requires_approval:
        raise HTTPException(status_code=422, detail="Artifact must be approved before delivery")

    job = DeliveryJob(
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
    job = db.query(DeliveryJob).filter(DeliveryJob.id == delivery_job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="DeliveryJob not found")

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
    job = db.query(DeliveryJob).filter(DeliveryJob.id == delivery_job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="DeliveryJob not found")
    return {"delivery_job": _job_to_dict(job)}


@router.post("/{delivery_job_id}/mark-sent", response_model=DeliveryJobMarkSentOut)
def mark_delivery_job_sent(
    delivery_job_id: str,
    req: DeliveryJobMarkSentIn = DeliveryJobMarkSentIn(),
    db: Session = Depends(get_db),
    admin: str = Depends(get_admin_email),
):
    job = db.query(DeliveryJob).filter(DeliveryJob.id == delivery_job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="DeliveryJob not found")
    if job.status != DeliveryStatus.draft:
        raise HTTPException(status_code=409, detail=f"DeliveryJob is already {job.status.value}")

    from datetime import datetime as dt
    job.status = DeliveryStatus.sent
    job.sent_at = dt.utcnow()

    db.add(AuditLog(
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

    db.commit()
    return {"delivery_job": _job_to_dict(job)}
