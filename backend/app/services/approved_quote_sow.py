"""Find the latest approved quote_draft and sibling sow_draft — workspace-scoped."""

from sqlalchemy.orm import Session
from app.models import Artifact, ArtifactType, Decision, DecisionStatus


def find_latest_approved_quote_sow(db: Session, opportunity_id: str, workspace_id: str) -> dict | None:
    """Return DTO with latest approved quote_draft + same-AgentRun sow_draft, or None.

    Requires workspace_id — filters quote, sibling SOW, and ensures same workspace.
    """
    result = (
        db.query(Decision, Artifact)
        .join(Artifact, Artifact.id == Decision.artifact_id)
        .filter(
            Decision.opportunity_id == opportunity_id,
            Decision.status == DecisionStatus.approved,
            Decision.resolved_at.isnot(None),
            Artifact.type == ArtifactType.quote_draft,
            (Artifact.workspace_id == workspace_id) | (Artifact.workspace_id.is_(None)),
            (Decision.workspace_id == workspace_id) | (Decision.workspace_id.is_(None)),
        )
        .order_by(Decision.resolved_at.desc())
        .first()
    )
    if not result:
        return None

    decision, quote = result
    sow = (
        db.query(Artifact)
        .filter(
            Artifact.agent_run_id == quote.agent_run_id,
            Artifact.opportunity_id == opportunity_id,
            Artifact.type == ArtifactType.sow_draft,
            (Artifact.workspace_id == workspace_id) | (Artifact.workspace_id.is_(None)),
        )
        .first()
    )
    if not sow:
        raise ValueError("Approved quote has no matching SOW draft")

    return {
        "quote_artifact_id": quote.id,
        "sow_artifact_id": sow.id,
        "agent_run_id": quote.agent_run_id,
        "opportunity_id": opportunity_id,
        "lead_id": quote.lead_id,
        "quote_title": quote.title,
        "sow_title": sow.title,
        "quote_markdown": quote.content_markdown or "",
        "sow_markdown": sow.content_markdown or "",
        "approved_at": decision.resolved_at.isoformat() if decision.resolved_at else None,
    }
