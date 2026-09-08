from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Literal


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
    workspace_id: str | None = None
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
    workspace_id: str | None = None
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
    workspace_id: str | None = None
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
    workspace_id: str | None = None
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
    workspace_id: str | None = None
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
    workspace_id: str | None = None
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
    workspace_id: str | None = None
    lead_id: str
    artifact_id: str
    channel: str
    recipient: str
    subject: str
    body_markdown: str
    status: str
    provider_message_id: str | None = None
    error_message: str | None = None
    sent_at: datetime | None = None
    created_at: datetime


class DeliveryJobMarkSentIn(BaseModel):
    operator_note: str = ""


class DeliveryJobMarkSentOut(BaseModel):
    delivery_job: DeliveryJobOut
    sent_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Customer Lifecycle ──
class CustomerOut(BaseModel):
    id: str
    workspace_id: str | None = None
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
    workspace_id: str | None = None
    customer_id: str
    name: str | None = None
    email: str | None = None
    contact_method: str | None = None
    phone: str | None = None
    external_provider: str | None = None
    external_user_id: str | None = None
    role: str | None = None
    is_primary: bool
    source_lead_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: str
    workspace_id: str | None = None
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
    workspace_id: str | None = None
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
    workspace_id: str | None = None
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


# ── Opportunity Message Recording ──
class OpportunityMessageCreateIn(BaseModel):
    body_markdown: str = Field(..., min_length=1)
    sender_label: str | None = None


class RecordedMessageOut(BaseModel):
    id: str
    conversation_id: str
    sender_type: str
    sender_label: str | None = None
    body_markdown: str
    source: str
    created_at: datetime


class RecordedOpportunityOut(BaseModel):
    id: str
    next_step: str | None = None


class OpportunityMessageCreateOut(BaseModel):
    message: RecordedMessageOut
    opportunity: RecordedOpportunityOut


# ── Proposal Draft ──
class ProposalDraftAgentRunOut(BaseModel):
    id: str
    agent_profile_id: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ProposalDraftArtifactOut(BaseModel):
    id: str
    agent_run_id: str | None = None
    type: str
    title: str
    content_markdown: str | None = None
    content_json: dict | None = None
    model: str
    requires_approval: bool
    created_at: datetime


class ProposalDraftDecisionOut(BaseModel):
    id: str
    question: str
    recommendation: str | None = None
    status: str


class ProposalDraftResponseOut(BaseModel):
    agent_run: ProposalDraftAgentRunOut
    artifact: ProposalDraftArtifactOut
    decision: ProposalDraftDecisionOut


# ── Event & Notification ──
class EventOut(BaseModel):
    id: str
    workspace_id: str | None = None
    type: str
    source: str
    severity: str
    subject_type: str | None = None
    subject_id: str | None = None
    actor: str
    title: str
    summary: str | None = None
    payload_json: dict | None = None
    occurred_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: str
    workspace_id: str | None = None
    event_id: str | None = None
    kind: str
    title: str
    body: str | None = None
    severity: str
    status: str
    target_type: str | None = None
    target_id: str | None = None
    target_url: str | None = None
    read_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationSummaryOut(BaseModel):
    unread_count: int = 0
    critical_count: int = 0
    latest: list[NotificationOut] = Field(default_factory=list)


class NotificationDeliveryOut(BaseModel):
    id: str
    workspace_id: str | None = None
    notification_id: str
    channel: str
    recipient: str | None = None
    status: str
    provider: str | None = None
    provider_message_id: str | None = None
    error_message: str | None = None
    attempt_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationMarkReadIn(BaseModel):
    notification_ids: list[str] | None = None

# ── Service Catalog ──
class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    positioning: str | None = None
    target_customer: str | None = None
    typical_duration: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    currency: str = "CNY"
    risk_notes: str | None = None


class ServiceUpdate(BaseModel):
    name: str | None = None
    positioning: str | None = None
    target_customer: str | None = None
    typical_duration: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    currency: str | None = None
    risk_notes: str | None = None


