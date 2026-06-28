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
    lead_id: str
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
    lead_id: str
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


# ── Common ──
class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict | None = None
    request_id: str | None = None


class PaginatedResponse(BaseModel):
    items: list
    total: int
