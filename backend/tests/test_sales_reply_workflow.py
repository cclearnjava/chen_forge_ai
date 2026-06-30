from app.db import SessionLocal
from app.models import (
    AgentProfile, AgentRun, AgentRunStatus, Artifact, ArtifactType,
    AuditLog, Contact, Conversation, Customer, Decision, DecisionStatus,
    Lead, Message, MessageSenderType, Opportunity, OpportunityStage,
)
from app.services.sales_reply_workflow import run_sales_reply_workflow
from app.services.mock_agents import generate_sales_reply, review_sales_reply


def _setup_opportunity(db):
    """Create a minimal Lead → Customer → Conversation → Message → Opportunity chain."""
    lead = Lead(
        owner_email="workflow-test@example.com",
        company="工作流测试公司",
        contact_name="王总",
        contact_method="email",
        problem="现有ERP系统报表生成太慢，财务月底结账耗时两天以上",
        desired_outcome="自动化财务报表生成",
    )
    db.add(lead)
    db.flush()

    customer = Customer(
        name=lead.company, owner_email=lead.owner_email,
        source_lead_id=lead.id,
    )
    db.add(customer)
    db.flush()

    conversation = Conversation(
        customer_id=customer.id, lead_id=lead.id,
        title="工作流测试对话", channel="web_form",
    )
    db.add(conversation)
    db.flush()

    msg = Message(
        conversation_id=conversation.id, customer_id=customer.id,
        sender_type=MessageSenderType.customer, sender_label=lead.contact_name,
        body_markdown=lead.problem, source="lead_form",
    )
    db.add(msg)
    db.flush()

    contact = Contact(
        customer_id=customer.id, name=lead.contact_name,
        email=lead.owner_email, contact_method=lead.contact_method,
        is_primary=True, source_lead_id=lead.id,
    )
    db.add(contact)
    db.flush()

    opp = Opportunity(
        customer_id=customer.id, lead_id=lead.id,
        primary_contact_id=contact.id,
        conversation_id=conversation.id,
        title="自动化报表 PoC",
        stage=OpportunityStage.qualified,
        desired_outcome=lead.desired_outcome,
        problem_summary=lead.problem,
        next_step="待 Sales Agent 生成回复",
    )
    db.add(opp)
    db.flush()
    return opp


