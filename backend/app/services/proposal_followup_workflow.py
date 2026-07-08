"""Proposal Follow-up Workflow: Sent Proposal → Feedback → Agent → Artifacts → Decision."""

from datetime import datetime
from sqlalchemy.orm import Session
from app.models import (
    AgentProfile, AgentRun, AgentRunStatus, Artifact, ArtifactType,
    AuditLog, Decision, DecisionStatus,
)
from app.services.workspace import get_default_workspace_id
from app.services.agent_context import build_proposal_followup_context
from app.services.mock_agents import (
    generate_objection_analysis, generate_next_step_recommendation,
    generate_proposal_followup_reply,
)


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


def _create_artifact(db: Session, *, workspace_id: str, agent_run_id: str, opportunity_id: str,
                     lead_id: str | None, artifact_type: ArtifactType,
                     title: str, content_markdown: str, content_json: dict,
                     model: str, prompt_version: str, requires_approval: bool) -> Artifact:
    artifact = Artifact(
        workspace_id=workspace_id,
        agent_run_id=agent_run_id, opportunity_id=opportunity_id, lead_id=lead_id,
        type=artifact_type, title=title,
        content_markdown=content_markdown, content_json=content_json,
        model=model, prompt_version=prompt_version, requires_approval=requires_approval,
    )
    db.add(artifact)
    db.flush()
    return artifact


def run_proposal_followup_workflow(db: Session, opportunity_id: str) -> dict:
    ctx = build_proposal_followup_context(db, opportunity_id)
    opp = ctx["opportunity"]
    lead_id = ctx["lead_id"]

    wid = get_default_workspace_id(db)
    profile = _upsert_agent_profile(
        db, name="proposal_followup_agent", display_name="Proposal Follow-up Agent",
        role="基于已发送 Proposal 和客户反馈生成跟进回复、异议分析和下一步建议",
        allowed_tools=["context_builder"],
        output_types=["proposal_followup_reply_draft", "objection_analysis", "next_step_recommendation"],
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

    reply = generate_proposal_followup_reply(ctx)
    objection = generate_objection_analysis(ctx)
    recommendation = generate_next_step_recommendation(ctx)

    reply_artifact = _create_artifact(
        db, workspace_id=wid, agent_run_id=run.id, opportunity_id=opportunity_id, lead_id=lead_id,
        artifact_type=ArtifactType.proposal_followup_reply_draft,
        title="Proposal Follow-up 回复草稿",
        content_markdown=reply["content_markdown"], content_json=reply["content_json"],
        model="mock-proposal-followup-v1", prompt_version="proposal_followup.v1",
        requires_approval=True,
    )

    objection_artifact = _create_artifact(
        db, workspace_id=wid, agent_run_id=run.id, opportunity_id=opportunity_id, lead_id=lead_id,
        artifact_type=ArtifactType.objection_analysis,
        title="异议分析",
        content_markdown=objection["content_markdown"], content_json=objection["content_json"],
        model="mock-proposal-followup-v1", prompt_version="proposal_followup.v1",
        requires_approval=False,
    )

    recommendation_artifact = _create_artifact(
        db, workspace_id=wid, agent_run_id=run.id, opportunity_id=opportunity_id, lead_id=lead_id,
        artifact_type=ArtifactType.next_step_recommendation,
        title="下一步建议",
        content_markdown=recommendation["content_markdown"], content_json=recommendation["content_json"],
        model="mock-proposal-followup-v1", prompt_version="proposal_followup.v1",
        requires_approval=False,
    )

    run.status = AgentRunStatus.succeeded
    run.completed_at = datetime.utcnow()
    run.output_json = {
        "reply_artifact_id": reply_artifact.id,
        "objection_artifact_id": objection_artifact.id,
        "recommendation_artifact_id": recommendation_artifact.id,
    }

    decision = Decision(
        workspace_id=wid,
        agent_run_id=run.id, opportunity_id=opportunity_id, lead_id=lead_id,
        artifact_id=reply_artifact.id,
        question="是否批准发送这条 Proposal Follow-up 回复草稿？",
        recommendation="review_before_send",
        status=DecisionStatus.waiting,
    )
    db.add(decision)
    db.flush()

    db.add(AuditLog(
        workspace_id=wid,
        lead_id=lead_id, actor="system:proposal_followup_workflow",
        action="proposal_followup_generated",
        details_json={
            "opportunity_id": opportunity_id,
            "agent_run_id": run.id,
            "artifacts": [reply_artifact.id, objection_artifact.id, recommendation_artifact.id],
            "decision_id": decision.id,
        },
    ))

    return {
        "agent_run": run,
        "artifacts": [reply_artifact, objection_artifact, recommendation_artifact],
        "decision": decision,
    }
