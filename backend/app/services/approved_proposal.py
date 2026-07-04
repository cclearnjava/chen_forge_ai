"""Find the latest approved proposal_draft for an Opportunity."""

from sqlalchemy.orm import Session
from app.models import Artifact, ArtifactType, Customer, Decision, DecisionStatus, Opportunity


def find_latest_approved_proposal(db: Session, opportunity_id: str) -> dict | None:
    """Return the latest approved proposal_draft DTO, or None if not found.

    Single JOIN query: Decision(approved + opportunity_id + resolved_at not null)
    JOIN Artifact(type=proposal_draft) ON decision.artifact_id = artifact.id.
    Ordered by Decision.resolved_at desc.
    """
    result = (
        db.query(Decision, Artifact)
        .join(Artifact, Artifact.id == Decision.artifact_id)
        .filter(
            Decision.opportunity_id == opportunity_id,
            Decision.status == DecisionStatus.approved,
            Decision.resolved_at.isnot(None),
            Artifact.type == ArtifactType.proposal_draft,
        )
        .order_by(Decision.resolved_at.desc())
        .first()
    )
    if not result:
        return None

    decision, artifact = result

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
