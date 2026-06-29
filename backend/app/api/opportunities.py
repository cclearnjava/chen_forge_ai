from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.models import AuditLog, Conversation, Customer, Message, Opportunity, OpportunityStage
from app.schemas import OpportunityUpdate

router = APIRouter(tags=["opportunities"])


@router.get("/admin/opportunities")
def list_opportunities(
    stage: str | None = Query(None),
    q: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    query = db.query(Opportunity).options(joinedload(Opportunity.customer))
    if stage:
        try:
            OpportunityStage(stage)
        except ValueError:
            allowed = [e.value for e in OpportunityStage]
            raise HTTPException(status_code=422, detail=f"Invalid stage. Allowed: {allowed}")
        query = query.filter(Opportunity.stage == stage)
    if q:
        query = query.filter(
            (Opportunity.title.ilike(f"%{q}%"))
            | (Opportunity.customer.has(Customer.name.ilike(f"%{q}%")))
        )
    total = query.count()
    items = (
        query
        .order_by(Opportunity.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    def _to_out(o: Opportunity) -> dict:
        return {
            "id": o.id,
            "customer_id": o.customer_id,
            "lead_id": o.lead_id,
            "title": o.title,
            "stage": o.stage.value if hasattr(o.stage, "value") else o.stage,
            "desired_outcome": o.desired_outcome,
            "problem_summary": o.problem_summary,
            "budget_range": o.budget_range,
            "estimated_value": o.estimated_value,
            "probability": o.probability,
            "next_step": o.next_step,
            "company_name": o.customer.name if o.customer else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "updated_at": o.updated_at.isoformat() if o.updated_at else None,
        }

    return {"items": [_to_out(o) for o in items], "total": total}


@router.get("/admin/opportunities/{opportunity_id}")
def get_opportunity_detail(
    opportunity_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    opp = (
        db.query(Opportunity)
        .options(
            joinedload(Opportunity.customer),
            joinedload(Opportunity.primary_contact),
            joinedload(Opportunity.conversation),
        )
        .filter(Opportunity.id == opportunity_id)
        .first()
    )
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    messages = []
    if opp.conversation:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == opp.conversation.id)
            .order_by(Message.created_at)
            .all()
        )

    return {"opportunity": _opportunity_to_detail(opp, messages)}


@router.patch("/admin/opportunities/{opportunity_id}")
def update_opportunity(
    opportunity_id: str,
    req: OpportunityUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    changes = {}
    if req.stage is not None:
        try:
            opp.stage = OpportunityStage(req.stage)
        except ValueError:
            allowed = [e.value for e in OpportunityStage]
            raise HTTPException(status_code=422, detail=f"Invalid stage. Allowed: {allowed}")
        changes["stage"] = req.stage
    if req.next_step is not None:
        opp.next_step = req.next_step
        changes["next_step"] = req.next_step
    if req.estimated_value is not None:
        opp.estimated_value = req.estimated_value
        changes["estimated_value"] = req.estimated_value
    if req.probability is not None:
        opp.probability = req.probability
        changes["probability"] = req.probability
    if req.desired_outcome is not None:
        opp.desired_outcome = req.desired_outcome
        changes["desired_outcome"] = req.desired_outcome
    if req.problem_summary is not None:
        opp.problem_summary = req.problem_summary
        changes["problem_summary"] = req.problem_summary
    if req.budget_range is not None:
        opp.budget_range = req.budget_range
        changes["budget_range"] = req.budget_range

    if changes:
        db.add(AuditLog(
            lead_id=opp.lead_id,
            actor=_admin,
            action="opportunity_updated",
            details_json={"opportunity_id": opp.id, "changes": changes},
        ))

    db.commit()
    db.refresh(opp)
    return {"opportunity": _opportunity_brief(opp)}


def _opportunity_brief(o: Opportunity) -> dict:
    return {
        "id": o.id,
        "customer_id": o.customer_id,
        "lead_id": o.lead_id,
        "title": o.title,
        "stage": o.stage.value if hasattr(o.stage, "value") else o.stage,
        "desired_outcome": o.desired_outcome,
        "problem_summary": o.problem_summary,
        "budget_range": o.budget_range,
        "estimated_value": o.estimated_value,
        "probability": o.probability,
        "next_step": o.next_step,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
    }


def _opportunity_to_detail(o: Opportunity, messages: list[Message]) -> dict:
    result = {
        "id": o.id,
        "customer_id": o.customer_id,
        "lead_id": o.lead_id,
        "primary_contact_id": o.primary_contact_id,
        "conversation_id": o.conversation_id,
        "title": o.title,
        "stage": o.stage.value if hasattr(o.stage, "value") else o.stage,
        "desired_outcome": o.desired_outcome,
        "problem_summary": o.problem_summary,
        "budget_range": o.budget_range,
        "estimated_value": o.estimated_value,
        "probability": o.probability,
        "next_step": o.next_step,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
        "customer": None,
        "primary_contact": None,
        "conversation": None,
        "recent_messages": [],
    }
    if o.customer:
        result["customer"] = {
            "id": o.customer.id,
            "name": o.customer.name,
            "owner_email": o.customer.owner_email,
            "industry": o.customer.industry,
            "company_size": o.customer.company_size,
            "created_at": o.customer.created_at.isoformat() if o.customer.created_at else None,
        }
    if o.primary_contact:
        result["primary_contact"] = {
            "id": o.primary_contact.id,
            "name": o.primary_contact.name,
            "email": o.primary_contact.email,
            "contact_method": o.primary_contact.contact_method,
            "is_primary": o.primary_contact.is_primary,
        }
    if o.conversation:
        result["conversation"] = {
            "id": o.conversation.id,
            "title": o.conversation.title,
            "channel": o.conversation.channel,
            "status": o.conversation.status.value if hasattr(o.conversation.status, "value") else o.conversation.status,
            "created_at": o.conversation.created_at.isoformat() if o.conversation.created_at else None,
        }
    result["recent_messages"] = [
        {
            "id": m.id,
            "sender_type": m.sender_type.value if hasattr(m.sender_type, "value") else m.sender_type,
            "sender_label": m.sender_label,
            "body_markdown": m.body_markdown,
            "source": m.source,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
    return result
