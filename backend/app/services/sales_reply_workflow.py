"""Sales Reply Workflow: Opportunity → AgentRun → Artifact → Decision → AuditLog."""

from datetime import datetime
from sqlalchemy.orm import Session
from app.models import (
    AgentProfile, AgentRun, AgentRunStatus, Artifact, ArtifactType,
    AuditLog, Decision, DecisionStatus,
)
from app.services.workspace import get_default_workspace_id
from app.services.context_builder import build_sales_reply_context_pack
from app.services.events import record_event
from app.services.mock_agents import generate_sales_reply, review_sales_reply


def _upsert_agent_profile(db: Session, name: str, display_name: str, role: str,
                          allowed_tools: list, output_types: list) -> AgentProfile:
    profile = db.query(AgentProfile).filter(AgentProfile.name == name).first()
    if profile:
        return profile
    profile = AgentProfile(
        name=name,
        display_name=display_name,
        role=role,
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
        agent_run_id=agent_run_id,
        opportunity_id=opportunity_id,
        lead_id=lead_id,
        type=artifact_type,
        title=title,
        content_markdown=content_markdown,
        content_json=content_json,
        model=model,
        prompt_version=prompt_version,
        requires_approval=requires_approval,
    )
    db.add(artifact)
    db.flush()
    return artifact


