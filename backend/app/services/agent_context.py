from sqlalchemy.orm import Session, joinedload
from app.models import Opportunity, Message


def build_opportunity_agent_context(db: Session, opportunity_id: str) -> dict:
    """Read context for an AgentRun on this Opportunity. Fail-closed if not found."""
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
        raise ValueError(f"Opportunity {opportunity_id} not found")

    messages = []
    if opp.conversation:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == opp.conversation.id)
            .order_by(Message.created_at)
            .all()
        )

    return {
        "opportunity": opp,
        "customer": opp.customer,
        "primary_contact": opp.primary_contact,
        "conversation": opp.conversation,
        "messages": messages,
        "lead_id": opp.lead_id,
    }
