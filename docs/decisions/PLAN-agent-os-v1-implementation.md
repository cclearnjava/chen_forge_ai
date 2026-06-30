# PLAN：一人公司 Agent OS V1 实现方案

## 目标

把 ChenForge AI 从“客户生命周期后台”推进到“一人公司 Agent OS”的第一个可演示闭环。

本阶段不追求完整 CRM，也不直接接真实 LLM。目标是先跑通：

```text
Lead / Opportunity
  -> Sales Agent 生成客户回复草稿
  -> Quality Agent 审查草稿风险
  -> 系统创建 Decision
  -> 人工审批
  -> DeliveryJob / Message / AuditLog 留痕
```

这条链路验证产品最核心的判断：Agent 可以提效，但对客动作必须由人类负责人批准。

## 已确认的产品决策

### 1. 产品重心

第一阶段优先做 `Company Cockpit`，但它不是信息密度很高的 CRM 首页，而是“一人老板每天 5 分钟决策入口”。

首页只回答三件事：

- 今天最重要的下一步动作是什么。
- 哪些 Agent 输出需要我审批。
- 哪些客户或机会存在风险。

### 2. 首页风格

采用“安静决策台”。

不把所有客户、线索、消息和报表堆到首页。首页只放少量高优先级队列，详细信息进入机会详情页承接。

### 3. 机会详情页布局

采用“审批动作常驻右侧”。

主区展示客户上下文、Conversation 和 Agent Workbench；右侧固定展示：

- 下一步动作。
- Approval Gate。
- Customer Profile。
- Audit Trail。

这样可以把产品原则可视化：Agent 负责生成建议，人类负责人负责最终经营动作。

### 4. 后端第一阶段重心

优先实现 `Agent + Decision` 审批闭环，而不是先做完整 Cockpit 聚合 API。

原因：

- Cockpit 可以先用已有生命周期 API 和少量聚合查询支撑。
- Agent + Decision 闭环是一人公司 Agent OS 的核心差异。
- 该闭环能同时验证数据模型、Agent 编排、审批、发送和审计。

### 5. Agent 实现策略

采用“确定性 mock Agent 先行”。

第一阶段不直接接 OpenAI-compatible provider。先用稳定模板生成 Agent 输出，保证：

- 测试稳定。
- 审计链路稳定。
- API 和 UI 先跑通。
- 后续可以把 mock provider 替换为真实 provider。

## 用户体验蓝图

### 路由结构

第一阶段前端页面：

```text
/admin
  Company Cockpit

/admin/opportunities
  Opportunity List

/admin/opportunities/[opportunityId]
  Opportunity Detail + Agent Workbench + Approval Gate

/admin/approvals
  Approval Center，后续聚合所有待审批动作
```

`/admin/approvals` 可以在第一阶段后半段实现。最小可演示闭环优先依赖 `/admin/opportunities/[opportunityId]`。

### Company Cockpit

页面目标：

- 展示今日最重要的 3-5 个经营动作。
- 展示待审批 Agent 输出数量。
- 展示风险提醒。
- 点击进入对应 Opportunity 详情页。

推荐模块：

- `Today Brief`：CEO Agent 风格的今日经营摘要，第一版可由后端聚合数据或前端 mock 支撑。
- `Priority Queue`：今日优先处理事项。
- `Waiting Approval`：待审批草稿。
- `Risk Flags`：Quality Agent 或规则产生的风险提示。

不做：

- 大型销售漏斗图。
- 完整客户表格。
- 复杂筛选器。
- 大面积营销式 hero。

### Opportunity Detail

页面目标：

- 让负责人理解客户上下文。
- 查看 Sales Agent 草稿和 Quality Agent 审查。
- 完成人工审批或要求重写。
- 看到动作留痕。

页面布局：

```text
Header
  Opportunity 标题、阶段、预算、概率、下一步动作

Main Column
  Conversation Thread
  Agent Workbench
    Sales Reply Draft
    Discovery Questions
    Quality Review

Right Rail
  Owner Action
  Approval Gate
  Customer Profile
  Audit Trail
```

关键交互：

- 点击 `Run Sales Agent` 生成草稿。
- 点击 `Approve` 批准草稿。
- 点击 `Request rewrite` 要求重写。
- 审批后生成 DeliveryJob，并把最终消息写入 Conversation。

### Approval Center

第一阶段可以先做轻量版。

列表字段：

- Decision 状态。
- 关联客户。
- 关联 Opportunity。
- Artifact 类型。
- 风险等级。
- 创建时间。
- 操作入口。