class ServiceOut(BaseModel):
    id: str; workspace_id: str | None = None
    name: str; slug: str; status: str
    positioning: str | None = None; target_customer: str | None = None
    pain_points_json: dict | None = None; outcomes_json: dict | None = None
    required_inputs_json: dict | None = None; success_criteria_json: dict | None = None
    typical_duration: str | None = None
    price_min: int | None = None; price_max: int | None = None; currency: str = "CNY"
    sort_order: int = 0; is_featured: bool = False
    risk_notes: str | None = None
    created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}


class ServiceDetailOut(ServiceOut):
    packages: list = Field(default_factory=list)
    deliverables: list = Field(default_factory=list)
    risk_rules: list = Field(default_factory=list)


# ── Workspace Knowledge Engine (P3) ──

from pydantic import field_validator
from app.models import KNOWLEDGE_STATUSES, KNOWLEDGE_SOURCE_TYPES


class KnowledgeSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class KnowledgeSourceOut(BaseModel):
    id: str; workspace_id: str | None = None
    name: str; description: str | None = None
    created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}


class KnowledgeItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content_markdown: str = Field(..., min_length=1)
    summary: str | None = None
    source_type: str = "manual"
    source_id: str | None = None
    service_id: str | None = None
    tags_json: list[str] = Field(default_factory=list)
    status: str = "active"
    visibility: str = "internal"
    confidence: float | None = None
    metadata_json: dict | None = None

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str) -> str:
        if v not in KNOWLEDGE_STATUSES:
            raise ValueError(f"Invalid status: {v}")
        return v

    @field_validator("source_type")
    @classmethod
    def _check_source_type(cls, v: str) -> str:
        if v not in KNOWLEDGE_SOURCE_TYPES:
            raise ValueError(f"Invalid source_type: {v}")
        return v


class KnowledgeItemUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    content_markdown: str | None = Field(None, min_length=1)
    summary: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    service_id: str | None = None
    tags_json: list[str] | None = None
    status: str | None = None
    visibility: str | None = None
    confidence: float | None = None
    metadata_json: dict | None = None

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str | None) -> str | None:
        if v is not None and v not in KNOWLEDGE_STATUSES:
            raise ValueError(f"Invalid status: {v}")
        return v

    @field_validator("source_type")
    @classmethod
    def _check_source_type(cls, v: str | None) -> str | None:
        if v is not None and v not in KNOWLEDGE_SOURCE_TYPES:
            raise ValueError(f"Invalid source_type: {v}")
        return v


class KnowledgeItemOut(BaseModel):
    id: str; workspace_id: str | None = None
    source_id: str | None = None; service_id: str | None = None
    title: str; summary: str | None = None; content_markdown: str
    source_type: str; tags_json: list[str] = Field(default_factory=list)
    status: str; visibility: str; confidence: float | None = None
    metadata_json: dict | None = None
    archived_at: datetime | None = None
    created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}


class KnowledgeItemListOut(BaseModel):
    items: list[KnowledgeItemOut] = Field(default_factory=list)
    total: int = 0


class KnowledgeReviewDocumentRef(BaseModel):
    id: str
    filename: str


class KnowledgeReviewItemOut(BaseModel):
    item: KnowledgeItemOut
    quality_flags: list[str] = Field(default_factory=list)
    document: KnowledgeReviewDocumentRef | None = None


class KnowledgeReviewListOut(BaseModel):
    items: list[KnowledgeReviewItemOut] = Field(default_factory=list)
    total: int = 0


class KnowledgeReviewBulkRequest(BaseModel):
    item_ids: list[str] = Field(..., min_length=1, max_length=100)
    action: str
    service_id: str | None = None

    @field_validator("action")
    @classmethod
    def _check_action(cls, v: str) -> str:
        if v not in ("activate", "archive", "set_service", "clear_service"):
            raise ValueError(f"Invalid action: {v}")
        return v


class KnowledgeReviewBulkOut(BaseModel):
    updated_count: int = 0
    items: list[KnowledgeItemOut] = Field(default_factory=list)


