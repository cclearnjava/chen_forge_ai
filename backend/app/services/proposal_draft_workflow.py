"""Proposal Draft Workflow: Opportunity → Proposal Agent → Artifact → Decision → AuditLog."""

from datetime import datetime
from sqlalchemy.orm import Session
from app.models import (
    AgentProfile, AgentRun, AgentRunStatus, Artifact, ArtifactType,
    AuditLog, Decision, DecisionStatus,
)
from app.services.workspace import get_default_workspace_id
from app.services.agent_context import build_opportunity_proposal_context
from app.services.mock_agents import generate_proposal_draft


def _upsert_agent_profile(db: Session, name: str, display_name: str, role: str,
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


def run_proposal_draft_workflow(db: Session, opportunity_id: str) -> dict:
    ctx = build_opportunity_proposal_context(db, opportunity_id)
    opp = ctx["opportunity"]
    lead_id = ctx["lead_id"]

    wid = get_default_workspace_id(db)
    profile = _upsert_agent_profile(
        db, name="proposal_agent", display_name="Proposal Agent",
        role="基于客户对话和商机上下文生成 PoC 方案草案",
        allowed_tools=["context_builder"],
        output_types=["proposal_draft"],
    )

    run = AgentRun(
        workspace_id=wid,
        agent_profile_id=profile.id,
        lead_id=lead_id,
        opportunity_id=opportunity_id,
        conversation_id=opp.conversation_id,
        status=AgentRunStatus.running,
        started_at=datetime.utcnow(),
        input_json={"opportunity_id": opportunity_id},
    )
    db.add(run)
    db.flush()

    draft = generate_proposal_draft(ctx)

    artifact = Artifact(
        workspace_id=wid,
        agent_run_id=run.id,
        opportunity_id=opportunity_id,
        lead_id=lead_id,
        type=ArtifactType.proposal_draft,
        title="PoC 方案草案",
        content_markdown=draft["content_markdown"],
        content_json=draft["content_json"],
        model="mock-proposal-agent-v1",
        prompt_version="proposal_draft.v1",
        requires_approval=True,
    )
    db.add(artifact)
    db.flush()

    run.status = AgentRunStatus.succeeded
    run.completed_at = datetime.utcnow()
    run.output_json = {"artifact_id": artifact.id}

    decision = Decision(
        workspace_id=wid,
        agent_run_id=run.id,
        opportunity_id=opportunity_id,
        lead_id=lead_id,
        artifact_id=artifact.id,
        question="是否批准这份 PoC 方案草案？",
        recommendation="review_before_send",
        status=DecisionStatus.waiting,
    )
    db.add(decision)
    db.flush()

    db.add(AuditLog(
        workspace_id=wid,
        lead_id=lead_id,
        actor="system:proposal_draft_workflow",
        action="proposal_draft_generated",
        details_json={
            "opportunity_id": opportunity_id,
            "agent_run_id": run.id,
            "artifact_id": artifact.id,
            "decision_id": decision.id,
        },
    ))

    return {
        "agent_run": run,
        "artifact": artifact,
        "decision": decision,
    }
