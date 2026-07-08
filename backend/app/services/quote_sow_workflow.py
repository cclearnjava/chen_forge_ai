"""Quote/SOW Draft Workflow: Context → Agent → Artifacts → Decision → AuditLog."""

from datetime import datetime
from sqlalchemy.orm import Session
from app.models import (
    AgentProfile, AgentRun, AgentRunStatus, Artifact, ArtifactType,
    AuditLog, Decision, DecisionStatus,
)
from app.services.workspace import get_default_workspace_id
from app.services.quote_sow_context import build_quote_sow_context
from app.services.mock_agents import generate_commercial_review, generate_quote_draft, generate_sow_draft


def _upsert_profile(db: Session, name: str, display_name: str, role: str,
                    allowed_tools: list, output_types: list) -> AgentProfile:
    profile = db.query(AgentProfile).filter(AgentProfile.name == name).first()
    if profile:
        return profile
    profile = AgentProfile(
        name=name, display_name=display_name, role=role,
        allowed_tools_json={"tools": allowed_tools},
        output_artifact_types_json={"types": output_types},
    )
    db.add(profile)
    db.flush()
    return profile


def _create_artifact(db: Session, *, workspace_id: str, agent_run_id: str, opportunity_id: str,
                     lead_id: str | None, artifact_type: ArtifactType,
                     title: str, content_markdown: str, content_json: dict,
                     model: str, prompt_version: str, requires_approval: bool) -> Artifact:
    a = Artifact(
        workspace_id=workspace_id,
        agent_run_id=agent_run_id, opportunity_id=opportunity_id, lead_id=lead_id,
        type=artifact_type, title=title,
        content_markdown=content_markdown, content_json=content_json,
        model=model, prompt_version=prompt_version, requires_approval=requires_approval,
    )
    db.add(a)
    db.flush()
    return a


def run_quote_sow_workflow(db: Session, opportunity_id: str) -> dict:
    ctx = build_quote_sow_context(db, opportunity_id)
    opp = ctx["opportunity"]
    lead_id = ctx["lead_id"]

    wid = opp.workspace_id or get_default_workspace_id(db)
    profile = _upsert_profile(
        db, name="quote_sow_agent", display_name="Quote / SOW Agent",
        role="基于已批准 Proposal 和客户反馈生成报价、SOW 和商业风险审查",
        allowed_tools=["context_builder"],
        output_types=["quote_draft", "sow_draft", "commercial_review"],
    )

    run = AgentRun(
        workspace_id=wid,
        agent_profile_id=profile.id, lead_id=lead_id,
        opportunity_id=opportunity_id, conversation_id=opp.conversation_id,
        status=AgentRunStatus.running, started_at=datetime.utcnow(),
        input_json={"opportunity_id": opportunity_id},
    )
    db.add(run)
    db.flush()

    quote = generate_quote_draft(ctx)
    sow = generate_sow_draft(ctx)
    review = generate_commercial_review(ctx)

    quote_artifact = _create_artifact(
        db, workspace_id=wid, agent_run_id=run.id, opportunity_id=opportunity_id, lead_id=lead_id,
        artifact_type=ArtifactType.quote_draft, title="Quote Draft",
        content_markdown=quote["content_markdown"], content_json=quote["content_json"],
        model="mock-quote-sow-v1", prompt_version="quote_sow.v1", requires_approval=True,
    )

    sow_artifact = _create_artifact(
        db, workspace_id=wid, agent_run_id=run.id, opportunity_id=opportunity_id, lead_id=lead_id,
        artifact_type=ArtifactType.sow_draft, title="SOW Draft",
        content_markdown=sow["content_markdown"], content_json=sow["content_json"],
        model="mock-quote-sow-v1", prompt_version="quote_sow.v1", requires_approval=True,
    )

    review_artifact = _create_artifact(
        db, workspace_id=wid, agent_run_id=run.id, opportunity_id=opportunity_id, lead_id=lead_id,
        artifact_type=ArtifactType.commercial_review, title="Commercial Review",
        content_markdown=review["content_markdown"], content_json=review["content_json"],
        model="mock-quote-sow-v1", prompt_version="quote_sow.v1", requires_approval=False,
    )

    run.status = AgentRunStatus.succeeded
    run.completed_at = datetime.utcnow()
    run.output_json = {
        "quote_artifact_id": quote_artifact.id,
        "sow_artifact_id": sow_artifact.id,
        "review_artifact_id": review_artifact.id,
    }

    decision = Decision(
        workspace_id=wid,
        agent_run_id=run.id, opportunity_id=opportunity_id, lead_id=lead_id,
        artifact_id=quote_artifact.id,
        question="是否批准这份 Quote / SOW 草稿？",
        recommendation="review_before_send",
        status=DecisionStatus.waiting,
    )
    db.add(decision)
    db.flush()

    db.add(AuditLog(
        workspace_id=wid,
        lead_id=lead_id, actor="system:quote_sow_workflow",
        action="quote_sow_generated",
        details_json={
            "opportunity_id": opportunity_id, "agent_run_id": run.id,
            "artifacts": [quote_artifact.id, sow_artifact.id, review_artifact.id],
            "decision_id": decision.id,
        },
    ))

    return {
        "agent_run": run,
        "artifacts": [quote_artifact, sow_artifact, review_artifact],
        "decision": decision,
    }