class KnowledgeDocumentReviewCounts(BaseModel):
    total: int = 0; draft: int = 0; active: int = 0; archived: int = 0


class KnowledgeDocumentOut(BaseModel):
    id: str; workspace_id: str | None = None
    source_id: str | None = None
    filename: str; content_type: str | None = None; file_ext: str | None = None
    storage_path: str; status: str; parser: str | None = None
    text_excerpt: str | None = None; error_message: str | None = None
    item_count: int = 0; metadata_json: dict | None = None
    created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}


class KnowledgeDocumentUploadOut(BaseModel):
    document: KnowledgeDocumentOut
    items: list[KnowledgeItemOut] = Field(default_factory=list)
    item_count: int = 0


class KnowledgeDocumentListOut(BaseModel):
    items: list[KnowledgeDocumentOut] = Field(default_factory=list)
    total: int = 0


class KnowledgeDocumentReviewOut(BaseModel):
    document: KnowledgeDocumentOut
    items: list[KnowledgeItemOut] = Field(default_factory=list)
    counts: KnowledgeDocumentReviewCounts = Field(default_factory=KnowledgeDocumentReviewCounts)
    quality_summary: dict[str, int] = Field(default_factory=dict)


class KnowledgeVectorOut(BaseModel):
    id: str; workspace_id: str | None = None
    knowledge_item_id: str; provider: str; embedding_model: str
    content_hash: str; vector_dim: int = 0
    status: str; error_message: str | None = None
    indexed_at: datetime | None = None
    created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}


class KnowledgeVectorStatusOut(BaseModel):
    knowledge_item_id: str
    status: str  # not_indexed / indexed / stale / failed
    provider: str | None = None
    embedding_model: str | None = None
    vector_dim: int | None = None
    content_hash: str | None = None
    stale: bool = False
    indexed_at: datetime | None = None
    error_message: str | None = None
    vector_store: str | None = None


class KnowledgeVectorReindexRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=100)


class KnowledgeVectorReindexOut(BaseModel):
    indexed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0


# ── Knowledge Retrieval Evaluation (P6.9) ──

class RetrievalEvalCaseCreate(BaseModel):
    query: str = Field(..., min_length=1)
    expected_knowledge_item_ids: list[str] = Field(..., min_length=1, max_length=20)
    tags_json: list[str] = Field(default_factory=list)
    notes: str | None = None


class RetrievalEvalCaseUpdate(BaseModel):
    query: str | None = Field(None, min_length=1)
    expected_knowledge_item_ids: list[str] | None = Field(None, min_length=1, max_length=20)
    tags_json: list[str] | None = None
    notes: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("active", "archived"):
            raise ValueError(f"Invalid status: {v}")
        return v


class RetrievalEvalCaseOut(BaseModel):
    id: str
    workspace_id: str
    query: str
    expected_knowledge_item_ids: list[str] = Field(default_factory=list)
    tags_json: list[str] = Field(default_factory=list)
    notes: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class RetrievalEvalCasePromotionRequest(BaseModel):
    feedback_ids: list[str] = Field(default_factory=list, max_length=50)
    suggestion_id: str | None = None


class RetrievalEvalCasePromotionOut(BaseModel):
    created_count: int = 0
    skipped_count: int = 0
    cases: list[RetrievalEvalCaseOut] = Field(default_factory=list)


class RetrievalEvalRunCreate(BaseModel):
    case_ids: list[str] | None = Field(default=None, max_length=100)
    k: int = Field(default=5, ge=1, le=20)


