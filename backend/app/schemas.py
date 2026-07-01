from pydantic import BaseModel, Field
from datetime import datetime


# ── Lead ──
class LeadCreate(BaseModel):
    owner_email: str = Field(..., max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    contact_name: str | None = None
    contact_method: str = Field(..., max_length=255)
    industry: str | None = None
    problem: str = Field(..., min_length=10)
    desired_outcome: str = Field(..., max_length=255)
    company_size: str | None = None
    budget_range: str | None = None
    timeline: str | None = None
    video_links: list[str] | None = None
    honeypot: str = ""
    submitted_after_ms: int = 0


class LeadUpdate(BaseModel):
    status: str | None = None
    contact_name: str | None = None
    contact_method: str | None = None


class LeadOut(BaseModel):
    id: str
    owner_email: str
    company: str
    contact_name: str | None = None
    contact_method: str
    industry: str | None = None
    problem: str
    desired_outcome: str
    company_size: str | None = None
    budget_range: str | None = None
    timeline: str | None = None
    video_links: list[str] | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Auth ──
class EmailStartRequest(BaseModel):
    email: str = Field(..., max_length=255)


class EmailVerifyRequest(BaseModel):
    email: str = Field(..., max_length=255)
    code: str = Field(..., min_length=6, max_length=6)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Attachment ──
class AttachmentOut(BaseModel):
    id: str
    lead_id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    uploaded_by_email: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Artifact ──
class ArtifactOut(BaseModel):
    id: str
    lead_id: str | None = None
    agent_run_id: str | None = None
    opportunity_id: str | None = None
    type: str
    title: str
    content_markdown: str | None = None
    content_json: dict | None = None
    model: str
    prompt_version: str
    requires_approval: bool
    approved_at: datetime | None = None
    version_history: list | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ArtifactUpdate(BaseModel):
    content_markdown: str
    operator_note: str = ""


class ArtifactApprove(BaseModel):
    operator_note: str = ""


# ── Decision ──
class DecisionOut(BaseModel):
    id: str
    lead_id: str | None = None
    agent_run_id: str | None = None
    opportunity_id: str | None = None
    artifact_id: str | None = None
    question: str
    recommendation: str | None = None
    status: str
    operator_note: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class DecisionAction(BaseModel):
    operator_note: str = ""


# ── Agent ──
class AgentTaskOut(BaseModel):
    id: str
    lead_id: str
    agent_name: str
    status: str
    input_json: dict | None = None
    output_json: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class RunAgentRequest(BaseModel):
    provider: str = "mock"


class AgentProfileOut(BaseModel):
    id: str
    name: str
    display_name: str
    role: str
    allowed_tools_json: dict | None = None
    output_artifact_types_json: dict | None = None
    requires_approval: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentRunOut(BaseModel):
    id: str
    agent_profile_id: str
    lead_id: str | None = None
    opportunity_id: str | None = None
    conversation_id: str | None = None
    status: str
    input_json: dict | None = None
    output_json: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ToolInvocationOut(BaseModel):
    id: str
    agent_run_id: str
    tool_name: str
    input_json: dict | None = None
    output_json: dict | None = None
    status: str
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Delivery ──
class DeliveryJobCreate(BaseModel):
    lead_id: str
    artifact_id: str
    channel: str = "email"
    recipient: str = Field(..., max_length=255)
    subject: str = Field(..., max_length=500)


class DeliveryJobOut(BaseModel):
    id: str
    lead_id: str
    artifact_id: str
    channel: str
    recipient: str
    subject: str
    body_markdown: str
    status: str
    provider_message_id: str | None = None
    error_message: str | None = None
    created_at: datetime
    sent_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Customer Lifecycle ──
class CustomerOut(BaseModel):
    id: str
    name: str
    owner_email: str
    industry: str | None = None
    company_size: str | None = None
    source_lead_id: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContactOut(BaseModel):
    id: str
    customer_id: str
    name: str | None = None
    email: str | None = None
    contact_method: str | None = None
    role: str | None = None
    is_primary: bool
    source_lead_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: str
    customer_id: str
    lead_id: str | None = None
    primary_contact_id: str | None = None
    title: str
    channel: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    customer_id: str
    contact_id: str | None = None
    sender_type: str
    sender_label: str | None = None
    body_markdown: str
    source: str
    external_message_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OpportunityOut(BaseModel):
    id: str
    customer_id: str
    lead_id: str | None = None
    primary_contact_id: str | None = None
    conversation_id: str | None = None
    title: str
    stage: str
    desired_outcome: str | None = None
    problem_summary: str | None = None
    budget_range: str | None = None
    estimated_value: int | None = None
    probability: int | None = None
    next_step: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LifecycleOut(BaseModel):
    customer: CustomerOut
    contact: ContactOut
    conversation: ConversationOut
    message: MessageOut
    opportunity: OpportunityOut


class OpportunityUpdate(BaseModel):
    stage: str | None = None
    next_step: str | None = None
    estimated_value: int | None = None
    probability: int | None = None
    desired_outcome: str | None = None
    problem_summary: str | None = None
    budget_range: str | None = None


class MessageCreate(BaseModel):
    body_markdown: str = Field(..., min_length=1)
    sender_type: str = "owner"
    source: str = "manual"


class CustomerDetailOut(CustomerOut):
    contacts: list[ContactOut] = Field(default_factory=list)
    opportunities: list[OpportunityOut] = Field(default_factory=list)
    recent_conversations: list[ConversationOut] = Field(default_factory=list)


class OpportunityDetailOut(OpportunityOut):
    customer: CustomerOut | None = None
    primary_contact: ContactOut | None = None
    conversation: ConversationOut | None = None
    recent_messages: list[MessageOut] = Field(default_factory=list)


# ── Common ──
class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict | None = None
    request_id: str | None = None


class PaginatedResponse(BaseModel):
    items: list
    total: int


# ── Admin Cockpit ──
class CockpitOpportunityOut(BaseModel):
    id: str
    customer_id: str
    lead_id: str | None = None
    primary_contact_id: str | None = None
    conversation_id: str | None = None
    title: str
    stage: str
    desired_outcome: str | None = None
    problem_summary: str | None = None
    budget_range: str | None = None
    estimated_value: int | None = None
    probability: int | None = None
    next_step: str | None = None
    created_at: datetime
    updated_at: datetime


class CockpitCustomerOut(BaseModel):
    id: str
    name: str
    owner_email: str
    industry: str | None = None
    company_size: str | None = None


class CockpitContactOut(BaseModel):
    id: str
    name: str | None = None
    email: str | None = None
    contact_method: str | None = None
    is_primary: bool


class CockpitConversationOut(BaseModel):
    id: str
    title: str
    channel: str
    status: str


class CockpitMessageOut(BaseModel):
    id: str
    sender_type: str
    sender_label: str | None = None
    body_markdown: str
    source: str
    created_at: datetime


class CockpitArtifactOut(BaseModel):
    id: str
    agent_run_id: str | None = None
    type: str
    title: str
    content_markdown: str | None = None
    content_json: dict | None = None
    model: str
    requires_approval: bool
    created_at: datetime


class CockpitDecisionOut(BaseModel):
    id: str
    agent_run_id: str | None = None
    artifact_id: str | None = None
    question: str
    recommendation: str | None = None
    status: str
    operator_note: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class CockpitDeliveryJobOut(BaseModel):
    id: str
    artifact_id: str
    channel: str
    recipient: str
    subject: str
    body_markdown: str
    status: str
    created_at: datetime
    sent_at: datetime | None = None


class CockpitAuditLogOut(BaseModel):
    id: str
    actor: str
    action: str
    details_json: dict | None = None
    created_at: datetime


class CockpitAgentRunOut(BaseModel):
    id: str
    agent_profile_id: str
    status: str
    input_json: dict | None = None
    output_json: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class AdminOpportunityCockpitOut(BaseModel):
    opportunity: CockpitOpportunityOut
    customer: CockpitCustomerOut | None = None
    contact: CockpitContactOut | None = None
    conversation: CockpitConversationOut | None = None
    messages: list[CockpitMessageOut] = Field(default_factory=list)
    artifacts: list[CockpitArtifactOut] = Field(default_factory=list)
    decisions: list[CockpitDecisionOut] = Field(default_factory=list)
    delivery_jobs: list[CockpitDeliveryJobOut] = Field(default_factory=list)
    audit_logs: list[CockpitAuditLogOut] = Field(default_factory=list)
    agent_runs: list[CockpitAgentRunOut] = Field(default_factory=list)
