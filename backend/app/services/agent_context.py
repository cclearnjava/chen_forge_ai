from sqlalchemy.orm import Session, joinedload
from app.models import Artifact, ArtifactType, Opportunity, Message


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


def build_opportunity_proposal_context(db: Session, opportunity_id: str) -> dict:
    """Extended context for Proposal Agent — includes historical artifacts."""
    ctx = build_opportunity_agent_context(db, opportunity_id)
    opp = ctx["opportunity"]

    customer_reply_draft = (
        db.query(Artifact)
        .filter(
            Artifact.opportunity_id == opportunity_id,
            Artifact.type == ArtifactType.customer_reply_draft,
        )
        .order_by(Artifact.created_at.desc())
        .first()
    )

    discovery_questions = (
        db.query(Artifact)
        .filter(
            Artifact.opportunity_id == opportunity_id,
            Artifact.type == ArtifactType.discovery_questions,
        )
        .order_by(Artifact.created_at.desc())
        .first()
    )

    review = (
        db.query(Artifact)
        .filter(
            Artifact.opportunity_id == opportunity_id,
            Artifact.type == ArtifactType.review,
        )
        .order_by(Artifact.created_at.desc())
        .first()
    )

    ctx["customer_reply_draft"] = customer_reply_draft
    ctx["discovery_questions"] = discovery_questions
    ctx["review"] = review
    return ctx
