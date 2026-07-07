from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.models import (
    AgentRun, Artifact, ArtifactType, AuditLog, Contact, Conversation, Customer,
    Decision, DeliveryChannel, DeliveryJob, DeliveryStatus, Message,
    MessageSenderType, Opportunity, OpportunityStage,
)
from app.schemas import (
    AdminOpportunityCockpitOut, OpportunityMessageCreateIn,
    OpportunityMessageCreateOut, OpportunityUpdate,
    ProposalDraftResponseOut,
)
from app.services.approved_proposal import find_latest_approved_proposal
from app.services.proposal_draft_workflow import run_proposal_draft_workflow
from app.services.proposal_followup_workflow import run_proposal_followup_workflow
from app.services.approved_quote_sow import find_latest_approved_quote_sow
from app.services.quote_sow_workflow import run_quote_sow_workflow
from app.services.proposal_pdf_renderer import render_approved_proposal_pdf
from app.services.proposal_pdf_storage import storage as pdf_storage
from app.services.sales_reply_workflow import run_sales_reply_workflow


class SalesReplyRequest(BaseModel):
    opportunity_id: str


router = APIRouter(tags=["opportunities"])


@router.get("/admin/opportunities")
def list_opportunities(
    stage: str | None = Query(None),
    q: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    query = db.query(Opportunity).options(joinedload(Opportunity.customer))
    if stage:
        try:
            OpportunityStage(stage)
        except ValueError:
            allowed = [e.value for e in OpportunityStage]
            raise HTTPException(status_code=422, detail=f"Invalid stage. Allowed: {allowed}")
        query = query.filter(Opportunity.stage == stage)
    if q:
        query = query.filter(
            (Opportunity.title.ilike(f"%{q}%"))
            | (Opportunity.customer.has(Customer.name.ilike(f"%{q}%")))
        )
    total = query.count()
    items = (
        query
        .order_by(Opportunity.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    def _to_out(o: Opportunity) -> dict:
        return {
            "id": o.id,
            "customer_id": o.customer_id,
            "lead_id": o.lead_id,
            "title": o.title,
            "stage": o.stage.value if hasattr(o.stage, "value") else o.stage,
            "desired_outcome": o.desired_outcome,
            "problem_summary": o.problem_summary,
            "budget_range": o.budget_range,
            "estimated_value": o.estimated_value,
            "probability": o.probability,
            "next_step": o.next_step,
            "company_name": o.customer.name if o.customer else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "updated_at": o.updated_at.isoformat() if o.updated_at else None,
        }

    return {"items": [_to_out(o) for o in items], "total": total}


@router.get("/admin/opportunities/{opportunity_id}")
def get_opportunity_detail(
    opportunity_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
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
        raise HTTPException(status_code=404, detail="Opportunity not found")

    messages = []
    if opp.conversation:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == opp.conversation.id)
            .order_by(Message.created_at)
            .all()
        )

    # BE-10: collect agent output data in endpoint (db is available here)
    agent_runs = (
        db.query(AgentRun)
        .filter(AgentRun.opportunity_id == opportunity_id)
        .order_by(AgentRun.created_at.desc())
        .all()
    )
    artifacts = (
        db.query(Artifact)
        .filter(Artifact.opportunity_id == opportunity_id)
        .order_by(Artifact.created_at.desc())
        .all()
    )
    decisions = (
        db.query(Decision)
        .filter(Decision.opportunity_id == opportunity_id)
        .order_by(Decision.created_at.desc())
        .all()
    )
    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.lead_id == opp.lead_id)
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )

    return {"opportunity": _opportunity_to_detail(opp, messages, agent_runs, artifacts, decisions, audit_logs)}


