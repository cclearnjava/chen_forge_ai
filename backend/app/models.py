import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base
import enum


def utcnow():
    return datetime.utcnow()


def new_uuid():
    return str(uuid.uuid4())


class LeadStatus(str, enum.Enum):
    new = "new"
    reviewing = "reviewing"
    diagnosed = "diagnosed"
    proposed = "proposed"
    contacted = "contacted"
    sent = "sent"
    archived = "archived"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class AgentRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class DecisionStatus(str, enum.Enum):
    waiting = "waiting"
    approved = "approved"
    deferred = "deferred"
    rewrite_requested = "rewrite_requested"
    edited_and_approved = "edited_and_approved"


class ArtifactType(str, enum.Enum):
    diagnosis = "diagnosis"
    architecture = "architecture"
    proposal = "proposal"
    email = "email"
    roadmap = "roadmap"
    review = "review"
    audit = "audit"
    requirement_summary = "requirement_summary"
    customer_reply_draft = "customer_reply_draft"
    discovery_questions = "discovery_questions"
    proposal_draft = "proposal_draft"
    delivery_roadmap = "delivery_roadmap"
    sent_message = "sent_message"
    proposal_followup_reply_draft = "proposal_followup_reply_draft"
    objection_analysis = "objection_analysis"
    next_step_recommendation = "next_step_recommendation"
    quote_draft = "quote_draft"
    sow_draft = "sow_draft"
    commercial_review = "commercial_review"


class DeliveryChannel(str, enum.Enum):
    email = "email"
    feishu = "feishu"
    wecom = "wecom"
    sms = "sms"
    client_portal = "client_portal"
    manual_copy = "manual_copy"


class DeliveryStatus(str, enum.Enum):
    draft = "draft"
    queued = "queued"
    sending = "sending"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"


class NotificationChannel(str, enum.Enum):
    feishu = "feishu"
    wecom = "wecom"
    email = "email"


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class ConversationStatus(str, enum.Enum):
    open = "open"
    waiting_on_customer = "waiting_on_customer"
    waiting_on_owner = "waiting_on_owner"
    closed = "closed"


class MessageSenderType(str, enum.Enum):
    customer = "customer"
    owner = "owner"
    agent = "agent"
    system = "system"


class OpportunityStage(str, enum.Enum):
    lead = "lead"
    qualified = "qualified"
    proposal = "proposal"
    negotiation = "negotiation"
    won = "won"
    lost = "lost"
    archived = "archived"
    contracting = "contracting"


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(255))
    business_type: Mapped[str | None] = mapped_column(String(100))
    positioning: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)



class EventSeverity(str, enum.Enum):
    info = "info"
    success = "success"
    warning = "warning"
    critical = "critical"


class NotificationKind(str, enum.Enum):
    lead_created = "lead_created"
    customer_reply_recorded = "customer_reply_recorded"
    approval_required = "approval_required"
    proposal_ready = "proposal_ready"
    quote_sow_ready = "quote_sow_ready"
    delivery_action_required = "delivery_action_required"
    delivery_sent = "delivery_sent"
    delivery_failed = "delivery_failed"
    system_notice = "system_notice"


class NotificationReadStatus(str, enum.Enum):
    unread = "unread"
    read = "read"
    archived = "archived"


class NotifDeliveryChannel(str, enum.Enum):
    in_app = "in_app"
    email = "email"
    feishu = "feishu"
    wecom = "wecom"


class NotificationDeliveryStatus(str, enum.Enum):
    pending = "pending"
    delivered = "delivered"
    failed = "failed"




