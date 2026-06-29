from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.middleware import get_admin_email, get_current_email
from app.schemas import LeadCreate, LeadUpdate, LeadOut, AttachmentOut, PaginatedResponse
from app.models import Lead, LeadAttachment, LeadStatus
from app.services.customer_lifecycle import create_lifecycle_from_lead
from app.config import settings
import os
import uuid

router = APIRouter(tags=["leads"])

ALLOWED_TYPES = {
    "application/pdf", "image/png", "image/jpeg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.post("/leads", status_code=201)
def create_lead(req: LeadCreate, db: Session = Depends(get_db), email: str = Depends(get_current_email)):
    if req.honeypot:
        raise HTTPException(status_code=400, detail="Invalid request")

    if req.submitted_after_ms < 1500:
        raise HTTPException(status_code=400, detail="Too fast")

    if req.owner_email != email:
        raise HTTPException(status_code=403, detail="Email mismatch")

    lead = Lead(
        owner_email=req.owner_email,
        company=req.company,
        contact_name=req.contact_name,
        contact_method=req.contact_method,
        industry=req.industry,
        problem=req.problem,
        desired_outcome=req.desired_outcome,
        company_size=req.company_size,
        budget_range=req.budget_range,
        timeline=req.timeline,
        video_links=req.video_links,
    )
    db.add(lead)
    db.flush()

    lifecycle = create_lifecycle_from_lead(db, lead.id)
    db.commit()

    return {"lead": _lead_to_dict(lead), "lifecycle": lifecycle}


@router.get("/admin/leads")
def list_leads(
    status: str | None = Query(None),
    q: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    query = db.query(Lead)
    if status:
        query = query.filter(Lead.status == status)
    if q:
        query = query.filter(
            (Lead.company.ilike(f"%{q}%")) | (Lead.problem.ilike(f"%{q}%"))
        )
    total = query.count()
    items = query.order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [_lead_to_dict(l) for l in items], "total": total}


@router.get("/admin/leads/{lead_id}")
def get_lead_detail(
    lead_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    attachments = db.query(LeadAttachment).filter(LeadAttachment.lead_id == lead_id).all()
    return {
        "lead": _lead_to_dict(lead),
        "attachments": [_attachment_to_dict(a) for a in attachments],
    }


@router.patch("/admin/leads/{lead_id}")
def update_lead(
    lead_id: str,
    req: LeadUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if req.status:
        lead.status = LeadStatus(req.status)
    if req.contact_name is not None:
        lead.contact_name = req.contact_name
    if req.contact_method is not None:
        lead.contact_method = req.contact_method
    db.commit()
    return {"lead": _lead_to_dict(lead)}


@router.post("/leads/{lead_id}/attachments", status_code=201)
async def upload_attachment(
    lead_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    email: str = Depends(get_current_email),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.owner_email != email:
        raise HTTPException(status_code=403, detail="Not your lead")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported file type: {file.content_type}")

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=422, detail=f"File exceeds {settings.max_upload_size_mb}MB")

    ext = os.path.splitext(file.filename or "file")[1]
    storage_key = f"uploads/{lead_id}/{uuid.uuid4().hex}{ext}"
    full_path = os.path.join(settings.upload_dir, storage_key)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(content)

    attachment = LeadAttachment(
        lead_id=lead_id,
        filename=file.filename or "file",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        storage_key=storage_key,
        uploaded_by_email=email,
    )
    db.add(attachment)
    db.commit()
    return {"attachment": _attachment_to_dict(attachment)}


def _lead_to_dict(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "owner_email": lead.owner_email,
        "company": lead.company,
        "contact_name": lead.contact_name,
        "contact_method": lead.contact_method,
        "industry": lead.industry,
        "problem": lead.problem,
        "desired_outcome": lead.desired_outcome,
        "company_size": lead.company_size,
        "budget_range": lead.budget_range,
        "timeline": lead.timeline,
        "video_links": lead.video_links,
        "status": lead.status.value if hasattr(lead.status, 'value') else lead.status,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


def _attachment_to_dict(a: LeadAttachment) -> dict:
    return {
        "id": a.id,
        "lead_id": a.lead_id,
        "filename": a.filename,
        "content_type": a.content_type,
        "size_bytes": a.size_bytes,
        "storage_key": a.storage_key,
        "uploaded_by_email": a.uploaded_by_email,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