class RetrievalEvalRunOut(BaseModel):
    id: str
    workspace_id: str
    status: str
    case_count: int = 0
    average_recall_at_k: float = 0.0
    average_precision_at_k: float = 0.0
    zero_hit_count: int = 0
    miss_count: int = 0
    error_count: int = 0
    k: int = 5
    trigger_source: str | None = None
    knowledge_item_id: str | None = None
    retriever_version: str | None = None
    vector_store: str | None = None
    embedding_model: str | None = None
    reranker_enabled: bool | None = False
    reranker_provider: str | None = None
    reranker_model: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class RetrievalEvalResultOut(BaseModel):
    id: str
    workspace_id: str
    run_id: str
    case_id: str
    query: str
    expected_knowledge_item_ids: list[str] = Field(default_factory=list)
    actual_knowledge_item_ids: list[str] = Field(default_factory=list)
    matched_expected_ids: list[str] = Field(default_factory=list)
    missed_expected_ids: list[str] = Field(default_factory=list)
    extra_hit_ids: list[str] = Field(default_factory=list)
    recall_at_k: float = 0.0
    precision_at_k: float = 0.0
    hit_count: int = 0
    citation_pack_json: dict | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class RetrievalEvalRunDetailOut(BaseModel):
    run: RetrievalEvalRunOut
    results: list[RetrievalEvalResultOut] = Field(default_factory=list)


class KnowledgeChangeValidationRequest(BaseModel):
    k: int = Field(default=5, ge=1, le=20)


class KnowledgeChangeValidationOut(BaseModel):
    knowledge_item_id: str
    case_ids: list[str] = Field(default_factory=list)
    case_count: int = 0
    run: RetrievalEvalRunOut
    results: list[RetrievalEvalResultOut] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class KnowledgeChangeValidationHistoryItemOut(BaseModel):
    run: RetrievalEvalRunOut
    results: list[RetrievalEvalResultOut] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class KnowledgeChangeValidationHistoryOut(BaseModel):
    knowledge_item_id: str
    items: list[KnowledgeChangeValidationHistoryItemOut] = Field(default_factory=list)
    total: int = 0


class KnowledgeEngineConnectionCreate(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}
    display_name: str = Field(default="WeKnora", min_length=1, max_length=255)
    endpoint_alias: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9_-]+$")
    credential_ref: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9_-]+$")
    knowledge_base_id: str = Field(min_length=1, max_length=255)
    expected_revision: int = Field(default=0, ge=0)


class KnowledgeEngineConnectionOut(BaseModel):
    """No raw credentials or network address in the public contract."""
    model_config = {"from_attributes": True}
    id: str
    workspace_id: str
    provider: Literal["weknora"]
    display_name: str
    endpoint_alias: str
    knowledge_base_id: str
    knowledge_base_name: str | None = None
    status: Literal["unverified", "ready", "disabled"]
    revision: int
    verified_revision: int | None = None
    verified_upstream_version: str | None = None
    last_checked_at: datetime | None = None
    last_error_code: str | None = None


class WorkspaceKnowledgeConfigUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    provider: Literal["local", "weknora"]
    connection_id: str | None = None
    expected_version: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_connection(self):
        if (self.provider == "local" and self.connection_id is not None) or (
            self.provider == "weknora" and not self.connection_id
        ):
            raise ValueError("connection_id must be set only for weknora")
        return self


class KnowledgeCitationHitV2(BaseModel):
    # Preserve existing retriever-specific score/source fields when serializing.
    model_config = {"extra": "allow"}
    provider: Literal["local", "weknora"]
    reference_id: str = Field(min_length=1)
    knowledge_item_id: str | None = None
    external_reference_id: str | None = None
    title: str
    excerpt: str
    source_type: str
    score: float = Field(allow_inf_nan=False)
    rank: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrieved_at: datetime

    @model_validator(mode="after")
    def validate_identity(self):
        if self.provider == "local":
            if not self.knowledge_item_id or self.external_reference_id is not None:
                raise ValueError("local citations require only knowledge_item_id")
            expected = f"local:{self.knowledge_item_id}"
        else:
            if not self.external_reference_id or self.knowledge_item_id is not None:
                raise ValueError("external citations require only external_reference_id")
            expected = f"external:{self.external_reference_id}"
        if self.reference_id != expected:
            raise ValueError("reference_id does not match provider identity")
        return self


