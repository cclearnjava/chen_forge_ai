# Agent Runtime Models V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first backend data foundation for Agent OS: `AgentProfile`, `AgentRun`, and `ToolInvocation`, with Pydantic schemas and focused tests.

**Architecture:** Follow the current backend style: SQLAlchemy models live in `backend/app/models.py`, Pydantic schemas live in `backend/app/schemas.py`, and tests create database rows directly through `SessionLocal`. This slice only adds runtime records for future mock Sales/Quality agents; it does not implement workflow services, API routes, frontend UI, real LLM calls, or migrations.

**Tech Stack:** FastAPI, SQLAlchemy ORM, Pydantic v2, SQLite test database, pytest.

---

## Scope

### In Scope

- Add enum `AgentRunStatus`.
- Add model `AgentProfile`.
- Add model `AgentRun`.
- Add model `ToolInvocation`.
- Add relationships among `AgentProfile`, `AgentRun`, and `ToolInvocation`.
- Add optional relationships from `AgentRun` to existing `Lead`, `Opportunity`, and `Conversation`.
- Add Pydantic output schemas:
  - `AgentProfileOut`
  - `AgentRunOut`
  - `ToolInvocationOut`
- Add model tests covering creation, defaults, relationships, and enum count.

### Out of Scope

- No API endpoints.
- No `AgentContextBuilder`.
- No mock Sales Agent.
- No mock Quality Agent.
- No `Artifact -> Decision` workflow.
- No frontend binding.
- No database migration framework.
- No real LLM provider.

## File Structure

### Modify: `backend/app/models.py`

Responsibilities:

- Define persistent SQLAlchemy models and enums.
- Keep names and style consistent with existing models.
- Keep timestamp defaults consistent with existing `utcnow`.

### Modify: `backend/app/schemas.py`

Responsibilities:

- Define API-safe output schemas for the new models.
- Use `model_config = {"from_attributes": True}` to match existing schema style.
- Avoid mutable defaults.

### Modify: `backend/tests/test_models.py`

Responsibilities:

- Extend existing direct model creation tests.
- Verify the new models can be created with realistic Customer Lifecycle context.
- Verify relationship traversal works.
- Verify default statuses are correct.

## Data Model Specification

### Enum: `AgentRunStatus`

Add near existing task/status enums in `backend/app/models.py`.

Values:

```python
class AgentRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
```

Reason:

- `AgentTask` already has `TaskStatus`, but `AgentRun` is a new multi-step Agent OS runtime concept.
- Use a separate enum to avoid coupling old lead diagnosis tasks to the new agent runtime.

### Model: `AgentProfile`

Table name:

```python
__tablename__ = "agent_profiles"
```

Fields:

| Field | Type | Nullable | Default | Index | Notes |
|---|---:|---:|---:|---:|---|
| `id` | `String(36)` | no | `new_uuid` | primary key | UUID string |
| `name` | `String(100)` | no | none | unique + index | machine name, e.g. `sales_agent` |
| `display_name` | `String(255)` | no | none | no | human label |
| `role` | `Text` | no | none | no | role description |
| `allowed_tools_json` | `JSON` | yes | none | no | list or dict of allowed tools |
| `output_artifact_types_json` | `JSON` | yes | none | no | allowed artifact types |
| `requires_approval` | `Boolean` | no | `True` | no | default conservative |
| `is_active` | `Boolean` | no | `True` | index | inactive profiles cannot be used by runtime services |
| `created_at` | `DateTime` | no | `utcnow` | no | existing project style |
| `updated_at` | `DateTime` | no | `utcnow`, `onupdate=utcnow` | no | existing project style |

Relationships:

```python
runs: Mapped[list["AgentRun"]] = relationship(back_populates="agent_profile")
```

Implementation snippet:

```python
class AgentProfile(Base):
    __tablename__ = "agent_profiles"

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
```

### Model: `AgentRun`

Table name:

```python
__tablename__ = "agent_runs"
```

Fields:

| Field | Type | Nullable | Default | Index | Notes |
|---|---:|---:|---:|---:|---|
| `id` | `String(36)` | no | `new_uuid` | primary key | UUID string |
| `agent_profile_id` | `String(36)` | no | none | yes | FK to `agent_profiles.id` |
| `lead_id` | `String(36)` | yes | none | yes | FK to `leads.id` |
| `opportunity_id` | `String(36)` | yes | none | yes | FK to `opportunities.id` |
| `conversation_id` | `String(36)` | yes | none | yes | FK to `conversations.id` |
| `status` | `SAEnum(AgentRunStatus)` | no | `pending` | yes | runtime state |
| `input_json` | `JSON` | yes | none | no | context snapshot |
| `output_json` | `JSON` | yes | none | no | final structured output |
| `error_message` | `Text` | yes | none | no | failure reason |
| `started_at` | `DateTime` | yes | none | no | start timestamp |
| `completed_at` | `DateTime` | yes | none | no | end timestamp |
| `created_at` | `DateTime` | no | `utcnow` | no | existing project style |

