from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.models import Customer

router = APIRouter(tags=["customers"])


@router.get("/admin/customers")
def list_customers(
    q: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    query = db.query(Customer)
    if q:
        query = query.filter(
            (Customer.name.ilike(f"%{q}%")) | (Customer.owner_email.ilike(f"%{q}%"))
        )
    total = query.count()
    items = (
        query
        .options(joinedload(Customer.contacts), joinedload(Customer.opportunities))
        .order_by(Customer.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    def _to_out(c: Customer) -> dict:
        primary = next((ct for ct in c.contacts if ct.is_primary), None)
        return {
            "id": c.id,
            "name": c.name,
            "owner_email": c.owner_email,
            "industry": c.industry,
            "company_size": c.company_size,
            "primary_contact": {
                "id": primary.id,
                "name": primary.name,
                "email": primary.email,
            } if primary else None,
            "opportunity_count": len(c.opportunities) if c.opportunities else 0,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }

    return {"items": [_to_out(c) for c in items], "total": total}


@router.get("/admin/customers/{customer_id}")
def get_customer_detail(
    customer_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    customer = (
        db.query(Customer)
        .options(
            joinedload(Customer.contacts),
            joinedload(Customer.opportunities),
            joinedload(Customer.conversations),
        )
        .filter(Customer.id == customer_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {"customer": _customer_to_detail(customer)}


def _customer_to_detail(c: Customer) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "owner_email": c.owner_email,
        "industry": c.industry,
        "company_size": c.company_size,
        "source_lead_id": c.source_lead_id,
        "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "contacts": [
            {
                "id": ct.id,
                "customer_id": ct.customer_id,
                "name": ct.name,
                "email": ct.email,
                "contact_method": ct.contact_method,
                "role": ct.role,
                "is_primary": ct.is_primary,
                "source_lead_id": ct.source_lead_id,
                "created_at": ct.created_at.isoformat() if ct.created_at else None,
                "updated_at": ct.updated_at.isoformat() if ct.updated_at else None,
            }
            for ct in (c.contacts or [])
        ],
        "opportunities": [
            {
                "id": o.id,
                "customer_id": o.customer_id,
                "lead_id": o.lead_id,
                "title": o.title,
                "stage": o.stage.value if hasattr(o.stage, "value") else o.stage,
                "desired_outcome": o.desired_outcome,
                "budget_range": o.budget_range,
                "next_step": o.next_step,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "updated_at": o.updated_at.isoformat() if o.updated_at else None,
            }
            for o in (c.opportunities or [])
        ],
        "recent_conversations": [
            {
                "id": conv.id,
                "customer_id": conv.customer_id,
                "lead_id": conv.lead_id,
                "title": conv.title,
                "channel": conv.channel,
                "status": conv.status.value if hasattr(conv.status, "value") else conv.status,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            }
            for conv in (c.conversations or [])
        ],
    }