该页面不是第一阶段最先实现项，先由 Opportunity Detail 的右侧审批卡片承接。

## 后端实现蓝图

### 当前可复用底座

已存在或正在实现：

- `Lead`
- `Customer`
- `Contact`
- `Conversation`
- `Message`
- `Opportunity`
- `Artifact`
- `Decision`
- `DeliveryJob`
- `AuditLog`
- `create_lifecycle_from_lead(db, lead_id)`

### 需要新增或增强的模型

#### AgentProfile

表示一个固定 Agent 角色。

建议字段：

- `id`
- `name`
- `display_name`
- `role`
- `allowed_tools_json`
- `output_artifact_types_json`
- `requires_approval`
- `is_active`
- `created_at`
- `updated_at`

第一阶段内置：

- `sales_agent`
- `quality_agent`
- `ceo_agent` 可先只作为 Cockpit 文案来源，不进入真实 workflow。

#### AgentRun

表示一次 Agent 执行。

建议字段：

- `id`
- `agent_profile_id`
- `opportunity_id`
- `conversation_id`
- `lead_id`
- `status`
- `input_json`
- `output_json`
- `error_message`
- `started_at`
- `completed_at`
- `created_at`

状态建议：

```text
pending
running
succeeded
failed
cancelled
```

#### ToolInvocation

记录 Agent 执行过程中的工具调用。

第一阶段 mock Agent 可以先不真实调用外部工具，但保留记录结构。

建议字段：

- `id`
- `agent_run_id`
- `tool_name`
- `input_json`
- `output_json`
- `status`
- `error_message`
- `created_at`

### 需要新增的服务

#### AgentContextBuilder

职责：

- 根据 `opportunity_id` 读取 Customer、Contact、Conversation、Message、Opportunity。
- 组装 Sales Agent 和 Quality Agent 的输入上下文。
- 屏蔽前端不应该参与的上下文拼装细节。

输入：

- `opportunity_id`

输出：

- `customer`
- `primary_contact`
- `opportunity`
- `recent_messages`
- `known_constraints`

#### MockSalesAgent

职责：

- 基于 Opportunity 和 Conversation 生成确定性回复草稿。
- 生成澄清问题。

输出 Artifact：

- `customer_reply_draft`
- `discovery_questions`

生成策略：

- 使用模板。
- 从 `problem_summary`、`desired_outcome`、`budget_range`、`timeline`、最近客户消息中提取内容。
- 不承诺明确交付范围、价格和验收标准。

#### MockQualityAgent

职责：

- 审查 Sales Agent 的回复草稿。
- 标记潜在风险。

输出 Artifact：

- `review`

风险类型：

- `overpromise`
- `missing_evidence`
- `unclear_scope`
- `pricing_risk`
- `timeline_risk`

第一阶段可以用规则审查：

- 出现“保证”“一定”“免费”“确定上线”等词汇时标记风险。
- 回复中缺少“需要确认/建议先澄清/以 PoC 验收为准”等安全表达时标记 `unclear_scope`。

#### ApprovalService

职责：

- 为需要人工审批的 Artifact 创建 Decision。
- 处理 approve / request rewrite / edit and approve。
- 保证高风险对客动作不能绕过 Decision。

规则：

- `customer_reply_draft` 必须创建 Decision。
- Decision 通过前不能创建对客 Message。
- Decision 通过后才能进入 DeliveryJob。

#### DeliveryService

职责：

- 审批通过后创建 DeliveryJob。
- 第一阶段可以先使用 `manual_copy` 或已有 email 通道。
- 生成 `sent_message` Artifact 或直接写入 Message。
- 写入 AuditLog。

## API 设计

### 运行 Sales Agent

```text
POST /api/v1/admin/opportunities/{opportunity_id}/agent-runs/sales-reply
```

行为：

- 创建 Sales AgentRun。
- 创建 Sales reply Artifact。
- 创建 Discovery questions Artifact。
- 创建 Quality AgentRun。
- 创建 Quality review Artifact。
- 创建 waiting Decision。

响应：

```json
{
  "agent_run": {},
  "artifacts": [],
  "quality_review": {},
  "decision": {}
}
```

### 获取 Opportunity 详情

```text
GET /api/v1/admin/opportunities/{opportunity_id}
```

需要增强返回：

- `opportunity`
- `customer`
- `primary_contact`
- `conversation`
- `messages`
- `agent_runs`
- `artifacts`
- `decisions`
- `audit_logs`

### 审批 Decision

```text
POST /api/v1/admin/decisions/{decision_id}/approve
```

