# ChenForge AI API Contract v0

## 目标

本文档冻结 MVP 阶段前端和后端之间的接口契约，避免字段漂移。所有前端 API client、FastAPI schema、Agent workflow artifact 都必须以本文档为准。

## 全局约定

- API 前缀：`/api/v1`
- 请求和响应均使用 JSON。
- 时间字段使用 ISO 8601 字符串。
- ID 字段使用字符串 UUID。
- 公开接口不需要管理员认证。
- 客户提交需求前需要通过邮箱验证码建立客户会话。
- 后台接口需要管理员认证。
- LLM key 不允许出现在任何前端响应中。

## 错误响应

所有错误统一返回：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "业务问题不能为空",
  "details": {
    "field": "problem"
  },
  "request_id": "req_123"
}
```

字段说明：

- `code`：机器可读错误码。
- `message`：人类可读错误说明。
- `details`：结构化错误详情，可为空对象。
- `request_id`：请求追踪 ID。

## 枚举

### LeadStatus

```text
new
reviewing
diagnosed
proposed
contacted
sent
archived
```

### TaskStatus

```text
pending
running
succeeded
failed
```

### DecisionStatus

```text
waiting
approved
deferred
rewrite_requested
edited_and_approved
```

### ArtifactType

```text
diagnosis
architecture
proposal
email
roadmap
review
audit
requirement_summary
customer_reply_draft
proposal_draft
discovery_questions
delivery_roadmap
sent_message
```

### DeliveryChannel

```text
email
feishu
wecom
sms
client_portal
manual_copy
```

MVP 只实现 `email`。其他通道作为后续扩展，不进入第一版实现。

### DeliveryStatus

```text
draft
queued
sending
sent
failed
cancelled
```

### NotificationChannel

```text
feishu
wecom
email
```

## 数据对象

### Lead

```json
{
  "id": "lead_001",
  "owner_email": "client@example.com",
  "company": "区域连锁门店",
  "contact_name": "陈先生",
  "contact_method": "wechat: example",
  "industry": "连锁零售",
  "problem": "客服重复问答太多，销售资料整理慢",
  "desired_outcome": "企业知识库 / RAG 问答",
  "company_size": "50-200",
  "budget_range": "3-5w",
  "timeline": "30 天内看 PoC",
  "video_links": ["https://example.com/demo-video"],
  "status": "new",
  "created_at": "2026-05-29T00:00:00+08:00",
  "updated_at": "2026-05-29T00:00:00+08:00"
}
```

必填字段：

- `company`
- `owner_email`
- `contact_method`
- `problem`
- `desired_outcome`

可选字段：

- `contact_name`
- `industry`
- `company_size`
- `budget_range`
- `timeline`
- `video_links`

### LeadAttachment

```json
{
  "id": "attachment_001",
  "lead_id": "lead_001",
  "filename": "客服流程截图.png",
  "content_type": "image/png",
  "size_bytes": 245102,
  "storage_key": "uploads/lead_001/attachment_001.png",
  "uploaded_by_email": "client@example.com",
  "created_at": "2026-05-29T00:00:10+08:00"
}
```

### AgentTask

```json
{
  "id": "task_001",
  "lead_id": "lead_001",
  "agent_name": "lead_diagnosis",
  "status": "succeeded",
  "input_json": {},
  "output_json": {},
  "error_message": null,
  "started_at": "2026-05-29T00:01:00+08:00",
  "completed_at": "2026-05-29T00:01:12+08:00"
}
```

### Artifact

```json
{
  "id": "artifact_001",
  "lead_id": "lead_001",
  "type": "diagnosis",
  "title": "初步诊断摘要",
  "content_markdown": "## 初步诊断摘要\n...",
  "content_json": {},
  "model": "mock-llm-v1",
  "prompt_version": "lead_diagnosis.v1",
  "requires_approval": false,
  "approved_at": null,
  "created_at": "2026-05-29T00:01:12+08:00"
}
```

### Decision

```json
{
  "id": "decision_001",
  "lead_id": "lead_001",
  "artifact_id": "artifact_001",
  "question": "是否批准进入 PoC Proposal 草稿生成？",
  "recommendation": "approve",
  "status": "waiting",
  "operator_note": null,
  "created_at": "2026-05-29T00:01:12+08:00",
  "resolved_at": null
}
```

### DeliveryJob

```json
{
  "id": "delivery_001",
  "lead_id": "lead_001",
  "artifact_id": "artifact_002",
  "channel": "email",
  "recipient": "client@example.com",
  "subject": "ChenForge AI：关于您 AI 落地需求的初步建议",
  "body_markdown": "您好，以下是我们的初步理解...",
  "status": "sent",
  "provider_message_id": "email_msg_001",
  "error_message": null,
  "created_at": "2026-05-29T00:05:00+08:00",
  "sent_at": "2026-05-29T00:05:06+08:00"
}
```

### NotificationEvent

```json
{
  "id": "notification_001",
  "lead_id": "lead_001",
  "channel": "feishu",
  "event_type": "lead_created",
  "status": "sent",
  "payload_json": {},
  "error_message": null,
  "created_at": "2026-05-29T00:00:12+08:00"
}
```

## Public API

### POST `/api/v1/auth/email/start`

发送邮箱验证码。

请求：

```json
{
  "email": "client@example.com"
}
```

响应 `202`：

```json
{
  "message": "验证码已发送",
  "expires_in_seconds": 600
}
```

校验规则：

- 邮箱必须合法。
- 同一邮箱 60 秒内只能发送一次。
- 验证码有效期为 10 分钟。

### POST `/api/v1/auth/email/verify`

校验邮箱验证码并建立客户会话。

请求：

```json
{
  "email": "client@example.com",
  "code": "123456"
}
```

响应 `200`：

```json
{
  "session": {
    "email": "client@example.com",
    "expires_at": "2026-05-29T12:00:00+08:00"
  }
}
```

### POST `/api/v1/leads`

创建客户需求。调用前必须已有客户邮箱会话。

请求：

```json
{
  "owner_email": "client@example.com",
  "company": "区域连锁门店",
  "contact_name": "陈先生",
  "contact_method": "wechat: example",
  "industry": "连锁零售",
  "problem": "客服重复问答太多，销售资料整理慢",
  "desired_outcome": "企业知识库 / RAG 问答",
  "company_size": "50-200",
  "budget_range": "3-5w",
  "timeline": "30 天内看 PoC",
  "video_links": ["https://example.com/demo-video"],
  "honeypot": "",
  "submitted_after_ms": 4200
}
```

响应 `201`：

```json
{
  "lead": {
      "id": "lead_001",
      "owner_email": "client@example.com",
      "company": "区域连锁门店",
      "contact_name": "陈先生",
      "contact_method": "wechat: example",
      "industry": "连锁零售",
      "problem": "客服重复问答太多，销售资料整理慢",
      "desired_outcome": "企业知识库 / RAG 问答",
      "company_size": "50-200",
      "budget_range": "3-5w",
      "timeline": "30 天内看 PoC",
      "video_links": ["https://example.com/demo-video"],
      "status": "new",
      "created_at": "2026-05-29T00:00:00+08:00",
      "updated_at": "2026-05-29T00:00:00+08:00"
  }
}
```

校验规则：

- `honeypot` 必须为空。
- `submitted_after_ms` 必须大于等于 `1500`。
- `problem` 最小长度为 10 个字符。
- `owner_email` 必须等于当前客户会话邮箱。

### POST `/api/v1/leads/{lead_id}/attachments`

上传需求附件。MVP 支持文档和截图，不支持视频大文件上传。

请求类型：`multipart/form-data`

字段：

- `file`：必填。

响应 `201`：

```json
{
  "attachment": {}
}
```

校验规则：

- 只允许 `pdf`、`docx`、`xlsx`、`png`、`jpg`、`jpeg`。
- 单文件最大 20MB。
- 该 Lead 必须属于当前客户邮箱会话。

## Admin API

以下接口需要管理员认证。

### GET `/api/v1/leads`

查询线索列表。

Query 参数：

- `status`：可选，LeadStatus。
- `desired_outcome`：可选。
- `q`：可选，按公司或问题搜索。

响应 `200`：

```json
{
  "items": [],
  "total": 0
}
```

### GET `/api/v1/leads/{lead_id}`

查询线索详情。

响应 `200`：

```json
{
  "lead": {},
  "attachments": [],
  "artifacts": [],
  "decisions": [],
  "agent_tasks": [],
  "delivery_jobs": [],
  "notification_events": []
}
```

### PATCH `/api/v1/leads/{lead_id}`

更新线索状态或基础字段。

请求：

```json
{
  "status": "reviewing"
}
```

响应 `200`：

```json
{
  "lead": {}
}
```

### POST `/api/v1/leads/{lead_id}/run-diagnosis`

运行线索诊断工作流。

请求：

```json
{
  "provider": "mock"
}
```

响应 `202`：

```json
{
  "task": {},
  "artifact": {},
  "decision": {}
}
```

### POST `/api/v1/leads/{lead_id}/run-proposal`

运行 Proposal 工作流。

前置条件：

- 该线索必须已有 diagnosis artifact。
- 进入 Proposal 的 decision 必须为 `approved`。

响应 `202`：

```json
{
  "task": {},
  "artifact": {},
  "decision": {}
}
```

### POST `/api/v1/leads/{lead_id}/run-intake-response`

运行需求理解、客户回复草稿和方案草案工作流。

响应 `202`：

```json
{
  "task": {},
  "artifacts": [],
  "decisions": []
}
```

### GET `/api/v1/agent-tasks/{task_id}`

查询 Agent 任务状态。

响应 `200`：

```json
{
  "task": {}
}
```

### GET `/api/v1/leads/{lead_id}/artifacts`

查询某线索的生成物。

响应 `200`：

```json
{
  "items": []
}
```

### GET `/api/v1/artifacts/{artifact_id}`

查询生成物详情。

响应 `200`：

```json
{
  "artifact": {}
}
```

### POST `/api/v1/artifacts/{artifact_id}/approve`

批准生成物。

请求：

```json
{
  "operator_note": "内容可用于客户沟通"
}
```

### PATCH `/api/v1/artifacts/{artifact_id}`

保存负责人修改后的生成物内容。

请求：

```json
{
  "content_markdown": "修改后的客户回复草稿...",
  "operator_note": "压低承诺，补充澄清问题"
}
```

响应 `200`：

```json
{
  "artifact": {}
}
```

### GET `/api/v1/decisions`

查询待决策项。

Query 参数：

- `status`：可选，DecisionStatus，默认 `waiting`。

响应 `200`：

```json
{
  "items": []
}
```

### POST `/api/v1/decisions/{decision_id}/approve`

批准决策。

请求：

```json
{
  "operator_note": "同意进入下一步"
}
```

响应 `200`：

```json
{
  "decision": {}
}
```

### POST `/api/v1/decisions/{decision_id}/defer`

暂缓决策。

请求：

```json
{
  "operator_note": "等待客户补充预算和时间"
}
```

响应 `200`：

```json
{
  "decision": {}
}
```

### POST `/api/v1/decisions/{decision_id}/request-rewrite`

要求重写。

请求：

```json
{
  "operator_note": "语气过度承诺，改得更克制"
}
```

### POST `/api/v1/delivery-jobs`

基于已审批 Artifact 创建发送任务。MVP 只允许 `channel=email`。

请求：

```json
{
  "lead_id": "lead_001",
  "artifact_id": "artifact_002",
  "channel": "email",
  "recipient": "client@example.com",
  "subject": "ChenForge AI：关于您 AI 落地需求的初步建议"
}
```

响应 `201`：

```json
{
  "delivery_job": {}
}
```

前置条件：

- Artifact 必须已审批。
- Artifact 必须属于该 Lead。
- recipient 必须等于 Lead 的 owner_email，或由管理员显式确认。

### POST `/api/v1/delivery-jobs/{delivery_job_id}/send`

发送已创建的 DeliveryJob。

响应 `202`：

```json
{
  "delivery_job": {}
}
```

### GET `/api/v1/delivery-jobs/{delivery_job_id}`

查询发送任务状态。

响应 `200`：

```json
{
  "delivery_job": {}
}
```

## Agent 输出契约

### lead_diagnosis

```json
{
  "pain_summary": "客户当前主要痛点是...",
  "business_goal": "降低重复咨询成本",
  "workflow_candidates": ["客服 FAQ 问答", "销售资料自动整理"],
  "recommended_first_poc": "企业知识库 / RAG 问答",
  "suitability_score": 82,
  "risk_flags": ["资料质量未知", "权限边界需确认"],
  "missing_questions": ["知识库资料在哪里？", "谁负责审核回复？"],
  "next_step_recommendation": "建议先做 5 天流程诊断"
}
```

### proposal

```json
{
  "proposal_summary": "建议从企业知识库问答 PoC 开始",
  "discovery_agenda": ["梳理资料来源", "定义高频问题", "确认审批边界"],
  "poc_scope": ["资料导入", "RAG 问答", "后台审核"],
  "milestones": ["第 1 周诊断", "第 2 周原型", "第 3-4 周试用"],
  "acceptance_metrics": ["FAQ 命中率", "人工咨询减少比例", "审核通过率"],
  "out_of_scope": ["直接替代客服", "自动对外发送"],
  "client_reply_draft": "您好，我建议先从一个边界清晰的知识库问答 PoC 开始..."
}
```

### intake_response

```json
{
  "requirement_summary": {
    "business_context": "客户是一家区域连锁门店...",
    "main_problem": "客服重复问答和销售资料整理效率低",
    "likely_ai_scenarios": ["RAG 知识库", "销售资料助手"],
    "missing_information": ["现有资料位置", "客服审核边界"]
  },
  "customer_reply_draft": {
    "subject": "ChenForge AI：关于您 AI 落地需求的初步理解",
    "body_markdown": "您好，我们已经收到您的需求..."
  },
  "proposal_draft": {
    "recommended_first_poc": "企业知识库 / RAG 问答",
    "scope": ["资料整理", "问答原型", "人工审核后台"],
    "timeline": "建议先用 2-3 周完成 PoC",
    "risks": ["资料质量未知", "权限边界需确认"],
    "next_step": "建议安排一次 45 分钟诊断沟通"
  }
}
```

## 联调检查点

### 第一次联调

- 公开表单提交。
- 后端创建 Lead。
- 后台列表能看到 Lead。

### 第二次联调

- 后台触发诊断。
- mock LLM provider 返回 diagnosis。
- 后端创建 artifact 和 decision。
- 前端展示 artifact 和 decision。

### 第三次联调

- 操作员批准 decision。
- 操作员运行 proposal。
- 后端创建 proposal artifact。
- 前端展示客户回复草稿并提示需要人工审批。

### 第四次联调

- 客户完成邮箱验证码登录。
- 客户提交需求并上传附件。
- 后台收到 Lead、附件和内部通知状态。
- Agent 生成需求理解、客户回复草稿和方案草案。
- 操作员编辑并批准客户回复。
- 后端创建并发送 email DeliveryJob。
- 前端展示发送状态和审计记录。