def run_sales_reply_workflow(db: Session, opportunity_id: str) -> dict:
    """Execute the full Sales Reply → Quality Review → Decision loop.

    All writes use db.add + db.flush. The caller (API) owns db.commit().
    Any exception leaves no persisted state (fail-closed by caller's rollback).
    """
    # 1. Build context pack (Opportunity + Service Catalog + Knowledge Engine)
    ctx = build_sales_reply_context_pack(db, opportunity_id)
    opp = ctx["opportunity"]
    lead_id = ctx["lead_id"]
    context_usage = ctx.get("usage", {})
    citation_pack = ctx.get("citation_pack", {})

    # 2. Upsert sales_agent profile
    sales_wid = opp.workspace_id or get_default_workspace_id(db)
    sales_profile = _upsert_agent_profile(
        db, name="sales_agent", display_name="Sales Agent",
        role="生成客户回复草稿和澄清问题",
        allowed_tools=["context_builder"],
        output_types=["customer_reply_draft", "discovery_questions"],
    )

    # 3. Create Sales AgentRun
    sales_run = AgentRun(
        workspace_id=sales_wid,
        agent_profile_id=sales_profile.id,
        lead_id=lead_id,
        opportunity_id=opportunity_id,
        conversation_id=opp.conversation_id,
        status=AgentRunStatus.running,
        started_at=datetime.utcnow(),
        input_json={"opportunity_id": opportunity_id},
    )
    db.add(sales_run)
    db.flush()

    # 4. Generate sales reply
    reply = generate_sales_reply(ctx)
    reply_md = reply["customer_reply_draft"]
    questions = reply["discovery_questions"]

    # 5. Create customer_reply_draft Artifact
    draft_artifact = _create_artifact(
        db, workspace_id=sales_wid,
        agent_run_id=sales_run.id,
        opportunity_id=opportunity_id,
        lead_id=lead_id,
        artifact_type=ArtifactType.customer_reply_draft,
        title="客户回复草稿",
        content_markdown=reply_md,
        content_json={"reply": reply_md, "discovery_questions": questions, "context_usage": context_usage, "citations": citation_pack},
        model="mock-sales-agent-v1",
        prompt_version="sales_reply.v1",
        requires_approval=True,
    )

    # 6. Create discovery_questions Artifact
    questions_artifact = _create_artifact(
        db, workspace_id=sales_wid,
        agent_run_id=sales_run.id,
        opportunity_id=opportunity_id,
        lead_id=lead_id,
        artifact_type=ArtifactType.discovery_questions,
        title="澄清问题",
        content_markdown="\n\n".join(f"- {q}" for q in questions),
        content_json={"questions": questions},
        model="mock-sales-agent-v1",
        prompt_version="sales_reply.v1",
        requires_approval=False,
    )

    # Mark sales run succeeded
    sales_run.status = AgentRunStatus.succeeded
    sales_run.completed_at = datetime.utcnow()
    sales_run.output_json = {
        "draft_artifact_id": draft_artifact.id,
        "questions_artifact_id": questions_artifact.id,
        "discovery_questions_count": len(questions),
        "context_usage": context_usage,
        "citation_count": citation_pack.get("hit_count", 0),
        "retriever_version": citation_pack.get("retriever_version"),
    }

    # Record context_pack.built event (no notification rule → event only)
    record_event(
        db, workspace_id=sales_wid, type="context_pack.built", source="sales_reply_workflow",
        subject_type="opportunity", subject_id=opportunity_id,
        title="Context Pack built for sales reply",
        payload_json={
            "service_hit_count": context_usage.get("service_hit_count", 0),
            "knowledge_hit_count": context_usage.get("knowledge_hit_count", 0),
            "context_builder_version": context_usage.get("context_builder_version"),
        },
    )

    # 7. Upsert quality_agent profile
    quality_wid = opp.workspace_id or get_default_workspace_id(db)
    quality_profile = _upsert_agent_profile(
        db, name="quality_agent", display_name="Quality Agent",
        role="审查客户回复草稿中的风险",
        allowed_tools=["risk_rules"],
        output_types=["review"],
    )

    # 8. Create Quality AgentRun
    quality_run = AgentRun(
        workspace_id=quality_wid,
        agent_profile_id=quality_profile.id,
        lead_id=lead_id,
        opportunity_id=opportunity_id,
        conversation_id=opp.conversation_id,
        status=AgentRunStatus.running,
        started_at=datetime.utcnow(),
        input_json={"artifact_id": draft_artifact.id},
    )
    db.add(quality_run)
    db.flush()

    # 9. Review
    review = review_sales_reply(reply_md)

    # 10. Create review Artifact
    review_artifact = _create_artifact(
        db, workspace_id=sales_wid,
        agent_run_id=quality_run.id,
        opportunity_id=opportunity_id,
        lead_id=lead_id,
        artifact_type=ArtifactType.review,
        title="Quality Review",
        content_markdown=f"风险等级: {review['risk_level']}\n\n{review['summary']}",
        content_json=review,
        model="mock-quality-agent-v1",
        prompt_version="quality_review.v1",
        requires_approval=False,
    )

    # Mark quality run succeeded
    quality_run.status = AgentRunStatus.succeeded
    quality_run.completed_at = datetime.utcnow()
    quality_run.output_json = {
        "review_artifact_id": review_artifact.id,
        "risk_level": review["risk_level"],
        "flag_count": len(review["risk_flags"]),
    }

    # 11. Create waiting Decision
    decision = Decision(
        workspace_id=sales_wid,
        agent_run_id=sales_run.id,
        opportunity_id=opportunity_id,
        lead_id=lead_id,
        artifact_id=draft_artifact.id,
        question="是否批准发送这条客户回复草稿？",
        recommendation=review["recommendation"],
        status=DecisionStatus.waiting,
    )
    db.add(decision)
    db.flush()

    # 12. AuditLog
    db.add(AuditLog(
        workspace_id=sales_wid,
        lead_id=lead_id,
        actor="system:sales_reply_workflow",
        action="sales_reply_workflow_completed",
        details_json={
            "opportunity_id": opportunity_id,
            "sales_agent_run_id": sales_run.id,
            "quality_agent_run_id": quality_run.id,
            "artifacts": [draft_artifact.id, questions_artifact.id, review_artifact.id],
            "decision_id": decision.id,
        },
    ))
    db.flush()

    return {
        "sales_agent_run": sales_run,
        "quality_agent_run": quality_run,
        "artifacts": [draft_artifact, questions_artifact, review_artifact],
        "quality_review": review,
        "decision": decision,
    }
