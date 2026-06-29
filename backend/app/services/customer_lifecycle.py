"""Customer lifecycle projection from a submitted lead."""

from sqlalchemy.orm import Session
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


def create_lifecycle_from_lead(db: Session, lead_id: str) -> dict:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    existing_opportunity = db.query(Opportunity).filter(Opportunity.lead_id == lead_id).first()
    if existing_opportunity:
        raise ValueError(f"Lead {lead_id} already has lifecycle")

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
        title=f"{lead.company} 初次咨询",
        channel="web_form",
    )
    db.add(conversation)
    db.flush()

    message = Message(
        conversation_id=conversation.id,
        customer_id=customer.id,
        contact_id=contact.id,
        sender_type=MessageSenderType.customer,
        sender_label=contact.name or lead.owner_email,
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
        title=f"{lead.desired_outcome} PoC",
        stage=OpportunityStage.qualified,
        desired_outcome=lead.desired_outcome,
        problem_summary=lead.problem,
        budget_range=lead.budget_range,
        next_step="由 Sales Agent 生成澄清问题",
    )
    db.add(opportunity)
    db.flush()

    db.add(AuditLog(
        lead_id=lead.id,
        actor="system:customer_lifecycle",
        action="customer_lifecycle_created",
        details_json={
            "customer_id": customer.id,
            "contact_id": contact.id,
            "conversation_id": conversation.id,
            "message_id": message.id,
            "opportunity_id": opportunity.id,
        },
    ))
    db.commit()

    return {
        "customer": {"id": customer.id},
        "contact": {"id": contact.id},
        "conversation": {"id": conversation.id},
        "message": {"id": message.id},
        "opportunity": {"id": opportunity.id},
    }