Relationships:

```python
agent_profile: Mapped["AgentProfile"] = relationship(back_populates="runs")
lead: Mapped["Lead | None"] = relationship()
opportunity: Mapped["Opportunity | None"] = relationship()
conversation: Mapped["Conversation | None"] = relationship()
tool_invocations: Mapped[list["ToolInvocation"]] = relationship(
    back_populates="agent_run",
    order_by="ToolInvocation.created_at",
)
```

Implementation snippet:

```python
class AgentRun(Base):
    __tablename__ = "agent_runs"

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
```

### Model: `ToolInvocation`

Table name:

```python
__tablename__ = "tool_invocations"
```

Fields:

| Field | Type | Nullable | Default | Index | Notes |
|---|---:|---:|---:|---:|---|
| `id` | `String(36)` | no | `new_uuid` | primary key | UUID string |
| `agent_run_id` | `String(36)` | no | none | yes | FK to `agent_runs.id` |
| `tool_name` | `String(100)` | no | none | index | e.g. `context_builder` |
| `input_json` | `JSON` | yes | none | no | tool input |
| `output_json` | `JSON` | yes | none | no | tool output |
| `status` | `String(50)` | no | `"succeeded"` | index | keep simple for v1 |
| `error_message` | `Text` | yes | none | no | failure reason |
| `created_at` | `DateTime` | no | `utcnow` | no | existing project style |

Relationships:

```python
agent_run: Mapped["AgentRun"] = relationship(back_populates="tool_invocations")
```

Implementation snippet:

```python
class ToolInvocation(Base):
    __tablename__ = "tool_invocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    agent_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_runs.id"), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_json: Mapped[dict | None] = mapped_column(JSON)
    output_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="succeeded", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    agent_run: Mapped["AgentRun"] = relationship(back_populates="tool_invocations")
```

## Schema Specification

Add the following section in `backend/app/schemas.py` after the existing `AgentTaskOut` and `RunAgentRequest` schemas, or near the future Agent section.

```python
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
```

No create/update schemas are required in this slice because no API route is implemented yet.

## Test Data Pattern

Use the existing direct `SessionLocal()` style in `backend/tests/test_models.py`.

Create reusable local setup inside each test rather than adding shared fixtures in this slice. This keeps the change small and consistent with current tests.

Minimal lifecycle context needed for an `AgentRun`:

```python
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
```

## Tasks

### Task 1: Add Agent Runtime Models

**Files:**

- Modify: `backend/app/models.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing imports and enum assertion**

Update imports in `backend/tests/test_models.py`:

```python
from app.models import (
    Lead, VerificationCode, LeadAttachment, AgentTask,
    Artifact, Decision, DeliveryJob, NotificationEvent, AuditLog,
    Customer, Contact, Conversation, Message, Opportunity,
    AgentProfile, AgentRun, ToolInvocation,
    LeadStatus, TaskStatus, AgentRunStatus, DecisionStatus, ArtifactType,
    DeliveryChannel, DeliveryStatus, NotificationChannel, NotificationStatus,
    ConversationStatus, MessageSenderType, OpportunityStage,
)
```

Update `test_all_enums`:

```python
def test_all_enums():
    assert len(LeadStatus) == 7
    assert len(TaskStatus) == 4
    assert len(AgentRunStatus) == 5
    assert len(DecisionStatus) == 5
    assert len(DeliveryStatus) == 6
    assert len(NotificationChannel) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend
./.venv/bin/python3 -m pytest tests/test_models.py::test_all_enums -q
```

Expected:

```text
ImportError: cannot import name 'AgentProfile'
```

If the failure is for `AgentRunStatus` first, that is also acceptable because none of the new symbols exist yet.

- [ ] **Step 3: Implement enum and models**

In `backend/app/models.py`:

- Add `AgentRunStatus` after `TaskStatus`.
- Add `AgentProfile`, `AgentRun`, and `ToolInvocation` after `AgentTask` or after `Opportunity`.
- Use the exact field definitions from this document.

- [ ] **Step 4: Run enum test**

Run:

```bash
cd backend
./.venv/bin/python3 -m pytest tests/test_models.py::test_all_enums -q
```

Expected:

```text
1 passed
```

### Task 2: Test AgentProfile Creation Defaults

**Files:**

- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: Add failing test**

Add:

```python
def test_create_agent_profile():
    db = SessionLocal()
    profile = AgentProfile(
        name="sales_agent",
        display_name="Sales Agent",
        role="生成客户回复草稿和澄清问题",
        allowed_tools_json={"tools": ["context_builder"]},
        output_artifact_types_json={"types": ["customer_reply_draft", "discovery_questions"]},
    )
    db.add(profile)
    db.commit()

    saved = db.query(AgentProfile).filter(AgentProfile.name == "sales_agent").one()
    assert saved.id is not None
    assert saved.requires_approval is True
    assert saved.is_active is True
    assert saved.allowed_tools_json == {"tools": ["context_builder"]}
    assert saved.output_artifact_types_json == {"types": ["customer_reply_draft", "discovery_questions"]}
    assert saved.created_at is not None
    assert saved.updated_at is not None
