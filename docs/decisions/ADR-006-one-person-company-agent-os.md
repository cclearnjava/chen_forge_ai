# ADR-006：一人公司 Agent OS 总架构

## 状态

Proposed

## 背景

ChenForge AI 的 MVP 已经把公开官网、线索提交、私有后台、Agent 诊断、人工审批和对客发送串成一条可审计的咨询交付闭环。下一阶段的产品方向是把这条闭环升级为“一人公司 Agent OS”：让一个人类负责人借助多个 Agent 承担销售、方案、合同、交付、财务和经营复盘等角色。

这个方向不能简单做成多个聊天机器人。ToB 交付场景最重要的是责任边界、审批链路、对客承诺可追踪、合同和报价可复核。系统必须继续坚持“人类专家负责，Agent 团队提效”，而不是把经营决策和对客动作交给不可审计的自治流程。

## 决策

### 1. 产品形态：Company Cockpit + Agent Workbench

一人公司 Agent OS 的核心界面分为两层：

- `Company Cockpit`：经营驾驶舱，展示客户管线、待审批项、待跟进客户、交付风险和经营摘要。
- `Agent Workbench`：Agent 工作台，展示 Sales、Solution、Contract、Delivery、Finance、Quality/Risk、CEO Agent 生成的草稿、建议和审查结果。

后台不再只是线索列表，而是围绕客户生命周期组织：

```text
Lead -> Customer -> Conversation -> Opportunity -> Proposal -> Contract -> Project -> Finance
```

第一阶段只实现到 `Opportunity + Sales Agent + Quality Agent + Approval Center`，不一次性覆盖完整公司运营。

### 2. Agent 定位：建议者，不是最终执行者

系统保留固定角色的 Agent 团队：

- `CEO Agent`：经营摘要、机会优先级、下一步建议。
- `Sales Agent`：客户回复草稿、澄清问题、跟进计划。
- `Solution Agent`：需求理解、PoC 方案、交付路线图。
- `Contract Agent`：合同草案、条款风险、版本差异说明。
- `Delivery Agent`：项目计划、交付周报、风险报告。
- `Finance Agent`：报价建议、毛利估算、回款提醒。
- `Quality/Risk Agent`：审查对客输出、发现过度承诺和缺证据内容。

所有 Agent 都只能生成 `Artifact`、`Recommendation`、`Decision` 或 `Review`。Agent 不能直接执行高风险业务动作。

### 3. 不可绕过的主链路

所有对客内容和高风险经营动作必须经过以下链路：

```text
Artifact -> Decision -> Human Approval -> DeliveryJob / State Change -> AuditLog
```

高风险动作包括：

- 发送客户消息。
- 批准 Proposal。
- 修改报价。
- 生成或发送合同。
- 改变机会关键阶段。
- 承诺交付范围、周期或验收标准。

这些动作必须由代码层 `PolicyGuard` 和 `ApprovalGate` 约束，不能依赖 prompt 约束。

### 4. 第一阶段业务闭环

第一阶段冻结为 Sales-led agent OS slice：

```text
客户提交需求
  -> 创建 Lead
  -> 归并或创建 Customer / Contact
  -> 创建 Conversation / Message
  -> 创建 Opportunity
  -> Sales Agent 生成客户回复草稿和澄清问题
  -> Quality/Risk Agent 审查草稿
  -> 创建 Decision
  -> 人工审批或要求重写
  -> Delivery Center 发送
  -> AuditLog 留痕
```

这个闭环是后续 CEO、Contract、Delivery、Finance Agent 的最小完整单元。它验证三件事：

- 客户生命周期对象能承接现有 Lead。
- Agent 输出能通过 Artifact/Decision 被人类接管。
- 对客动作能被 DeliveryJob 和 AuditLog 追踪。

### 5. 数据模型演进

保留现有核心模型：

- `Lead`
- `AgentTask`
- `Artifact`
- `Decision`
- `DeliveryJob`
- `NotificationEvent`
- `AuditLog`

第一阶段新增：

