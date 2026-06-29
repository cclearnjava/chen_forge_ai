from app.db import SessionLocal
from app.models import (
    AuditLog,
    Contact,
    Conversation,
    Customer,
    Lead,
    Message,
    MessageSenderType,
    Opportunity,
    OpportunityStage,
)
from app.services.customer_lifecycle import create_lifecycle_from_lead


def _create_lead(db):
    lead = Lead(
        owner_email="owner@example.com",
        company="陈记连锁门店",
        contact_name="陈总",
        contact_method="wechat: chen",
        industry="连锁零售",
        problem="客服重复问答多，门店销售资料整理慢",
        desired_outcome="企业知识库 / RAG 问答",
        company_size="50-200",
        budget_range="3-5w",
    )
    db.add(lead)
    db.commit()
    return lead


def test_create_lifecycle_from_lead():
    db = SessionLocal()
    lead = _create_lead(db)

    result = create_lifecycle_from_lead(db, lead.id)
    db.commit()

    customer = db.query(Customer).filter(Customer.id == result["customer"]["id"]).one()
    contact = db.query(Contact).filter(Contact.id == result["contact"]["id"]).one()
    conversation = db.query(Conversation).filter(Conversation.id == result["conversation"]["id"]).one()
    message = db.query(Message).filter(Message.id == result["message"]["id"]).one()
    opportunity = db.query(Opportunity).filter(Opportunity.id == result["opportunity"]["id"]).one()

    assert customer.name == lead.company
    assert customer.source_lead_id == lead.id
    assert contact.customer_id == customer.id
    assert contact.is_primary is True
    assert conversation.customer_id == customer.id
    assert conversation.lead_id == lead.id
    assert message.conversation_id == conversation.id
    assert message.sender_type == MessageSenderType.customer
    assert message.body_markdown == lead.problem
    assert opportunity.customer_id == customer.id
    assert opportunity.conversation_id == conversation.id
    assert opportunity.stage == OpportunityStage.qualified
    assert opportunity.next_step == "由 Sales Agent 生成澄清问题"

    logs = db.query(AuditLog).filter(
        AuditLog.lead_id == lead.id,
        AuditLog.action == "customer_lifecycle_created",
    ).all()
    assert len(logs) == 1


def test_create_lifecycle_from_missing_lead_fails():
    db = SessionLocal()

    try:
        create_lifecycle_from_lead(db, "missing-lead")
        assert False, "Should have raised"
    except ValueError as exc:
        assert "not found" in str(exc)


def test_create_lifecycle_from_lead_is_fail_closed_for_duplicates():
    db = SessionLocal()
    lead = _create_lead(db)
    create_lifecycle_from_lead(db, lead.id)
    db.commit()

    try:
        create_lifecycle_from_lead(db, lead.id)
        assert False, "Should have raised"
    except ValueError as exc:
        assert "already has lifecycle" in str(exc)

    assert db.query(Customer).filter(Customer.source_lead_id == lead.id).count() == 1
    assert db.query(Opportunity).filter(Opportunity.lead_id == lead.id).count() == 1
