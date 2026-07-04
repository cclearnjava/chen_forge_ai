"""Find the latest approved proposal_draft for an Opportunity."""

from sqlalchemy.orm import Session
from app.models import Artifact, ArtifactType, Customer, Decision, DecisionStatus, Opportunity


def find_latest_approved_proposal(db: Session, opportunity_id: str) -> dict | None:
    """Return the latest approved proposal_draft DTO, or None if not found.

    Criteria:
      - Artifact.opportunity_id == opportunity_id
      - Artifact.type == proposal_draft
      - Linked Decision.status == approved
      - Decision.resolved_at is not null
      - Ordered by Decision.resolved_at desc
    """
    decision = (
        db.query(Decision)
        .filter(
            Decision.opportunity_id == opportunity_id,
            Decision.status == DecisionStatus.approved,
            Decision.resolved_at.isnot(None),
        )
        .order_by(Decision.resolved_at.desc())
        .first()
    )
    if not decision:
        return None

    artifact = (
        db.query(Artifact)
        .filter(
            Artifact.id == decision.artifact_id,
            Artifact.type == ArtifactType.proposal_draft,
        )
        .first()
    )
    if not artifact:
        return None

    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    customer_name = ""
    opportunity_title = ""
    if opp:
        opportunity_title = opp.title
        if opp.customer_id:
            cust = db.query(Customer).filter(Customer.id == opp.customer_id).first()
            if cust:
                customer_name = cust.name

    return {
        "opportunity_id": opportunity_id,
        "artifact_id": artifact.id,
        "decision_id": decision.id,
        "approved_at": decision.resolved_at.isoformat() if decision.resolved_at else None,
        "title": artifact.title,
        "markdown": artifact.content_markdown or "",
        "content_json": artifact.content_json or {},
        "customer_name": customer_name,
        "opportunity_title": opportunity_title,
    }