- `Customer`：企业客户主体。
- `Contact`：客户联系人。
- `Conversation`：一段客户沟通上下文。
- `Message`：客户、人工、系统或 Agent 的消息记录。
- `Opportunity`：销售机会，承载阶段、金额、概率和下一步动作。
- `AgentProfile`：Agent 角色、允许工具、输出类型和审批策略。
- `AgentRun`：一次完整 Agent 执行，比 `AgentTask` 更适合多步骤链路。
- `ToolInvocation`：Agent 工具调用记录。
- `PolicyRule`：审批规则和自动化边界。

第二阶段再新增：

- `Contract`
- `Project`
- `WorkItem`
- `Invoice`
- `PaymentRecord`

### 6. 编排层演进

MVP 继续使用轻量自定义 workflow runner，不在第一阶段引入 LangGraph。

第一阶段新增的编排组件：

- `AgentRegistry`：注册 AgentProfile。
- `ContextBuilder`：从 Customer、Conversation、Opportunity、Artifact 组装上下文。
- `PolicyGuard`：判断动作是否需要审批、是否允许 Agent 发起。
- `ToolRouter`：限制 Agent 可调用工具。
- `ApprovalGate`：把需要人工决策的输出转换为 Decision。

### 7. 前端演进

前端后台从 Lead dashboard 演进为 Company Cockpit：

- 客户管线视图。
- 客户对话线程。
- 机会详情页。
- Agent 输出面板。
- 审批中心。
- 审计时间线。

第一阶段只实现与 Sales-led slice 相关的最小视图，不做完整 CRM。

## 方案比较

### 聊天室式多 Agent vs 业务对象驱动

- 聊天室式多 Agent 演示感强，但难以落库、审计、测试和审批。
- 业务对象驱动让 Agent 围绕 Customer、Conversation、Opportunity 和 Artifact 工作，便于恢复上下文和追踪责任边界。

裁决：采用业务对象驱动。

### 完整 Agent OS vs 第一阶段业务切片

- 完整 Agent OS 能呈现愿景，但会同时引入销售、合同、交付、财务、权限和前端多个复杂面。
- 第一阶段业务切片能验证一人公司 OS 的最小完整闭环，并复用现有 Lead、Artifact、Decision、DeliveryJob 和 AuditLog。

裁决：先做 Sales-led slice，再扩展 Contract、Delivery、Finance 和 CEO Agent。

### 固定工作流 vs 可配置 Agent 平台

- 可配置平台长期空间大，但第一阶段会让 schema、权限和 UI 过早泛化。
- 固定工作流更适合当前项目的 MVP 约束，也更容易测试和审计。

裁决：第一阶段固定工作流；当两个以上业务切片稳定后，再抽象为可配置 Agent OS。

### 轻量 runner vs LangGraph

- LangGraph 适合复杂状态图，但会增加学习、调试和部署复杂度。
- 当前更重要的是冻结业务边界和审批主链路。

裁决：第一阶段继续使用轻量 runner；LangGraph 作为第二阶段评估项。

## 不变量

- Agent 输出建议，不拥有最终决策权。
- Prompt 不能作为权限系统，权限必须由代码控制。
- 对客内容不能绕过 `Artifact -> Decision -> Approval -> DeliveryJob -> AuditLog`。
- 合同、报价、交付承诺和客户发送都属于高风险动作。
- 新增业务对象必须验证三类公民权：数据消费、行为消费、可见性消费。
- 第一阶段不做完整 CRM、不做支付、不做客户门户、不做通用 Agent Builder。

## 后果

- 后端需要新增客户生命周期模型和 API contract。
- 前端后台需要从 Lead 详情页演进为客户/机会/审批组合视图。
- Agent workflow 需要从硬编码函数演进为 AgentProfile + AgentRun + PolicyGuard。
- 现有 `Artifact`、`Decision`、`DeliveryJob`、`AuditLog` 会成为 Agent OS 的核心稳定层。
- 第一阶段的验收必须从完整客户价值链倒推：客户提交需求后，负责人能审批 Sales Agent 回复并发送，系统能留下完整审计记录。
