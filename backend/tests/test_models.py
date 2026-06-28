from app.db import SessionLocal
from app.models import (
    Lead, VerificationCode, LeadAttachment, AgentTask,
    Artifact, Decision, DeliveryJob, NotificationEvent, AuditLog,
    LeadStatus, TaskStatus, DecisionStatus, ArtifactType,
    DeliveryChannel, DeliveryStatus, NotificationChannel, NotificationStatus,
)


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
    assert len(DecisionStatus) == 5
    assert len(DeliveryStatus) == 6
    assert len(NotificationChannel) == 3
