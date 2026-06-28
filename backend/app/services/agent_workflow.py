"""Lightweight workflow runner — MVP version without LangGraph."""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import (
    AgentTask, TaskStatus, Artifact, ArtifactType,
    Decision, DecisionStatus, AuditLog, Lead,
)
from app.services.llm import get_llm_provider, LLMProvider


def _utcnow():
    return datetime.utcnow()


def _log(db: Session, lead_id: str, actor: str, action: str, details: dict = None):
    db.add(AuditLog(lead_id=lead_id, actor=actor, action=action, details_json=details))
    db.commit()


def _create_artifact(
    db: Session, lead_id: str, artifact_type: ArtifactType,
    title: str, content_markdown: str, content_json: dict,
    model: str, prompt_version: str, requires_approval: bool = False,
) -> Artifact:
    artifact = Artifact(
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
    db.commit()
    return artifact


def _create_decision(
    db: Session, lead_id: str, artifact_id: str,
    question: str, recommendation: str = "approve",
) -> Decision:
    decision = Decision(
        lead_id=lead_id,
        artifact_id=artifact_id,
        question=question,
        recommendation=recommendation,
    )
    db.add(decision)
    db.commit()
    return decision


def _run_agent(
    db: Session, lead_id: str, agent_name: str, prompt_name: str,
    input_payload: dict, output_schema: dict,
    artifact_type: ArtifactType, artifact_title: str,
    requires_approval: bool = False, decision_question: str | None = None,
) -> dict:
    provider = get_llm_provider()

    task = AgentTask(
        lead_id=lead_id,
        agent_name=agent_name,
        status=TaskStatus.running,
        input_json=input_payload,
        started_at=_utcnow(),
    )
    db.add(task)
    db.commit()

    try:
        output = provider.generate_json(prompt_name, input_payload, output_schema)
        task.status = TaskStatus.succeeded
        task.output_json = output
        task.completed_at = _utcnow()
        db.commit()

        artifact_title = f"{artifact_title}"
        artifact = _create_artifact(
            db, lead_id, artifact_type,
            artifact_title,
            content_markdown=_markdown_from_output(output),
            content_json=output,
            model=f"mock-{prompt_name}-v1",
            prompt_version="v1",
            requires_approval=requires_approval,
        )

        decision = None
        if decision_question:
            decision = _create_decision(
                db, lead_id, artifact.id,
                decision_question,
                "approve",
            )

        _log(db, lead_id, f"agent:{agent_name}", f"agent_completed",
             {"task_id": task.id, "artifact_id": artifact.id})

        return {
            "task": {"id": task.id, "status": task.status.value},
            "artifact": {"id": artifact.id, "type": artifact_type.value, "title": artifact_title},
            "decision": {"id": decision.id, "status": decision.status.value} if decision else None,
        }

    except Exception as e:
        task.status = TaskStatus.failed
        task.error_message = str(e)
        task.completed_at = _utcnow()
        db.commit()
        _log(db, lead_id, f"agent:{agent_name}", "agent_failed",
             {"task_id": task.id, "error": str(e)})
        raise


def run_diagnosis(db: Session, lead_id: str) -> dict:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    payload = {
        "company": lead.company,
        "problem": lead.problem,
        "desired_outcome": lead.desired_outcome,
        "industry": lead.industry,
        "company_size": lead.company_size,
    }
    return _run_agent(
        db, lead_id, "lead_diagnosis", "lead_diagnosis",
        payload, {},
        ArtifactType.requirement_summary, "需求理解",
        requires_approval=False,
        decision_question="是否基于此诊断进入方案设计阶段？",
    )


def run_proposal(db: Session, lead_id: str) -> dict:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    payload = {
        "company": lead.company,
        "problem": lead.problem,
        "desired_outcome": lead.desired_outcome,
    }
    return _run_agent(
        db, lead_id, "proposal", "proposal",
        payload, {},
        ArtifactType.proposal_draft, "方案草案",
        requires_approval=True,
        decision_question="是否批准此方案草案并进入客户沟通？",
    )


def run_intake_response(db: Session, lead_id: str) -> dict:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    payload = {
        "company": lead.company,
        "problem": lead.problem,
        "desired_outcome": lead.desired_outcome,
    }
    output = get_llm_provider().generate_json("intake_response", payload, {})

    task = AgentTask(
        lead_id=lead_id, agent_name="intake_response",
        status=TaskStatus.succeeded,
        input_json=payload, output_json=output,
        started_at=_utcnow(), completed_at=_utcnow(),
    )
    db.add(task)
    db.commit()

    artifacts = []
    decisions = []

    # 1. requirement_summary (no approval needed)
    summary = output.get("requirement_summary", {})
    art = _create_artifact(
        db, lead_id, ArtifactType.requirement_summary,
        "需求理解", str(summary), summary,
        "mock-intake_response-v1", "v1", requires_approval=False,
    )
    artifacts.append({"id": art.id, "type": "requirement_summary"})

    # 2. customer_reply_draft (requires approval)
    reply = output.get("customer_reply_draft", {})
    art = _create_artifact(
        db, lead_id, ArtifactType.customer_reply_draft,
        reply.get("subject", "客户回复草稿"),
        reply.get("body_markdown", str(reply)),
        reply, "mock-intake_response-v1", "v1", requires_approval=True,
    )
    artifacts.append({"id": art.id, "type": "customer_reply_draft"})
    dec = _create_decision(
        db, lead_id, art.id,
        "是否批准此客户回复草稿并发送？",
        "approve",
    )
    decisions.append({"id": dec.id, "question": dec.question})

    # 3. proposal_draft (requires approval)
    proposal = output.get("proposal_draft", {})
    art = _create_artifact(
        db, lead_id, ArtifactType.proposal_draft,
        "方案草案", str(proposal),
        proposal, "mock-intake_response-v1", "v1", requires_approval=True,
    )
    artifacts.append({"id": art.id, "type": "proposal_draft"})
    dec = _create_decision(
        db, lead_id, art.id,
        "是否批准此方案草案并进入下一步？",
        "approve",
    )
    decisions.append({"id": dec.id, "question": dec.question})

    _log(db, lead_id, "agent:intake_response", "intake_response_completed",
         {"task_id": task.id, "artifacts": [a["id"] for a in artifacts]})

    from app.models import LeadStatus
    lead.status = LeadStatus.diagnosed
    db.commit()

    return {
        "task": {"id": task.id, "status": "succeeded"},
        "artifacts": artifacts,
        "decisions": decisions,
    }


def _markdown_from_output(output: dict) -> str:
    """Covert structured output to readable markdown."""
    lines = []
    for key, value in output.items():
        if isinstance(value, list):
            lines.append(f"## {key}")
            for item in value:
                lines.append(f"- {item}")
        elif isinstance(value, dict):
            lines.append(f"## {key}")
            for k, v in value.items():
                lines.append(f"- **{k}**: {v}")
        else:
            lines.append(f"## {key}\n{value}")
    return "\n\n".join(lines)