class CitationPackV2(BaseModel):
    model_config = {"extra": "allow"}
    schema_version: Literal[2] = 2
    provider: Literal["local", "weknora"]
    config_version: int = Field(ge=0)
    retriever_version: str
    query_summary: str | None = None
    status: Literal["ok", "empty"]
    no_hit_reason: str | None = None
    hit_count: int = Field(ge=0)
    hits: list[KnowledgeCitationHitV2]
    retrieved_at: datetime
    latency_ms: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_hits(self):
        if self.hit_count != len(self.hits) or (self.status == "ok") != bool(self.hits):
            raise ValueError("citation status and hit_count must match hits")
        if any(hit.provider != self.provider for hit in self.hits):
            raise ValueError("mixed providers are not supported")
        if len({hit.reference_id for hit in self.hits}) != len(self.hits):
            raise ValueError("duplicate citation reference")
        return self


# ── Knowledge Retrieval Feedback (P6.11) ──

KNOWLEDGE_RETRIEVAL_FEEDBACK_TYPES = ("helpful", "irrelevant", "missing", "outdated", "needs_review")
KNOWLEDGE_RETRIEVAL_FEEDBACK_STATUSES = ("open", "reviewed", "resolved", "archived")
KNOWLEDGE_RETRIEVAL_FEEDBACK_SOURCES = (
    "sales_reply_citation",
    "retrieval_evaluation_result",
    "manual_review",
)


class KnowledgeRetrievalFeedbackCreate(BaseModel):
    feedback_type: str = Field(..., max_length=30)
    source: str = Field(..., max_length=60)
    query: str | None = None
    note: str | None = None
    knowledge_item_id: str | None = None
    expected_knowledge_item_id: str | None = None
    artifact_id: str | None = None
    retrieval_eval_result_id: str | None = None
    opportunity_id: str | None = None
    citation_hit_json: dict | None = None
    metadata_json: dict | None = None

    @field_validator("feedback_type")
    @classmethod
    def validate_feedback_type(cls, value: str) -> str:
        if value not in KNOWLEDGE_RETRIEVAL_FEEDBACK_TYPES:
            raise ValueError(f"Invalid feedback_type: {value}")
        return value

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if value not in KNOWLEDGE_RETRIEVAL_FEEDBACK_SOURCES:
            raise ValueError(f"Invalid source: {value}")
        return value


class KnowledgeRetrievalFeedbackUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=20)
    note: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in KNOWLEDGE_RETRIEVAL_FEEDBACK_STATUSES:
            raise ValueError(f"Invalid status: {value}")
        return value


class KnowledgeRetrievalFeedbackOut(BaseModel):
    id: str
    workspace_id: str
    feedback_type: str
    status: str
    source: str
    query: str | None = None
    note: str | None = None
    knowledge_item_id: str | None = None
    expected_knowledge_item_id: str | None = None
    artifact_id: str | None = None
    retrieval_eval_result_id: str | None = None
    opportunity_id: str | None = None
    citation_hit_json: dict | None = None
    metadata_json: dict | None = None
    created_by: str | None = None
    reviewed_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Knowledge Improvement Suggestions (P6.12) ──

KNOWLEDGE_IMPROVEMENT_SUGGESTION_TYPES = (
    "update_content",
    "improve_metadata",
    "improve_retrievability",
    "split_knowledge",
    "create_knowledge",
    "promote_eval_case",
)
KNOWLEDGE_IMPROVEMENT_SUGGESTION_STATUSES = ("open", "accepted", "dismissed", "applied", "archived")


class KnowledgeImprovementSuggestionGenerateRequest(BaseModel):
    feedback_type: str | None = Field(default=None, max_length=30)
    knowledge_item_id: str | None = None
    limit: int = Field(default=200, ge=1, le=500)

    @field_validator("feedback_type")
    @classmethod
    def validate_feedback_type(cls, value: str | None) -> str | None:
        if value is not None and value not in KNOWLEDGE_RETRIEVAL_FEEDBACK_TYPES:
            raise ValueError(f"Invalid feedback_type: {value}")
        return value


class KnowledgeImprovementSuggestionUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=20)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in KNOWLEDGE_IMPROVEMENT_SUGGESTION_STATUSES:
            raise ValueError(f"Invalid status: {value}")
        return value


class KnowledgeImprovementSuggestionOut(BaseModel):
    id: str
    workspace_id: str
    suggestion_type: str
    status: str
    title: str
    reason: str
    recommended_action: str
    knowledge_item_id: str | None = None
    expected_knowledge_item_id: str | None = None
    source_feedback_ids: list[str] = Field(default_factory=list)
    evidence_json: dict | None = None
    metadata_json: dict | None = None
    generator: str
    generator_version: str
    confidence: float | None = None
    accepted_at: datetime | None = None
    dismissed_at: datetime | None = None
    applied_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class KnowledgeImprovementSuggestionGenerateOut(BaseModel):
    created_count: int = 0
    updated_count: int = 0
    suggestions: list[KnowledgeImprovementSuggestionOut] = Field(default_factory=list)


class GuidedKnowledgeEditRequest(BaseModel):
    patch: KnowledgeItemUpdate
    reindex: bool = False


class GuidedKnowledgeEditOut(BaseModel):
    item: KnowledgeItemOut
    suggestion: KnowledgeImprovementSuggestionOut
    vector_status: KnowledgeVectorStatusOut | None = None


class GuidedKnowledgeCreateRequest(BaseModel):
    item: KnowledgeItemCreate
    reindex: bool = False


class GuidedKnowledgeCreateOut(BaseModel):
    item: KnowledgeItemOut
    suggestion: KnowledgeImprovementSuggestionOut
    vector_status: KnowledgeVectorStatusOut | None = None


# ── External Connector (P5) ──

_CONNECTOR_PROVIDERS = ("mock", "email", "feishu", "wechat_work")
_CONNECTOR_STATUSES = ("active", "paused", "disabled")


class ExternalConnectorCreate(BaseModel):
    provider: str = "mock"
    name: str = Field(..., min_length=1, max_length=120)
    config_json: dict | None = None
    secret_ref: str | None = None

    @field_validator("provider")
    @classmethod
    def _check_provider(cls, v: str) -> str:
        if v not in _CONNECTOR_PROVIDERS:
            raise ValueError(f"Invalid provider: {v}")
        return v


class ExternalConnectorUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    status: str | None = None
    config_json: dict | None = None
    secret_ref: str | None = None

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str | None) -> str | None:
        if v is not None and v not in _CONNECTOR_STATUSES:
            raise ValueError(f"Invalid status: {v}")
        return v


class ExternalConnectorOut(BaseModel):
    id: str; workspace_id: str | None = None
    provider: str; name: str; status: str
    config_json: dict | None = None
    secret_ref: str | None = None
    webhook_token: str | None = None
    webhook_path: str | None = None
    last_received_at: datetime | None = None
    created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}


class InboundMessageSenderIn(BaseModel):
    external_user_id: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class InboundMessageRecipientIn(BaseModel):
    address: str | None = None


class InboundMessageCreateIn(BaseModel):
    external_message_id: str = Field(..., min_length=1)
    external_thread_id: str | None = None
    sender: InboundMessageSenderIn
    recipient: InboundMessageRecipientIn | None = None
    body_markdown: str = Field(..., min_length=1)
    occurred_at: datetime | None = None
    raw_payload: dict | None = None

    @field_validator("sender")
    @classmethod
    def _sender_identifiable(cls, v: InboundMessageSenderIn) -> InboundMessageSenderIn:
        if not (v.email or v.phone or v.external_user_id):
            raise ValueError("sender must include email, phone, or external_user_id")
        return v


class InboundMessageCreateOut(BaseModel):
    deduplicated: bool = False
    connector_id: str
    customer: dict | None = None
    contact: dict | None = None
    conversation: dict | None = None
    message: dict | None = None
    event_id: str | None = None
    notification_id: str | None = None
