"""Context builder for Quote / SOW Draft Agent — validates all preconditions."""

from sqlalchemy.orm import Session
from app.models import ArtifactType, DeliveryJob, DeliveryStatus, Message
from app.services.agent_context import build_opportunity_agent_context
from app.services.approved_proposal import find_latest_approved_proposal


def build_quote_sow_context(db: Session, opportunity_id: str) -> dict:
    """Build context for Quote/SOW Agent. Fail-closed on missing preconditions."""
    ctx = build_opportunity_agent_context(db, opportunity_id)

    # Latest approved proposal
    proposal = find_latest_approved_proposal(db, opportunity_id)
    if not proposal:
        raise ValueError("No approved proposal found")

    # Must be sent
    sent = (
        db.query(DeliveryJob)
        .filter(
            DeliveryJob.artifact_id == proposal["artifact_id"],
            DeliveryJob.status == DeliveryStatus.sent,
        )
        .first()
    )
    if not sent:
        raise ValueError("Approved proposal has not been sent yet")

    # Must have proposal feedback
    opp = ctx["opportunity"]
    feedback = (
        db.query(Message)
        .filter(
            Message.conversation_id == opp.conversation_id,
            Message.source == "proposal_feedback",
        )
        .order_by(Message.created_at.desc())
        .first()
    )
    if not feedback:
        raise ValueError("No proposal feedback recorded")

    ctx["approved_proposal"] = proposal
    ctx["proposal_sent_job"] = sent
    ctx["latest_proposal_feedback"] = feedback
    return ctx