class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[EventSeverity] = mapped_column(SAEnum(EventSeverity), default=EventSeverity.info, nullable=False)
    subject_type: Mapped[str | None] = mapped_column(String(100))
    subject_id: Mapped[str | None] = mapped_column(String(36))
    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    event_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("events.id"), index=True)
    kind: Mapped[NotificationKind] = mapped_column(SAEnum(NotificationKind), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[EventSeverity] = mapped_column(SAEnum(EventSeverity), default=EventSeverity.info, nullable=False)
    status: Mapped[NotificationReadStatus] = mapped_column(SAEnum(NotificationReadStatus), default=NotificationReadStatus.unread, nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(100))
    target_id: Mapped[str | None] = mapped_column(String(36))
    target_url: Mapped[str | None] = mapped_column(String(500))
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    notification_id: Mapped[str] = mapped_column(String(36), ForeignKey("notifications.id"), nullable=False, index=True)
    channel: Mapped[NotifDeliveryChannel] = mapped_column(SAEnum(NotifDeliveryChannel), default=NotifDeliveryChannel.in_app, nullable=False)
    recipient: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[NotificationDeliveryStatus] = mapped_column(SAEnum(NotificationDeliveryStatus), default=NotificationDeliveryStatus.delivered, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100))
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)




class ServiceStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    inactive = "inactive"
    archived = "archived"


class RiskSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"




class Service(Base):
    __tablename__ = "services"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[ServiceStatus] = mapped_column(SAEnum(ServiceStatus), default=ServiceStatus.draft, nullable=False, index=True)
    positioning: Mapped[str | None] = mapped_column(Text)
    target_customer: Mapped[str | None] = mapped_column(Text)
    pain_points_json: Mapped[dict | None] = mapped_column(JSON)
    outcomes_json: Mapped[dict | None] = mapped_column(JSON)
    required_inputs_json: Mapped[dict | None] = mapped_column(JSON)
    success_criteria_json: Mapped[dict | None] = mapped_column(JSON)
    typical_duration: Mapped[str | None] = mapped_column(String(100))
    price_min: Mapped[int | None] = mapped_column(Integer)
    price_max: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="CNY", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ServicePackage(Base):
    __tablename__ = "service_packages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    service_id: Mapped[str] = mapped_column(String(36), ForeignKey("services.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price_min: Mapped[int | None] = mapped_column(Integer)
    price_max: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="CNY", nullable=False)
    duration: Mapped[str | None] = mapped_column(String(100))
    deliverables_json: Mapped[dict | None] = mapped_column(JSON)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ServiceDeliverable(Base):
    __tablename__ = "service_deliverables"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    service_id: Mapped[str] = mapped_column(String(36), ForeignKey("services.id"), nullable=False, index=True)
    package_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("service_packages.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    format: Mapped[str | None] = mapped_column(String(100))
    acceptance_criteria_json: Mapped[dict | None] = mapped_column(JSON)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ServiceRiskRule(Base):
    __tablename__ = "service_risk_rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    service_id: Mapped[str] = mapped_column(String(36), ForeignKey("services.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[RiskSeverity] = mapped_column(SAEnum(RiskSeverity), default=RiskSeverity.medium, nullable=False)
    disqualifies: Mapped[bool] = mapped_column(Boolean, default=False)
    suggested_response: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


# ── Workspace Knowledge Engine (P3) ──

KNOWLEDGE_STATUSES = ("draft", "active", "archived")
KNOWLEDGE_SOURCE_TYPES = (
    "manual", "faq", "case_study", "methodology", "pricing_rule",
    "contract_boundary", "delivery_sop", "service_note", "external_doc",
)

KNOWLEDGE_DOCUMENT_STATUSES = ("uploaded", "processing", "processed", "failed", "archived")


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    source_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("knowledge_sources.id"), index=True)
    service_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("services.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), default="manual", nullable=False, index=True)
    tags_json: Mapped[list | None] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    visibility: Mapped[str] = mapped_column(String(20), default="internal", nullable=False)
    confidence: Mapped[float | None] = mapped_column()
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255))
    contact_method: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(255))
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    desired_outcome: Mapped[str] = mapped_column(String(255), nullable=False)
    company_size: Mapped[str | None] = mapped_column(String(50))
    budget_range: Mapped[str | None] = mapped_column(String(50))
    timeline: Mapped[str | None] = mapped_column(String(255))
    video_links: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[LeadStatus] = mapped_column(
        SAEnum(LeadStatus), default=LeadStatus.new, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    industry: Mapped[str | None] = mapped_column(String(255))
    company_size: Mapped[str | None] = mapped_column(String(50))
    source_lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    contacts: Mapped[list["Contact"]] = relationship(back_populates="customer", order_by="Contact.is_primary.desc()")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="customer")
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="customer")