行为：

- 更新 Decision 状态为 `approved`。
- 创建 DeliveryJob。
- 写入 Conversation Message。
- 写入 AuditLog。

### 要求重写

```text
POST /api/v1/admin/decisions/{decision_id}/request-rewrite
```

行为：

- 更新 Decision 状态为 `rewrite_requested`。
- 写入 AuditLog。
- 第一阶段不自动重跑 Agent，先由负责人再次点击 Run Sales Agent。

### 编辑后批准

```text
POST /api/v1/admin/decisions/{decision_id}/edit-and-approve
```

请求：

```json
{
  "content_markdown": "负责人编辑后的最终客户回复"
}
```

行为：

- 创建新的 `sent_message` 或更新 approved output 记录。
- 更新 Decision 状态为 `edited_and_approved`。
- 创建 DeliveryJob。
- 写入 Message。
- 写入 AuditLog。

## 实现顺序

### Slice 1：后端模型和测试

新增：

- `AgentProfile`
- `AgentRun`
- `ToolInvocation`

测试：

- AgentProfile 能创建固定角色。
- AgentRun 能关联 Opportunity 和 Conversation。
- ToolInvocation 能关联 AgentRun。

验收：

- 后端全量测试通过。

### Slice 2：Mock Agent workflow

新增：

- `AgentContextBuilder`
- `MockSalesAgent`
- `MockQualityAgent`
- `run_sales_reply_workflow(db, opportunity_id)`

测试：

- 存在 Opportunity 时能生成 Sales Artifact。
- 能生成 Quality Review Artifact。
- 能创建 waiting Decision。
- 缺少 Opportunity 时 fail-closed。
- 重复运行策略明确：第一阶段允许多次生成新版本，列表按时间倒序展示。

验收：

- 通过一个 service test 跑通 `Opportunity -> Artifact -> Decision`。

### Slice 3：Decision API

新增：

- `backend/app/api/decisions.py`
- approve / request-rewrite / edit-and-approve endpoints

测试：

- approve 后创建 DeliveryJob。
- approve 后写入 Message。
- approve 后写入 AuditLog。
- rewrite request 不创建 DeliveryJob。
- 未审批不能产生对客消息。

验收：

- API test 跑通审批闭环。

### Slice 4：Opportunity 详情 API 增强

增强：

- `GET /api/v1/admin/opportunities/{opportunity_id}`

返回：

- agent_runs
- artifacts
- decisions
- audit_logs

测试：

- 详情接口返回 Agent 输出和 Decision。
- 空 AgentRun 时返回空数组，不报错。

验收：

- 前端 Opportunity Detail 可以只调用一个详情接口渲染核心页面。

### Slice 5：前端绑定真实 API

改造：

- `/admin` 使用安静 Cockpit 布局。
- `/admin/opportunities/[opportunityId]` 使用审批常驻右侧布局。
- 从静态 mock 数据切到后端 API。

交互：

- Run Sales Agent。
- Approve。
- Request rewrite。
- Edit and approve。

验收：

- 浏览器里能从机会详情页运行 Agent、看到草稿、审批并看到消息写回对话。

## 不做范围

第一阶段不做：

- 真实 LLM provider。
- LangGraph。
- 通用 Agent Builder。
- 完整 CRM。
- 合同、财务、项目交付。
- 客户门户。
- 多租户权限系统。
- 自动发送真实邮件给客户。

## 质量和验证要求

后端：

- 每个 service 都要有单元或集成测试。
- 每个高风险动作都要有 AuditLog。
- 对客 Message 只能由审批通过的 Decision 触发。
- mock Agent 输出必须确定性，不能依赖时间随机数生成主要内容。

前端：

- 页面先实现 mock 状态，再切 API。
- 所有主要状态要有空态、加载态、错误态。
- Opportunity Detail 移动端右侧审批栏下移。
- 不做营销式 hero，不使用大面积装饰渐变。

提交：

- 设计文档不需要提交。
- 当天新增代码必须在验证后提交。

## 第一阶段完成定义

完成后应能演示：

```text
1. 负责人打开 Cockpit，看到一个待审批客户动作。
2. 负责人进入 Opportunity Detail。
3. 点击 Run Sales Agent。
4. 系统生成客户回复草稿、澄清问题和 Quality Review。
5. 系统创建 waiting Decision。
6. 负责人点击 Approve。
7. 系统创建 DeliveryJob，并把最终回复写入 Conversation Message。
8. AuditLog 能看到完整链路。
```

这就是一人公司 Agent OS 的第一个稳定纵切。