```

- [ ] **Step 2: Run test**

Run:

```bash
cd backend
./.venv/bin/python3 -m pytest tests/test_models.py::test_create_agent_profile -q
```

Expected:

```text
1 passed
```

### Task 3: Test AgentRun Relationships

**Files:**

- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: Add failing relationship test**

Add:

```python
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
```

- [ ] **Step 2: Run test**

Run:

```bash
cd backend
./.venv/bin/python3 -m pytest tests/test_models.py::test_create_agent_run_for_opportunity_context -q
```

Expected:

```text
1 passed
```

### Task 4: Test ToolInvocation Relationship

**Files:**

- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: Add failing tool invocation test**

Add:

```python
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
```

- [ ] **Step 2: Run test**

Run:

```bash
cd backend
./.venv/bin/python3 -m pytest tests/test_models.py::test_create_tool_invocation_for_agent_run -q
```

Expected:

```text
1 passed
```

### Task 5: Add Pydantic Schemas

**Files:**

- Modify: `backend/app/schemas.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: Add schema imports and serialization test**

In `backend/tests/test_models.py`, import schemas near the top:

```python
from app.schemas import AgentProfileOut, AgentRunOut, ToolInvocationOut
```

Add:

```python
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
```

- [ ] **Step 2: Run test to verify it fails before schemas exist**

Run:

```bash
cd backend
./.venv/bin/python3 -m pytest tests/test_models.py::test_agent_runtime_schemas_serialize_from_models -q
```

Expected:

```text
ImportError: cannot import name 'AgentProfileOut'
```

- [ ] **Step 3: Implement schemas**

In `backend/app/schemas.py`, add:

```python
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
```

- [ ] **Step 4: Run schema test**

Run:

```bash
cd backend
./.venv/bin/python3 -m pytest tests/test_models.py::test_agent_runtime_schemas_serialize_from_models -q
```

Expected:

```text
1 passed
```

### Task 6: Full Backend Verification

**Files:**

- Verify: all backend tests

- [ ] **Step 1: Run focused model tests**

Run:

```bash
cd backend
./.venv/bin/python3 -m pytest tests/test_models.py -q
```

Expected:

```text
all tests in tests/test_models.py pass
```

- [ ] **Step 2: Run full backend tests**

Run:

```bash
cd backend
./.venv/bin/python3 -m pytest tests -q
```

Expected:

```text
all backend tests pass
```

- [ ] **Step 3: Run whitespace check**

Run:

```bash
git diff --check
```

Expected:

```text
no output
```

- [ ] **Step 4: Commit code changes only**

Stage only code and test files from this slice:

```bash
git add backend/app/models.py backend/app/schemas.py backend/tests/test_models.py
```

Commit message:

```text
Add agent runtime models

新增 AgentProfile、AgentRun、ToolInvocation 后端模型、schema 和测试，为 Agent OS 审批闭环打底。

Co-Authored-By: Codex Opus 4.6 <noreply@anthropic.com>
```

Do not stage design docs, `.superpowers/`, `.wow-harness/`, frontend mock files, or unrelated backend API work.

## Acceptance Criteria

- `AgentRunStatus` exists and has exactly five states.
- `AgentProfile` can persist a named fixed agent role.
- `AgentProfile.name` is unique and indexed.
- `AgentProfile.requires_approval` defaults to `True`.
- `AgentProfile.is_active` defaults to `True`.
- `AgentRun` can link to `AgentProfile`.
- `AgentRun` can optionally link to `Lead`, `Opportunity`, and `Conversation`.
- `AgentRun.status` defaults to `pending`.
- `ToolInvocation` can link to `AgentRun`.
- `ToolInvocation.status` defaults to `succeeded`.
- Pydantic output schemas can serialize SQLAlchemy model instances.
- `backend/.venv` is not committed.
- Full backend test suite passes before commit.

## Notes for the Next Slice

After this slice lands, the next development task should be:

```text
Mock Sales/Quality workflow:
Opportunity -> AgentRun -> Artifact -> Quality Review -> waiting Decision
```

That next slice should create service-level tests first and should not add frontend code until the backend workflow API is stable.