class Contact(Base):
    __tablename__ = "contacts"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    contact_method: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50), index=True)
    external_provider: Mapped[str | None] = mapped_column(String(50), index=True)
    external_user_id: Mapped[str | None] = mapped_column(String(255), index=True)
    role: Mapped[str | None] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="contacts")


class Conversation(Base):
    __tablename__ = "conversations"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id"), index=True)
    primary_contact_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("contacts.id"), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ConversationStatus] = mapped_column(
        SAEnum(ConversationStatus), default=ConversationStatus.open, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    contact_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("contacts.id"), index=True)
    sender_type: Mapped[MessageSenderType] = mapped_column(SAEnum(MessageSenderType), nullable=False, index=True)
    sender_label: Mapped[str | None] = mapped_column(String(255))
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    external_message_id: Mapped[str | None] = mapped_column(String(255))
    external_connector_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("external_connectors.id"), index=True)
    external_thread_id: Mapped[str | None] = mapped_column(String(255), index=True)
    raw_payload_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    customer: Mapped["Customer"] = relationship()


class Opportunity(Base):
    __tablename__ = "opportunities"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id"), index=True)
    primary_contact_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("contacts.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("conversations.id"), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    stage: Mapped[OpportunityStage] = mapped_column(
        SAEnum(OpportunityStage), default=OpportunityStage.lead, nullable=False, index=True
    )
    desired_outcome: Mapped[str | None] = mapped_column(String(255))
    problem_summary: Mapped[str | None] = mapped_column(Text)
    budget_range: Mapped[str | None] = mapped_column(String(50))
    estimated_value: Mapped[int | None] = mapped_column(Integer)
    probability: Mapped[int | None] = mapped_column(Integer)
    next_step: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="opportunities")
    primary_contact: Mapped["Contact | None"] = relationship()
    conversation: Mapped["Conversation | None"] = relationship()


class AgentProfile(Base):
    __tablename__ = "agent_profiles"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_tools_json: Mapped[dict | None] = mapped_column(JSON)
    output_artifact_types_json: Mapped[dict | None] = mapped_column(JSON)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    runs: Mapped[list["AgentRun"]] = relationship(back_populates="agent_profile")


class AgentRun(Base):
    __tablename__ = "agent_runs"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    agent_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_profiles.id"), nullable=False, index=True
    )
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id"), index=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("opportunities.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("conversations.id"), index=True)
    status: Mapped[AgentRunStatus] = mapped_column(
        SAEnum(AgentRunStatus), default=AgentRunStatus.pending, nullable=False, index=True
    )
    input_json: Mapped[dict | None] = mapped_column(JSON)
    output_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    agent_profile: Mapped["AgentProfile"] = relationship(back_populates="runs")
    lead: Mapped["Lead | None"] = relationship()
    opportunity: Mapped["Opportunity | None"] = relationship()
    conversation: Mapped["Conversation | None"] = relationship()
    tool_invocations: Mapped[list["ToolInvocation"]] = relationship(
        back_populates="agent_run",
        order_by="ToolInvocation.created_at",
    )
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="agent_run")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="agent_run")