class TestSalesReplyWorkflow:
    def test_schema_supports_opportunity_agent_run_artifacts(self):
        """BE-00: Artifact/Decision can be created with agent_run_id and opportunity_id."""
        db = SessionLocal()
        opp = _setup_opportunity(db)
        profile = AgentProfile(
            name="schema_test_agent", display_name="Schema Test",
            role="test", allowed_tools_json={}, output_artifact_types_json={},
        )
        db.add(profile)
        db.flush()

        run = AgentRun(
            agent_profile_id=profile.id, opportunity_id=opp.id,
            lead_id=opp.lead_id, status=AgentRunStatus.succeeded,
        )
        db.add(run)
        db.flush()

        art = Artifact(
            agent_run_id=run.id, opportunity_id=opp.id, lead_id=opp.lead_id,
            type=ArtifactType.customer_reply_draft, title="Test",
            content_markdown="test", model="mock", prompt_version="v1",
            requires_approval=True,
        )
        db.add(art)
        db.flush()

        dec = Decision(
            agent_run_id=run.id, opportunity_id=opp.id, lead_id=opp.lead_id,
            artifact_id=art.id, question="批准？",
            recommendation="approve",
        )
        db.add(dec)
        db.commit()

        saved_art = db.query(Artifact).filter(Artifact.id == art.id).one()
        assert saved_art.agent_run_id == run.id
        assert saved_art.opportunity_id == opp.id
        saved_dec = db.query(Decision).filter(Decision.id == dec.id).one()
        assert saved_dec.agent_run_id == run.id
        assert saved_dec.opportunity_id == opp.id

    def test_generates_customer_reply_draft(self):
        db = SessionLocal()
        opp = _setup_opportunity(db)
        db.commit()

        result = run_sales_reply_workflow(db, opp.id)
        db.commit()

        draft = result["artifacts"][0]
        assert draft.type == ArtifactType.customer_reply_draft
        assert draft.requires_approval is True
        assert "工作流测试公司" in draft.content_markdown
        assert "王总" in draft.content_markdown

    def test_generates_discovery_questions(self):
        db = SessionLocal()
        opp = _setup_opportunity(db)
        db.commit()

        result = run_sales_reply_workflow(db, opp.id)
        db.commit()

        q_art = result["artifacts"][1]
        assert q_art.type == ArtifactType.discovery_questions
        assert q_art.requires_approval is False
        questions = q_art.content_json["questions"]
        assert len(questions) >= 3

    def test_generates_review(self):
        db = SessionLocal()
        opp = _setup_opportunity(db)
        db.commit()

        result = run_sales_reply_workflow(db, opp.id)
        db.commit()

        review_art = result["artifacts"][2]
        assert review_art.type == ArtifactType.review
        review = result["quality_review"]
        assert review["risk_level"] in ("low", "medium", "high")
        assert "risk_flags" in review

    def test_quality_review_detects_overpromise(self):
        reply = "我们保证一个月一定上线，而且免费交付所有模块。"
        result = review_sales_reply(reply)
        assert result["risk_level"] == "high"
        assert any(f["type"] == "overpromise" for f in result["risk_flags"])

    def test_quality_review_detects_unclear_scope(self):
        reply = "感谢信任。我们会尽快安排开发并交付。价格按市场行情来。"
        result = review_sales_reply(reply)
        flags = result["risk_flags"]
        has_unclear = any(f["type"] == "unclear_scope" for f in flags)
        assert has_unclear or result["risk_level"] != "low"

    def test_creates_waiting_decision(self):
        db = SessionLocal()
        opp = _setup_opportunity(db)
        db.commit()

        result = run_sales_reply_workflow(db, opp.id)
        db.commit()

        dec = result["decision"]
        assert dec.status == DecisionStatus.waiting
        assert dec.artifact_id == result["artifacts"][0].id

    def test_first_run_creates_agent_profiles(self):
        db = SessionLocal()
        opp = _setup_opportunity(db)
        db.commit()

        run_sales_reply_workflow(db, opp.id)
        db.commit()

        sales = db.query(AgentProfile).filter(AgentProfile.name == "sales_agent").one()
        assert sales.is_active is True
        assert sales.allowed_tools_json == {"tools": ["context_builder"]}
        quality = db.query(AgentProfile).filter(AgentProfile.name == "quality_agent").one()
        assert quality.is_active is True
        assert quality.output_artifact_types_json == {"types": ["review"]}

    def test_missing_opportunity_fail_closed(self):
        db = SessionLocal()
        try:
            run_sales_reply_workflow(db, "nonexistent-opp-id")
            assert False, "Should have raised"
        except ValueError as exc:
            assert "not found" in str(exc)
        # No commit means no state persisted for this call. Just verify
        # the call didn't leave partial rows committed through the
        # workflow service itself (it doesn't call db.commit() internally).
        db.rollback()

    def test_repeated_runs_create_new_versions(self):
        db = SessionLocal()
        opp = _setup_opportunity(db)
        db.commit()

        run_sales_reply_workflow(db, opp.id)
        db.commit()
        run_sales_reply_workflow(db, opp.id)
        db.commit()

        drafts = (
            db.query(Artifact)
            .filter(
                Artifact.opportunity_id == opp.id,
                Artifact.type == ArtifactType.customer_reply_draft,
            )
            .all()
        )
        assert len(drafts) >= 2

        reviews = (
            db.query(Artifact)
            .filter(
                Artifact.opportunity_id == opp.id,
                Artifact.type == ArtifactType.review,
            )
            .all()
        )
        assert len(reviews) >= 2

        decisions = (
            db.query(Decision)
            .filter(Decision.opportunity_id == opp.id)
            .all()
        )
        assert len(decisions) >= 2

    def test_writes_audit_log(self):
        db = SessionLocal()
        opp = _setup_opportunity(db)
        db.commit()

        run_sales_reply_workflow(db, opp.id)
        db.commit()

        logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.lead_id == opp.lead_id,
                AuditLog.action == "sales_reply_workflow_completed",
            )
            .all()
        )
        assert len(logs) == 1
        assert logs[0].details_json["opportunity_id"] == opp.id

    def test_reply_has_no_overpromise_keywords(self):
        """BE-02: Output must not contain risky keywords."""
        db = SessionLocal()
        opp = _setup_opportunity(db)
        db.commit()

        result = run_sales_reply_workflow(db, opp.id)
        db.commit()

        draft_text = result["artifacts"][0].content_markdown
        for kw in ["保证", "一定上线", "免费交付"]:
            assert kw not in draft_text, f"Reply contains risky keyword: {kw}"

    def test_artifacts_have_correct_traceability(self):
        """BE-05: draft/questions → Sales AgentRun, review → Quality AgentRun."""
        db = SessionLocal()
        opp = _setup_opportunity(db)
        db.commit()

        result = run_sales_reply_workflow(db, opp.id)
        db.commit()

        sales_run = result["sales_agent_run"]
        quality_run = result["quality_agent_run"]

        drafts = [a for a in result["artifacts"] if a.type == ArtifactType.customer_reply_draft]
        assert len(drafts) == 1
        assert drafts[0].agent_run_id == sales_run.id
        assert drafts[0].opportunity_id == opp.id

        reviews = [a for a in result["artifacts"] if a.type == ArtifactType.review]
        assert len(reviews) == 1
        assert reviews[0].agent_run_id == quality_run.id
        assert reviews[0].opportunity_id == opp.id
