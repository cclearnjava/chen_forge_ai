# ChenForge AI API Contract v0

## 目标

本文档冻结 MVP 阶段前端和后端之间的接口契约，避免字段漂移。所有前端 API client、FastAPI schema、Agent workflow artifact 都必须以本文档为准。

## 全局约定

- API 前缀：`/api/v1`
- 请求和响应均使用 JSON。
- 时间字段使用 ISO 8601 字符串。
- ID 字段使用字符串 UUID。
- 公开接口不需要管理员认证。
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
```

## 数据对象

### Lead

```json
{
  "id": "lead_001",
  "company": "区域连锁门店",
  "contact_name": "陈先生",
  "contact_method": "wechat: example",
  "problem": "客服重复问答太多，销售资料整理慢",
  "desired_outcome": "企业知识库 / RAG 问答",
  "company_size": "50-200",
  "budget_range": "3-5w",
  "timeline": "30 天内看 PoC",
  "status": "new",
  "created_at": "2026-05-29T00:00:00+08:00",
  "updated_at": "2026-05-29T00:00:00+08:00"
}
```

必填字段：

- `company`
- `contact_method`
- `problem`
- `desired_outcome`

可选字段：

- `contact_name`
- `company_size`
- `budget_range`
- `timeline`

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

## Public API

### POST `/api/v1/leads`

创建公开线索。

请求：

```json
{
  "company": "区域连锁门店",
  "contact_name": "陈先生",
  "contact_method": "wechat: example",
  "problem": "客服重复问答太多，销售资料整理慢",
  "desired_outcome": "企业知识库 / RAG 问答",
  "company_size": "50-200",
  "budget_range": "3-5w",
  "timeline": "30 天内看 PoC",
  "honeypot": "",
  "submitted_after_ms": 4200
}
```

响应 `201`：

```json
{
  "lead": {
    "id": "lead_001",
    "company": "区域连锁门店",
    "contact_name": "陈先生",
    "contact_method": "wechat: example",
    "problem": "客服重复问答太多，销售资料整理慢",
    "desired_outcome": "企业知识库 / RAG 问答",
    "company_size": "50-200",
    "budget_range": "3-5w",
    "timeline": "30 天内看 PoC",
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
  "artifacts": [],
  "decisions": [],
  "agent_tasks": []
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

响应 `200`：

```json
{
  "decision": {}
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