class ToolInvocation(Base):
    __tablename__ = "tool_invocations"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    agent_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_runs.id"), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_json: Mapped[dict | None] = mapped_column(JSON)
    output_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="succeeded", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    agent_run: Mapped["AgentRun"] = relationship(back_populates="tool_invocations")


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class LeadAttachment(Base):
    __tablename__ = "lead_attachments"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by_email: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class AgentTask(Base):
    __tablename__ = "agent_tasks"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus), default=TaskStatus.pending, nullable=False
    )
    input_json: Mapped[dict | None] = mapped_column(JSON)
    output_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class Artifact(Base):
    __tablename__ = "artifacts"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id"), index=True)
    agent_run_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_runs.id"), index=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("opportunities.id"), index=True)
    type: Mapped[ArtifactType] = mapped_column(SAEnum(ArtifactType), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_markdown: Mapped[str | None] = mapped_column(Text)
    content_json: Mapped[dict | None] = mapped_column(JSON)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    version_history: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    agent_run: Mapped["AgentRun | None"] = relationship(back_populates="artifacts")


class Decision(Base):
    __tablename__ = "decisions"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id"), index=True)
    agent_run_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_runs.id"), index=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("opportunities.id"), index=True)
    artifact_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("artifacts.id"))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DecisionStatus] = mapped_column(
        SAEnum(DecisionStatus), default=DecisionStatus.waiting, nullable=False
    )
    operator_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    agent_run: Mapped["AgentRun | None"] = relationship(back_populates="decisions")


class DeliveryJob(Base):
    __tablename__ = "delivery_jobs"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id"), nullable=False, index=True)
    artifact_id: Mapped[str] = mapped_column(String(36), ForeignKey("artifacts.id"), nullable=False)
    channel: Mapped[DeliveryChannel] = mapped_column(SAEnum(DeliveryChannel), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DeliveryStatus] = mapped_column(
        SAEnum(DeliveryStatus), default=DeliveryStatus.draft, nullable=False
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)