@router.patch("/admin/opportunities/{opportunity_id}")
def update_opportunity(
    opportunity_id: str,
    req: OpportunityUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    changes = {}
    if req.stage is not None:
        try:
            opp.stage = OpportunityStage(req.stage)
        except ValueError:
            allowed = [e.value for e in OpportunityStage]
            raise HTTPException(status_code=422, detail=f"Invalid stage. Allowed: {allowed}")
        changes["stage"] = req.stage
    if req.next_step is not None:
        opp.next_step = req.next_step
        changes["next_step"] = req.next_step
    if req.estimated_value is not None:
        opp.estimated_value = req.estimated_value
        changes["estimated_value"] = req.estimated_value
    if req.probability is not None:
        opp.probability = req.probability
        changes["probability"] = req.probability
    if req.desired_outcome is not None:
        opp.desired_outcome = req.desired_outcome
        changes["desired_outcome"] = req.desired_outcome
    if req.problem_summary is not None:
        opp.problem_summary = req.problem_summary
        changes["problem_summary"] = req.problem_summary
    if req.budget_range is not None:
        opp.budget_range = req.budget_range
        changes["budget_range"] = req.budget_range

    if changes:
        db.add(AuditLog(
            lead_id=opp.lead_id,
            actor=_admin,
            action="opportunity_updated",
            details_json={"opportunity_id": opp.id, "changes": changes},
        ))

    db.commit()
    db.refresh(opp)
    return {"opportunity": _opportunity_brief(opp)}


def _opportunity_brief(o: Opportunity) -> dict:
    return {
        "id": o.id,
        "customer_id": o.customer_id,
        "lead_id": o.lead_id,
        "title": o.title,
        "stage": o.stage.value if hasattr(o.stage, "value") else o.stage,
        "desired_outcome": o.desired_outcome,
        "problem_summary": o.problem_summary,
        "budget_range": o.budget_range,
        "estimated_value": o.estimated_value,
        "probability": o.probability,
        "next_step": o.next_step,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
    }


def _opportunity_to_detail(o: Opportunity, messages: list[Message],
                          agent_runs: list, artifacts: list,
                          decisions: list, audit_logs: list) -> dict:
    result = {
        "id": o.id,
        "customer_id": o.customer_id,
        "lead_id": o.lead_id,
        "primary_contact_id": o.primary_contact_id,
        "conversation_id": o.conversation_id,
        "title": o.title,
        "stage": o.stage.value if hasattr(o.stage, "value") else o.stage,
        "desired_outcome": o.desired_outcome,
        "problem_summary": o.problem_summary,
        "budget_range": o.budget_range,
        "estimated_value": o.estimated_value,
        "probability": o.probability,
        "next_step": o.next_step,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
        "customer": None,
        "primary_contact": None,
        "conversation": None,
        "recent_messages": [],
    }
    if o.customer:
        result["customer"] = {
            "id": o.customer.id,
            "name": o.customer.name,
            "owner_email": o.customer.owner_email,
            "industry": o.customer.industry,
            "company_size": o.customer.company_size,
            "created_at": o.customer.created_at.isoformat() if o.customer.created_at else None,
        }
    if o.primary_contact:
        result["primary_contact"] = {
            "id": o.primary_contact.id,
            "name": o.primary_contact.name,
            "email": o.primary_contact.email,
            "contact_method": o.primary_contact.contact_method,
            "is_primary": o.primary_contact.is_primary,
        }
    if o.conversation:
        result["conversation"] = {
            "id": o.conversation.id,
            "title": o.conversation.title,
            "channel": o.conversation.channel,
            "status": o.conversation.status.value if hasattr(o.conversation.status, "value") else o.conversation.status,
            "created_at": o.conversation.created_at.isoformat() if o.conversation.created_at else None,
        }
    result["recent_messages"] = [
        {
            "id": m.id,
            "sender_type": m.sender_type.value if hasattr(m.sender_type, "value") else m.sender_type,
            "sender_label": m.sender_label,
            "body_markdown": m.body_markdown,
            "source": m.source,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
    # BE-10: append agent_runs, artifacts, decisions, audit_logs (from params)
    result["agent_runs"] = [
        {
            "id": r.id,
            "agent_profile_id": r.agent_profile_id,
            "status": r.status.value if hasattr(r.status, "value") else r.status,
            "input_json": r.input_json,
            "output_json": r.output_json,
            "error_message": r.error_message,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in agent_runs
    ]

    result["artifacts"] = [
        {
            "id": a.id,
            "agent_run_id": a.agent_run_id,
            "type": a.type.value if hasattr(a.type, "value") else a.type,
            "title": a.title,
            "content_markdown": a.content_markdown,
            "content_json": a.content_json,
            "model": a.model,
            "prompt_version": a.prompt_version,
            "requires_approval": a.requires_approval,
            "approved_at": a.approved_at.isoformat() if a.approved_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in artifacts
    ]

    result["decisions"] = [
        {
            "id": d.id,
            "agent_run_id": d.agent_run_id,
            "artifact_id": d.artifact_id,
            "question": d.question,
            "recommendation": d.recommendation,
            "status": d.status.value if hasattr(d.status, "value") else d.status,
            "operator_note": d.operator_note,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
        }
        for d in decisions
    ]

    result["audit_logs"] = [
        {
            "id": log.id,
            "actor": log.actor,
            "action": log.action,
            "details_json": log.details_json,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in audit_logs
    ]

    return result


# ── BE-09: Trigger Sales Reply Workflow ──

@router.post("/admin/agent-runs/sales-reply")
def trigger_sales_reply(
    req: SalesReplyRequest,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    opp = db.query(Opportunity).filter(Opportunity.id == req.opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    try:
        result = run_sales_reply_workflow(db, req.opportunity_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Workflow execution failed")

    def _run_to_dict(run):
        return {
            "id": run.id,
            "agent_profile_id": run.agent_profile_id,
            "status": run.status.value if hasattr(run.status, "value") else run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }

    def _artifact_to_dict(a):
        return {
            "id": a.id,
            "agent_run_id": a.agent_run_id,
            "type": a.type.value if hasattr(a.type, "value") else a.type,
            "title": a.title,
            "content_markdown": a.content_markdown,
            "content_json": a.content_json,
            "model": a.model,
            "requires_approval": a.requires_approval,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }

    return {
        "agent_runs": [_run_to_dict(result["sales_agent_run"]), _run_to_dict(result["quality_agent_run"])],
        "artifacts": [_artifact_to_dict(a) for a in result["artifacts"]],
        "quality_review": result["quality_review"],
        "decision": {
            "id": result["decision"].id,
            "question": result["decision"].question,
            "recommendation": result["decision"].recommendation,
            "status": result["decision"].status.value if hasattr(result["decision"].status, "value") else result["decision"].status,
        },
    }


# ── BE-02: Admin Cockpit Aggregation ──

def _to_iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def _enum_value(v) -> str:
    return v.value if hasattr(v, "value") else str(v)


@router.get("/admin/opportunities/{opportunity_id}/cockpit", response_model=AdminOpportunityCockpitOut)
def get_opportunity_cockpit(
    opportunity_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Customer and Contact (fail-soft)
    customer_dict = None
    if opp.customer_id:
        cust = db.query(Customer).filter(Customer.id == opp.customer_id).first()
        if cust:
            customer_dict = {
                "id": cust.id, "name": cust.name, "owner_email": cust.owner_email,
                "industry": cust.industry, "company_size": cust.company_size,
                "source_lead_id": cust.source_lead_id,
                "created_at": _to_iso(cust.created_at), "updated_at": _to_iso(cust.updated_at),
            }

    contact_dict = None
    if opp.primary_contact_id:
        ct = db.query(Contact).filter(Contact.id == opp.primary_contact_id).first()
        if ct:
            contact_dict = {
                "id": ct.id, "customer_id": ct.customer_id, "name": ct.name,
                "email": ct.email, "contact_method": ct.contact_method,
                "role": ct.role, "is_primary": ct.is_primary,
                "created_at": _to_iso(ct.created_at), "updated_at": _to_iso(ct.updated_at),
            }

    # Conversation + Messages (fail-soft)
    conversation_dict = None
    messages = []
    if opp.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == opp.conversation_id).first()
        if conv:
            conversation_dict = {
                "id": conv.id, "customer_id": conv.customer_id,
                "lead_id": conv.lead_id, "title": conv.title,
                "channel": conv.channel, "status": _enum_value(conv.status),
                "created_at": _to_iso(conv.created_at), "updated_at": _to_iso(conv.updated_at),
            }
            messages = [
                {
                    "id": m.id, "conversation_id": m.conversation_id,
                    "sender_type": _enum_value(m.sender_type),
                    "sender_label": m.sender_label, "body_markdown": m.body_markdown,
                    "source": m.source, "created_at": _to_iso(m.created_at),
                }
                for m in db.query(Message)
                .filter(Message.conversation_id == opp.conversation_id)
                .order_by(Message.created_at.asc())
                .all()
            ]

    # Artifacts by opportunity_id (desc)
    artifacts = [
        {
            "id": a.id, "agent_run_id": a.agent_run_id,
            "type": _enum_value(a.type), "title": a.title,
            "content_markdown": a.content_markdown, "content_json": a.content_json,
            "model": a.model, "prompt_version": a.prompt_version,
            "requires_approval": a.requires_approval,
            "created_at": _to_iso(a.created_at),
        }
        for a in db.query(Artifact)
        .filter(Artifact.opportunity_id == opportunity_id)
        .order_by(Artifact.created_at.desc())
        .all()
    ]

    # Decisions by opportunity_id (desc)
    decisions = [
        {
            "id": d.id, "agent_run_id": d.agent_run_id,
            "opportunity_id": d.opportunity_id,
            "artifact_id": d.artifact_id, "question": d.question,
            "recommendation": d.recommendation, "status": _enum_value(d.status),
            "operator_note": d.operator_note,
            "created_at": _to_iso(d.created_at), "resolved_at": _to_iso(d.resolved_at),
        }
        for d in db.query(Decision)
        .filter(Decision.opportunity_id == opportunity_id)
        .order_by(Decision.created_at.desc())
        .all()
    ]

    # DeliveryJobs — traced through artifacts of this opportunity
    artifact_ids = [a["id"] for a in artifacts]
    delivery_jobs = []
    if artifact_ids:
        delivery_jobs = [
            {
                "id": j.id, "lead_id": j.lead_id, "artifact_id": j.artifact_id,
                "channel": _enum_value(j.channel), "recipient": j.recipient,
                "subject": j.subject, "body_markdown": j.body_markdown,
                "status": _enum_value(j.status),
                "created_at": _to_iso(j.created_at), "sent_at": _to_iso(j.sent_at),
            }
            for j in db.query(DeliveryJob)
            .filter(DeliveryJob.artifact_id.in_(artifact_ids))
            .order_by(DeliveryJob.created_at.desc())
            .all()
        ]

    # AuditLogs — by lead_id (current approach, same as detail)
    audit_logs = [
        {
            "id": log.id, "actor": log.actor, "action": log.action,
            "details_json": log.details_json, "created_at": _to_iso(log.created_at),
        }
        for log in db.query(AuditLog)
        .filter(AuditLog.lead_id == opp.lead_id)
        .order_by(AuditLog.created_at.desc())
        .limit(30)
        .all()
    ]

    # AgentRuns by opportunity_id (desc)
    agent_runs = [
        {
            "id": r.id, "agent_profile_id": r.agent_profile_id,
            "status": _enum_value(r.status), "input_json": r.input_json,
            "output_json": r.output_json, "error_message": r.error_message,
            "started_at": _to_iso(r.started_at), "completed_at": _to_iso(r.completed_at),
            "created_at": _to_iso(r.created_at),
        }
        for r in db.query(AgentRun)
        .filter(AgentRun.opportunity_id == opportunity_id)
        .order_by(AgentRun.created_at.desc())
        .all()
    ]

    return {
        "opportunity": {
            "id": opp.id, "customer_id": opp.customer_id,
            "lead_id": opp.lead_id, "primary_contact_id": opp.primary_contact_id,
            "conversation_id": opp.conversation_id, "title": opp.title,
            "stage": _enum_value(opp.stage), "desired_outcome": opp.desired_outcome,
            "problem_summary": opp.problem_summary, "budget_range": opp.budget_range,
            "estimated_value": opp.estimated_value, "probability": opp.probability,
            "next_step": opp.next_step,
            "created_at": _to_iso(opp.created_at), "updated_at": _to_iso(opp.updated_at),
        },
        "customer": customer_dict,
        "contact": contact_dict,
        "conversation": conversation_dict,
        "messages": messages,
        "artifacts": artifacts,
        "decisions": decisions,
        "delivery_jobs": delivery_jobs,
        "audit_logs": audit_logs,
        "agent_runs": agent_runs,
    }


# ── BE-02: Record Customer Reply ──

@router.post("/admin/opportunities/{opportunity_id}/messages", status_code=201, response_model=OpportunityMessageCreateOut)
def record_customer_reply(
    opportunity_id: str,
    req: OpportunityMessageCreateIn,
    db: Session = Depends(get_db),
    admin: str = Depends(get_admin_email),
):
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if not opp.conversation_id:
        raise HTTPException(status_code=422, detail="Opportunity has no linked conversation")

    conv = db.query(Conversation).filter(Conversation.id == opp.conversation_id).first()
    if not conv:
        raise HTTPException(status_code=422, detail="Conversation not found")

    message = Message(
        conversation_id=opp.conversation_id,
        customer_id=opp.customer_id,
        contact_id=opp.primary_contact_id,
        sender_type=MessageSenderType.customer,
        sender_label=req.sender_label or "客户回复",
        body_markdown=req.body_markdown,
        source="manual",
    )
    db.add(message)
    db.flush()

    opp.next_step = "Review customer reply"

    db.add(AuditLog(
        lead_id=opp.lead_id,
        actor=admin,
        action="customer_message_recorded",
        details_json={
            "opportunity_id": opp.id,
            "conversation_id": opp.conversation_id,
            "message_id": message.id,
            "sender_type": "customer",
            "source": "manual",
        },
    ))

    db.commit()

    return {
        "message": {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "sender_type": _enum_value(message.sender_type),
            "sender_label": message.sender_label,
            "body_markdown": message.body_markdown,
            "source": message.source,
            "created_at": _to_iso(message.created_at),
        },
        "opportunity": {
            "id": opp.id,
            "next_step": opp.next_step,
        },
    }


# ── BE-05: Proposal Draft ──

class ProposalDraftRequest(BaseModel):
    opportunity_id: str


@router.post("/admin/agent-runs/proposal-draft", response_model=ProposalDraftResponseOut)
def trigger_proposal_draft(
    req: ProposalDraftRequest,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    opp = db.query(Opportunity).filter(Opportunity.id == req.opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    try:
        result = run_proposal_draft_workflow(db, req.opportunity_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Workflow execution failed")

    r = result
    return {
        "agent_run": {
            "id": r["agent_run"].id,
            "agent_profile_id": r["agent_run"].agent_profile_id,
            "status": _enum_value(r["agent_run"].status),
            "started_at": _to_iso(r["agent_run"].started_at),
            "completed_at": _to_iso(r["agent_run"].completed_at),
        },
        "artifact": {
            "id": r["artifact"].id,
            "agent_run_id": r["artifact"].agent_run_id,
            "type": _enum_value(r["artifact"].type),
            "title": r["artifact"].title,
            "content_markdown": r["artifact"].content_markdown,
            "content_json": r["artifact"].content_json,
            "model": r["artifact"].model,
            "requires_approval": r["artifact"].requires_approval,
            "created_at": _to_iso(r["artifact"].created_at),
        },
        "decision": {
            "id": r["decision"].id,
            "question": r["decision"].question,
            "recommendation": r["decision"].recommendation,
            "status": _enum_value(r["decision"].status),
        },
    }


# ── BE-02/03: Approved Proposal JSON + PDF ──

@router.get("/admin/opportunities/{opportunity_id}/approved-proposal")
def get_approved_proposal(
    opportunity_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    data = find_latest_approved_proposal(db, opportunity_id)
    if not data:
        raise HTTPException(status_code=404, detail="No approved proposal found for this opportunity")
    return data


@router.get("/admin/opportunities/{opportunity_id}/approved-proposal.pdf")
def download_approved_proposal_pdf(
    opportunity_id: str,
    db: Session = Depends(get_db),
    admin: str = Depends(get_admin_email),
):
    data = find_latest_approved_proposal(db, opportunity_id)
    if not data:
        raise HTTPException(status_code=404, detail="No approved proposal found for this opportunity")

    try:
        pdf_bytes = render_approved_proposal_pdf(data)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    db.add(AuditLog(
        lead_id=None,
        actor=admin,
        action="approved_proposal_pdf_downloaded",
        details_json={
            "opportunity_id": opportunity_id,
            "artifact_id": data["artifact_id"],
            "decision_id": data["decision_id"],
        },
    ))
    db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=chenforge-proposal-{opportunity_id[:8]}.pdf"
        },
    )


# ── BE-01: Proposal Delivery Job ──

class ProposalDeliveryRequest(BaseModel):
    operator_note: str = ""


@router.post("/admin/opportunities/{opportunity_id}/approved-proposal/delivery-job")
def create_proposal_delivery_job(
    opportunity_id: str,
    req: ProposalDeliveryRequest = ProposalDeliveryRequest(),
    db: Session = Depends(get_db),
    admin: str = Depends(get_admin_email),
):
    # Find latest approved proposal
    data = find_latest_approved_proposal(db, opportunity_id)
    if not data:
        raise HTTPException(status_code=404, detail="No approved proposal found for this opportunity")

    artifact_id = data["artifact_id"]

    # Check for existing draft DeliveryJob for this artifact
    existing = (
        db.query(DeliveryJob)
        .filter(DeliveryJob.artifact_id == artifact_id, DeliveryJob.status == DeliveryStatus.draft)
        .first()
    )
    if existing:
        return JSONResponse(content={"delivery_job": {
            "id": existing.id, "lead_id": existing.lead_id,
            "artifact_id": existing.artifact_id,
            "channel": _enum_value(existing.channel),
            "recipient": existing.recipient, "subject": existing.subject,
            "body_markdown": existing.body_markdown,
            "status": _enum_value(existing.status),
            "created_at": _to_iso(existing.created_at),
            "sent_at": _to_iso(existing.sent_at),
        }}, status_code=200)

    # Ensure PDF is available
    try:
        render_approved_proposal_pdf(data)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"PDF generation failed: {exc}")

    # Determine recipient
    recipient = data.get("customer_name", "unknown")
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if opp and opp.customer_id:
        cust = db.query(Customer).filter(Customer.id == opp.customer_id).first()
        if cust:
            recipient = cust.owner_email

    job = DeliveryJob(
        lead_id=opp.lead_id if opp else None,
        artifact_id=artifact_id,
        channel=DeliveryChannel.manual_copy,
        recipient=recipient,
        subject=f"PoC Proposal: {data.get('opportunity_title', '')}",
        body_markdown="已准备 PoC Proposal PDF，请下载后通过外部渠道发送给客户。",
        status=DeliveryStatus.draft,
    )
    db.add(job)
    db.flush()

    db.add(AuditLog(
        lead_id=opp.lead_id if opp else None,
        actor=admin,
        action="proposal_delivery_job_created",
        details_json={
            "opportunity_id": opportunity_id,
            "artifact_id": artifact_id,
            "decision_id": data["decision_id"],
            "delivery_job_id": job.id,
            "pdf_storage_key": pdf_storage.path(opportunity_id, artifact_id),
        },
    ))

    db.commit()
    return JSONResponse(content={"delivery_job": {
        "id": job.id, "lead_id": job.lead_id, "artifact_id": job.artifact_id,
        "channel": _enum_value(job.channel),
        "recipient": job.recipient, "subject": job.subject,
        "body_markdown": job.body_markdown,
        "status": _enum_value(job.status),
        "created_at": _to_iso(job.created_at), "sent_at": _to_iso(job.sent_at),
    }}, status_code=201)


# ── BE-02: Record Proposal Feedback ──

class ProposalFeedbackRequest(BaseModel):
    body_markdown: str = Field(..., min_length=1)
    sender_label: str | None = None


@router.post("/admin/opportunities/{opportunity_id}/proposal-feedback", status_code=201)
def record_proposal_feedback(
    opportunity_id: str,
    req: ProposalFeedbackRequest,
    db: Session = Depends(get_db),
    admin: str = Depends(get_admin_email),
):
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if not opp.conversation_id:
        raise HTTPException(status_code=422, detail="Opportunity has no linked conversation")

    # Check latest approved proposal is sent
    proposal_data = find_latest_approved_proposal(db, opportunity_id)
    if not proposal_data:
        raise HTTPException(status_code=422, detail="No approved proposal found")
    sent_job = (
        db.query(DeliveryJob)
        .filter(
            DeliveryJob.artifact_id == proposal_data["artifact_id"],
            DeliveryJob.status == DeliveryStatus.sent,
        )
        .first()
    )
    if not sent_job:
        raise HTTPException(status_code=422, detail="Approved proposal has not been sent yet")

    message = Message(
        conversation_id=opp.conversation_id, customer_id=opp.customer_id,
        contact_id=opp.primary_contact_id, sender_type=MessageSenderType.customer,
        sender_label=req.sender_label or "客户 Proposal 反馈",
        body_markdown=req.body_markdown, source="proposal_feedback",
    )
    db.add(message)
    db.flush()

    opp.next_step = "Review proposal feedback"

    db.add(AuditLog(
        lead_id=opp.lead_id, actor=admin, action="proposal_feedback_recorded",
        details_json={
            "opportunity_id": opp.id, "conversation_id": opp.conversation_id,
            "message_id": message.id, "source": "proposal_feedback",
        },
    ))

    db.commit()
    return {
        "message": {
            "id": message.id, "conversation_id": message.conversation_id,
            "sender_type": _enum_value(message.sender_type),
            "sender_label": message.sender_label,
            "body_markdown": message.body_markdown,
            "source": message.source, "created_at": _to_iso(message.created_at),
        },
        "opportunity": {"id": opp.id, "next_step": opp.next_step},
    }


# ── BE-07: Proposal Follow-up Agent ──

class ProposalFollowupRequest(BaseModel):
    opportunity_id: str


@router.post("/admin/agent-runs/proposal-followup")
def trigger_proposal_followup(
    req: ProposalFollowupRequest,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    opp = db.query(Opportunity).filter(Opportunity.id == req.opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    try:
        result = run_proposal_followup_workflow(db, req.opportunity_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Follow-up workflow failed")

    r = result
    return {
        "agent_run": {
            "id": r["agent_run"].id, "agent_profile_id": r["agent_run"].agent_profile_id,
            "status": _enum_value(r["agent_run"].status),
            "started_at": _to_iso(r["agent_run"].started_at),
            "completed_at": _to_iso(r["agent_run"].completed_at),
        },
        "artifacts": [
            {
                "id": a.id, "agent_run_id": a.agent_run_id,
                "type": _enum_value(a.type), "title": a.title,
                "content_markdown": a.content_markdown, "content_json": a.content_json,
                "model": a.model, "requires_approval": a.requires_approval,
                "created_at": _to_iso(a.created_at),
            }
            for a in r["artifacts"]
        ],
        "decision": {
            "id": r["decision"].id, "question": r["decision"].question,
            "recommendation": r["decision"].recommendation,
            "status": _enum_value(r["decision"].status),
        },
    }


# ── BE-05: Quote / SOW Draft ──

@router.post("/admin/agent-runs/quote-sow")
def trigger_quote_sow(
    req: ProposalFollowupRequest,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    opp = db.query(Opportunity).filter(Opportunity.id == req.opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    try:
        result = run_quote_sow_workflow(db, req.opportunity_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Quote/SOW workflow failed")
    r = result
    return {
        "agent_run": {"id": r["agent_run"].id, "status": _enum_value(r["agent_run"].status)},
        "artifacts": [
            {"id": a.id, "type": _enum_value(a.type), "title": a.title,
             "content_markdown": a.content_markdown, "content_json": a.content_json,
             "model": a.model, "requires_approval": a.requires_approval,
             "created_at": _to_iso(a.created_at)}
            for a in r["artifacts"]
        ],
        "decision": {
            "id": r["decision"].id, "question": r["decision"].question,
            "status": _enum_value(r["decision"].status),
            "artifact_id": r["decision"].artifact_id,
            "recommendation": r["decision"].recommendation,
        },
    }


# ── BE-02: Approved Quote/SOW JSON API ──

@router.get("/admin/opportunities/{opportunity_id}/approved-quote-sow")
def get_approved_quote_sow(
    opportunity_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    try:
        data = find_latest_approved_quote_sow(db, opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if not data:
        raise HTTPException(status_code=404, detail="No approved Quote/SOW found for this opportunity")
    return data


# ── BE-03: Quote/SOW DeliveryJob ──

@router.post("/admin/opportunities/{opportunity_id}/approved-quote-sow/delivery-job")
def create_quote_sow_delivery_job(
    opportunity_id: str,
    db: Session = Depends(get_db),
    admin: str = Depends(get_admin_email),
):
    try:
        data = find_latest_approved_quote_sow(db, opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if not data:
        raise HTTPException(status_code=404, detail="No approved Quote/SOW found for this opportunity")

    quote_id = data["quote_artifact_id"]
    existing = (
        db.query(DeliveryJob)
        .filter(DeliveryJob.artifact_id == quote_id, DeliveryJob.status == DeliveryStatus.draft)
        .first()
    )
    if existing:
        return JSONResponse(content={"delivery_job": {
            "id": existing.id, "lead_id": existing.lead_id,
            "artifact_id": existing.artifact_id,
            "channel": _enum_value(existing.channel),
            "recipient": existing.recipient, "subject": existing.subject,
            "body_markdown": existing.body_markdown,
            "status": _enum_value(existing.status),
            "created_at": _to_iso(existing.created_at),
            "sent_at": _to_iso(existing.sent_at),
        }}, status_code=200)

    recipient = "unknown"
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if opp and opp.customer_id:
        cust = db.query(Customer).filter(Customer.id == opp.customer_id).first()
        if cust:
            recipient = cust.owner_email

    body_md = f"""请将已审批的 Quote / SOW 确认材料发送给客户。

本发送任务对应：
- Quote: {data['quote_title']}
- SOW: {data['sow_title']}

发送后请回到系统点击 Mark sent。"""

    job = DeliveryJob(
        lead_id=data["lead_id"], artifact_id=quote_id,
        channel=DeliveryChannel.manual_copy, recipient=recipient,
        subject=f"Quote / SOW Confirmation: {opp.title if opp else ''}",
        body_markdown=body_md, status=DeliveryStatus.draft,
    )
    db.add(job)
    db.flush()

    db.add(AuditLog(
        lead_id=data["lead_id"], actor=admin,
        action="quote_sow_delivery_job_created",
        details_json={
            "opportunity_id": opportunity_id,
            "quote_artifact_id": quote_id,
            "sow_artifact_id": data["sow_artifact_id"],
            "delivery_job_id": job.id,
            "reused_existing": False,
        },
    ))

    db.commit()
    return JSONResponse(content={"delivery_job": {
        "id": job.id, "lead_id": job.lead_id, "artifact_id": job.artifact_id,
        "channel": _enum_value(job.channel),
        "recipient": job.recipient, "subject": job.subject,
        "body_markdown": job.body_markdown,
        "status": _enum_value(job.status),
        "created_at": _to_iso(job.created_at), "sent_at": _to_iso(job.sent_at),
    }}, status_code=201)
