from app.db import SessionLocal
from app.models import (
    Lead, VerificationCode, LeadAttachment, AgentTask,
    Artifact, Decision, DeliveryJob, NotificationEvent, AuditLog,
    Customer, Contact, Conversation, Message, Opportunity,
    AgentProfile, AgentRun, ToolInvocation,
    LeadStatus, TaskStatus, AgentRunStatus, DecisionStatus, ArtifactType,
    DeliveryChannel, DeliveryStatus, NotificationChannel, NotificationStatus,
    ConversationStatus, MessageSenderType, OpportunityStage,
)
from app.schemas import AgentProfileOut, AgentRunOut, ToolInvocationOut


def test_create_lead():
    db = SessionLocal()
    lead = Lead(
        owner_email="test@example.com",
        company="测试公司",
        contact_method="email",
        problem="这是一个足够长的业务问题描述用于测试",
        desired_outcome="企业知识库 / RAG 问答",
    )
    db.add(lead)
    db.commit()
    assert lead.id is not None
    assert lead.status == LeadStatus.new
    assert lead.created_at is not None


def test_create_verification_code():
    db = SessionLocal()
    from datetime import datetime, timedelta, timezone
    code = VerificationCode(
        email="test@example.com",
        code_hash="hashed_code_123",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(code)
    db.commit()
    assert code.id is not None
    assert code.used is False


def test_create_attachment():
    db = SessionLocal()
    lead = Lead(
        owner_email="test2@example.com",
        company="测试附件公司",
        contact_method="email",
        problem="这是一个测试附件上传的业务问题描述",
        desired_outcome="AI Agent 流程诊断与蓝图",
    )
    db.add(lead)
    db.flush()

    attachment = LeadAttachment(
        lead_id=lead.id,
        filename="test.png",
        content_type="image/png",
        size_bytes=1024,
        storage_key="uploads/test.png",
        uploaded_by_email="test2@example.com",
    )
    db.add(attachment)
    db.commit()
    assert attachment.id is not None


def test_create_agent_task():
    db = SessionLocal()
    lead = Lead(
        owner_email="test3@example.com",
        company="测试Agent公司",
        contact_method="email",
        problem="测试Agent工作流的业务问题描述够了",
        desired_outcome="内部自动化 MVP",
    )
    db.add(lead)
    db.flush()

    task = AgentTask(
        lead_id=lead.id,
        agent_name="lead_diagnosis",
        status=TaskStatus.pending,
    )
    db.add(task)
    db.commit()
    assert task.id is not None
    assert task.status == TaskStatus.pending


def test_create_artifact_and_decision():
    db = SessionLocal()
    lead = Lead(
        owner_email="test4@example.com",
        company="测试Artifact公司",
        contact_method="email",
        problem="测试Artifact和Decision的业务问题描述",
        desired_outcome="ChatBI / 自然语言问数",
    )
    db.add(lead)
    db.flush()

    artifact = Artifact(
        lead_id=lead.id,
        type=ArtifactType.requirement_summary,
        title="需求理解",
        content_markdown="## 需求理解\n这是测试内容",
        content_json={"key": "value"},
        model="mock-v0",
        prompt_version="v1",
        requires_approval=True,
    )
    db.add(artifact)
    db.flush()

    decision = Decision(
        lead_id=lead.id,
        artifact_id=artifact.id,
        question="是否批准此需求理解？",
        recommendation="approve",
    )
    db.add(decision)
    db.commit()
    assert artifact.id is not None
    assert decision.id is not None
    assert decision.status == DecisionStatus.waiting


def test_create_delivery_job():
    db = SessionLocal()
    lead = Lead(
        owner_email="test5@example.com",
        company="测试Delivery公司",
        contact_method="email",
        problem="测试DeliveryJob的业务问题描述足够了",
        desired_outcome="内部自动化 MVP",
    )
    db.add(lead)
    db.flush()

    artifact = Artifact(
        lead_id=lead.id,
        type=ArtifactType.customer_reply_draft,
        title="客户回复草稿",
        content_markdown="您好，这是回复内容",
        model="mock-v0",
        prompt_version="v1",
        requires_approval=True,
    )
    db.add(artifact)
    db.flush()

    job = DeliveryJob(
        lead_id=lead.id,
        artifact_id=artifact.id,
        channel=DeliveryChannel.email,
        recipient="client@example.com",
        subject="ChenForge AI 回复",
        body_markdown="这是邮件正文",
    )
    db.add(job)
    db.commit()
    assert job.id is not None
    assert job.channel == DeliveryChannel.email
    assert job.status == DeliveryStatus.draft


def test_create_notification():
    db = SessionLocal()
    event = NotificationEvent(
        channel=NotificationChannel.feishu,
        event_type="lead_created",
        payload_json={"lead_id": "test"},
    )
    db.add(event)
    db.commit()
    assert event.id is not None


def test_create_audit_log():
    db = SessionLocal()
    log = AuditLog(
        lead_id="test-lead-id",
        actor="system",
        action="lead_created",
        details_json={"company": "测试"},
    )
    db.add(log)
    db.commit()
    assert log.id is not None


def test_all_enums():
    assert len(LeadStatus) == 7
    assert len(TaskStatus) == 4
    assert len(AgentRunStatus) == 5
    assert len(DecisionStatus) == 5
    assert len(DeliveryStatus) == 6
    assert len(NotificationChannel) == 3


def test_create_customer_lifecycle_models():
    db = SessionLocal()
    lead = Lead(
        owner_email="founder@example.com",
        company="陈记连锁门店",
        contact_name="陈总",
        contact_method="wechat: chen",
        industry="连锁零售",
        problem="客服重复问答多，门店销售资料整理慢",
        desired_outcome="企业知识库 / RAG 问答",
        company_size="50-200",
    )
    db.add(lead)
    db.flush()

    customer = Customer(
        name=lead.company,
        owner_email=lead.owner_email,
        industry=lead.industry,
        company_size=lead.company_size,
        source_lead_id=lead.id,
    )
    db.add(customer)
    db.flush()

    contact = Contact(
        customer_id=customer.id,
        name=lead.contact_name,
        email=lead.owner_email,
        contact_method=lead.contact_method,
        is_primary=True,
        source_lead_id=lead.id,
    )
    db.add(contact)
    db.flush()

    conversation = Conversation(
        customer_id=customer.id,
        lead_id=lead.id,
        primary_contact_id=contact.id,
        title="首次 AI 落地咨询",
        channel="web_form",
    )
    db.add(conversation)
    db.flush()

    message = Message(
        conversation_id=conversation.id,
        customer_id=customer.id,
        contact_id=contact.id,
        sender_type=MessageSenderType.customer,
        sender_label=contact.name,
        body_markdown=lead.problem,
        source="lead_form",
    )
    db.add(message)
    db.flush()

    opportunity = Opportunity(
        customer_id=customer.id,
        lead_id=lead.id,
        primary_contact_id=contact.id,
        conversation_id=conversation.id,
        title="企业知识库 PoC",
        stage=OpportunityStage.qualified,
        desired_outcome=lead.desired_outcome,
        problem_summary=lead.problem,
        next_step="由 Sales Agent 生成澄清问题",
    )
    db.add(opportunity)
    db.commit()

    saved = db.query(Opportunity).filter(Opportunity.id == opportunity.id).one()
    assert saved.stage == OpportunityStage.qualified
    assert saved.customer_id == customer.id
    assert saved.conversation_id == conversation.id
    assert conversation.status == ConversationStatus.open
    assert message.sender_type == MessageSenderType.customer
    assert contact.is_primary is True


def test_create_agent_profile():
    db = SessionLocal()
    profile = AgentProfile(
        name="model_sales_agent_test",
        display_name="Sales Agent",
        role="生成客户回复草稿和澄清问题",
        allowed_tools_json={"tools": ["context_builder"]},
        output_artifact_types_json={"types": ["customer_reply_draft", "discovery_questions"]},
    )
    db.add(profile)
    db.commit()

    saved = db.query(AgentProfile).filter(AgentProfile.name == "model_sales_agent_test").one()
    assert saved.id is not None
    assert saved.requires_approval is True
    assert saved.is_active is True
    assert saved.allowed_tools_json == {"tools": ["context_builder"]}
    assert saved.output_artifact_types_json == {"types": ["customer_reply_draft", "discovery_questions"]}
    assert saved.created_at is not None
    assert saved.updated_at is not None


def test_create_agent_run_for_opportunity_context():
    db = SessionLocal()
    lead = Lead(
        owner_email="agent-runtime@example.com",
        company="Agent Runtime 测试公司",
        contact_name="陈总",
        contact_method="wechat: agent-runtime",
        problem="测试 Agent Runtime 需要一段足够长的客户业务问题描述",
        desired_outcome="企业知识库 / RAG 问答",
    )
    db.add(lead)
    db.flush()

    customer = Customer(
        name=lead.company,
        owner_email=lead.owner_email,
        source_lead_id=lead.id,
    )
    db.add(customer)
    db.flush()

    conversation = Conversation(
        customer_id=customer.id,
        lead_id=lead.id,
        title="Agent Runtime 测试对话",
        channel="web_form",
    )
    db.add(conversation)
    db.flush()

    opportunity = Opportunity(
        customer_id=customer.id,
        lead_id=lead.id,
        conversation_id=conversation.id,
        title="Agent Runtime 测试机会",
        stage=OpportunityStage.qualified,
        desired_outcome=lead.desired_outcome,
        problem_summary=lead.problem,
    )
    db.add(opportunity)
    db.flush()

    profile = AgentProfile(
        name="quality_agent_runtime_test",
        display_name="Quality Agent",
        role="审查客户回复草稿中的风险",
        allowed_tools_json={"tools": ["risk_rules"]},
        output_artifact_types_json={"types": ["review"]},
    )
    db.add(profile)
    db.flush()

    run = AgentRun(
        agent_profile_id=profile.id,
        lead_id=lead.id,
        opportunity_id=opportunity.id,
        conversation_id=conversation.id,
        input_json={"opportunity_id": opportunity.id},
    )
    db.add(run)
    db.commit()

    saved = db.query(AgentRun).filter(AgentRun.id == run.id).one()
    assert saved.status == AgentRunStatus.pending
    assert saved.agent_profile.name == "quality_agent_runtime_test"
    assert saved.lead_id == lead.id
    assert saved.opportunity_id == opportunity.id
    assert saved.conversation_id == conversation.id
    assert saved.input_json == {"opportunity_id": opportunity.id}
    assert saved.output_json is None
    assert saved.created_at is not None


def test_create_tool_invocation_for_agent_run():
    db = SessionLocal()
    profile = AgentProfile(
        name="sales_agent_tool_test",
        display_name="Sales Agent",
        role="生成客户回复草稿",
        allowed_tools_json={"tools": ["context_builder"]},
        output_artifact_types_json={"types": ["customer_reply_draft"]},
    )
    db.add(profile)
    db.flush()

    run = AgentRun(
        agent_profile_id=profile.id,
        input_json={"source": "unit_test"},
        output_json={"status": "prepared"},
    )
    db.add(run)
    db.flush()

    invocation = ToolInvocation(
        agent_run_id=run.id,
        tool_name="context_builder",
        input_json={"opportunity_id": "opp-test"},
        output_json={"message_count": 1},
    )
    db.add(invocation)
    db.commit()

    saved = db.query(ToolInvocation).filter(ToolInvocation.id == invocation.id).one()
    assert saved.id is not None
    assert saved.status == "succeeded"
    assert saved.agent_run_id == run.id
    assert saved.agent_run.agent_profile.name == "sales_agent_tool_test"
    assert saved.input_json == {"opportunity_id": "opp-test"}
    assert saved.output_json == {"message_count": 1}
    assert len(saved.agent_run.tool_invocations) == 1


def test_agent_runtime_schemas_serialize_from_models():
    db = SessionLocal()
    profile = AgentProfile(
        name="schema_sales_agent",
        display_name="Sales Agent",
        role="生成客户回复草稿",
        allowed_tools_json={"tools": ["context_builder"]},
        output_artifact_types_json={"types": ["customer_reply_draft"]},
    )
    db.add(profile)
    db.flush()

    run = AgentRun(
        agent_profile_id=profile.id,
        status=AgentRunStatus.succeeded,
        input_json={"source": "schema_test"},
        output_json={"artifact_count": 2},
    )
    db.add(run)
    db.flush()

    invocation = ToolInvocation(
        agent_run_id=run.id,
        tool_name="context_builder",
        input_json={"source": "schema_test"},
        output_json={"ok": True},
    )
    db.add(invocation)
    db.commit()

    profile_out = AgentProfileOut.model_validate(profile)
    run_out = AgentRunOut.model_validate(run)
    invocation_out = ToolInvocationOut.model_validate(invocation)

    assert profile_out.name == "schema_sales_agent"
    assert profile_out.requires_approval is True
    assert run_out.status == "succeeded"
    assert run_out.output_json == {"artifact_count": 2}
    assert invocation_out.tool_name == "context_builder"
    assert invocation_out.status == "succeeded"