class NotificationEvent(Base):
    __tablename__ = "notification_events"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id"), index=True)
    channel: Mapped[NotifDeliveryChannel] = mapped_column(SAEnum(NotifDeliveryChannel), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[NotificationReadStatus] = mapped_column(
        SAEnum(NotificationReadStatus), default=NotificationReadStatus.unread, nullable=False
    )
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

   
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id"), index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


# ── External Connector (P5) ──

class ExternalConnectorProvider(str, enum.Enum):
    mock = "mock"
    email = "email"
    feishu = "feishu"
    wechat_work = "wechat_work"


class ExternalConnectorStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    disabled = "disabled"


class ExternalConnector(Base):
    __tablename__ = "external_connectors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    provider: Mapped[ExternalConnectorProvider] = mapped_column(SAEnum(ExternalConnectorProvider), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[ExternalConnectorStatus] = mapped_column(SAEnum(ExternalConnectorStatus), default=ExternalConnectorStatus.active, nullable=False, index=True)
    config_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    secret_ref: Mapped[str | None] = mapped_column(String(255))
    webhook_token: Mapped[str | None] = mapped_column(String(120), unique=True, index=True)
    last_received_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


# ── Knowledge Document Upload (P6) ──

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("knowledge_sources.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120))
    file_ext: Mapped[str | None] = mapped_column(String(20), index=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="uploaded", nullable=False, index=True)
    parser: Mapped[str | None] = mapped_column(String(80))
    parser: Mapped[str | None] = mapped_column(String(80))
    text_excerpt: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


# ── Vector RAG (P6.6) ──

KNOWLEDGE_VECTOR_STATUSES = ("not_indexed", "indexed", "stale", "failed")


class KnowledgeVector(Base):
    __tablename__ = "knowledge_vectors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    knowledge_item_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_items.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    vector_json: Mapped[list | None] = mapped_column(JSON)
    vector_dim: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="not_indexed", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


# ── Knowledge Retrieval Evaluation (P6.9) ──

RETRIEVAL_EVAL_CASE_STATUSES = ("active", "archived")
RETRIEVAL_EVAL_RUN_STATUSES = ("running", "completed", "failed")
RETRIEVAL_EVAL_RESULT_STATUSES = ("passed", "missed", "empty", "error")
KNOWLEDGE_RETRIEVAL_FEEDBACK_TYPES = ("helpful", "irrelevant", "missing", "outdated", "needs_review")
KNOWLEDGE_RETRIEVAL_FEEDBACK_STATUSES = ("open", "reviewed", "resolved", "archived")
KNOWLEDGE_RETRIEVAL_FEEDBACK_SOURCES = (
    "sales_reply_citation",
    "retrieval_evaluation_result",
    "manual_review",
)
KNOWLEDGE_IMPROVEMENT_SUGGESTION_TYPES = (
    "update_content",
    "improve_metadata",
    "improve_retrievability",
    "split_knowledge",
    "create_knowledge",
    "promote_eval_case",
)
KNOWLEDGE_IMPROVEMENT_SUGGESTION_STATUSES = ("open", "accepted", "dismissed", "applied", "archived")


class RetrievalEvalCase(Base):
    __tablename__ = "retrieval_eval_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    expected_knowledge_item_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    tags_json: Mapped[list | None] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    results: Mapped[list["RetrievalEvalResult"]] = relationship(back_populates="case")


class RetrievalEvalRun(Base):
    __tablename__ = "retrieval_eval_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False, index=True)
    case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_recall_at_k: Mapped[float] = mapped_column(default=0.0, nullable=False)
    average_precision_at_k: Mapped[float] = mapped_column(default=0.0, nullable=False)
    zero_hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    miss_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    k: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    trigger_source: Mapped[str | None] = mapped_column(String(80), index=True)
    knowledge_item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("knowledge_items.id"), index=True)
    retriever_version: Mapped[str | None] = mapped_column(String(120))
    vector_store: Mapped[str | None] = mapped_column(String(80))
    embedding_model: Mapped[str | None] = mapped_column(String(120))
    reranker_enabled: Mapped[bool | None] = mapped_column(Boolean, default=False)
    reranker_provider: Mapped[str | None] = mapped_column(String(80))
    reranker_model: Mapped[str | None] = mapped_column(String(120))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    results: Mapped[list["RetrievalEvalResult"]] = relationship(
        back_populates="run",
        order_by="RetrievalEvalResult.created_at",
    )


class RetrievalEvalResult(Base):
    __tablename__ = "retrieval_eval_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("retrieval_eval_runs.id"), index=True, nullable=False)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("retrieval_eval_cases.id"), index=True, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    expected_knowledge_item_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    actual_knowledge_item_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    matched_expected_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    missed_expected_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    extra_hit_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    recall_at_k: Mapped[float] = mapped_column(default=0.0, nullable=False)
    precision_at_k: Mapped[float] = mapped_column(default=0.0, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    citation_pack_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="empty", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    run: Mapped["RetrievalEvalRun"] = relationship(back_populates="results")
    case: Mapped["RetrievalEvalCase"] = relationship(back_populates="results")


class KnowledgeRetrievalFeedback(Base):
    __tablename__ = "knowledge_retrieval_feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(30), default="needs_review", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(60), default="manual_review", nullable=False, index=True)
    query: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    knowledge_item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("knowledge_items.id"), index=True)
    expected_knowledge_item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("knowledge_items.id"), index=True)
    artifact_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("artifacts.id"), index=True)
    retrieval_eval_result_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("retrieval_eval_results.id"), index=True)
    opportunity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("opportunities.id"), index=True)
    citation_hit_json: Mapped[dict | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_by: Mapped[str | None] = mapped_column(String(255))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class KnowledgeImprovementSuggestion(Base):
    __tablename__ = "knowledge_improvement_suggestions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    suggestion_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge_item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("knowledge_items.id"), index=True)
    expected_knowledge_item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("knowledge_items.id"), index=True)
    source_feedback_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    evidence_json: Mapped[dict | None] = mapped_column(JSON)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    generator: Mapped[str] = mapped_column(String(80), default="rule_based", nullable=False)
    generator_version: Mapped[str] = mapped_column(String(120), default="knowledge_improvement.rule_v1", nullable=False)
    confidence: Mapped[float | None] = mapped_column()
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
