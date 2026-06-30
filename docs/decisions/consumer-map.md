# ChenForge AI 消费方清单

## API 消费方

| 契约 | 生产方 | 消费方 | 语义 |
| --- | --- | --- | --- |
| `POST /api/v1/leads` | 后端 Lead API | 公开官网 `LeadIntakeForm` | 创建线索 |
| `GET /api/v1/leads` | 后端 Lead API | 后台 `LeadInbox` | 查看线索列表 |
| `GET /api/v1/leads/{lead_id}` | 后端 Lead API | 后台 `LeadDetail` | 查看线索详情 |
| `PATCH /api/v1/leads/{lead_id}` | 后端 Lead API | 后台状态控制 | 更新线索状态 |
| `POST /api/v1/leads/{lead_id}/run-diagnosis` | Agent API | 后台线索详情 | 触发诊断工作流 |
| `POST /api/v1/leads/{lead_id}/run-proposal` | Agent API | 后台线索详情 | 触发 Proposal 工作流 |
| `GET /api/v1/agent-tasks/{task_id}` | Agent API | 后台任务状态展示 | 查询 Agent 任务状态 |
| `GET /api/v1/leads/{lead_id}/artifacts` | Artifact API | 后台生成物列表 | 查询线索生成物 |
| `GET /api/v1/artifacts/{artifact_id}` | Artifact API | 后台生成物查看器 | 查看生成物详情 |
| `POST /api/v1/artifacts/{artifact_id}/approve` | Artifact API | 后台生成物查看器 | 批准生成物 |
| `GET /api/v1/decisions` | Decision API | 后台决策队列 | 查看待决策项 |
| `POST /api/v1/decisions/{decision_id}/approve` | Decision API | 后台决策动作 | 批准决策 |
| `POST /api/v1/decisions/{decision_id}/defer` | Decision API | 后台决策动作 | 暂缓决策 |
| `POST /api/v1/decisions/{decision_id}/request-rewrite` | Decision API | 后台决策动作 | 要求重写 |
| `GET /api/v1/customers` | Customer API | Company Cockpit | 查看客户列表 |
| `GET /api/v1/customers/{customer_id}` | Customer API | 客户详情页 | 查看客户主体和联系人摘要 |
| `GET /api/v1/customers/{customer_id}/conversations` | Conversation API | 客户详情页、Agent context builder | 查看客户沟通线程 |
| `POST /api/v1/conversations/{conversation_id}/messages` | Message API | 客户对话 UI、Delivery Center 回写 | 创建人工或系统消息 |
| `GET /api/v1/opportunities` | Opportunity API | Company Cockpit、销售管线 | 查看机会列表 |
| `GET /api/v1/opportunities/{opportunity_id}` | Opportunity API | 机会详情页、Agent context builder | 查看销售机会详情 |
| `PATCH /api/v1/opportunities/{opportunity_id}` | Opportunity API | 机会详情页、审批动作 | 更新机会阶段或下一步动作 |
| `POST /api/v1/opportunities/{opportunity_id}/run-sales-agent` | Agent API | 机会详情页 | 触发 Sales Agent 回复草稿 |
| `POST /api/v1/opportunities/{opportunity_id}/run-quality-review` | Agent API | 机会详情页、审批中心 | 触发 Quality/Risk Agent 审查 |
| `GET /api/v1/agent-runs/{agent_run_id}` | Agent API | Agent 输出面板 | 查询多步骤 Agent run |
| `GET /api/v1/policy-rules` | Policy API | 审批中心、Agent workbench | 查看高风险动作审批规则 |

## 数据消费方

| 数据模型 | 数据消费方 | 行为消费方 | 可见性消费方 |
| --- | --- | --- | --- |
| Lead | 后台列表、线索详情、Agent workflow | 状态更新、运行诊断 | 后台筛选、搜索、详情页 |
| AgentTask | 后台任务状态、审计日志 | workflow runner、失败重试 | 线索详情任务记录 |
| Artifact | 生成物查看器、Quality Reviewer | 审批、复制、导出 | 线索详情、artifact list |
| Decision | 决策队列、线索详情 | approve/defer/rewrite | 后台决策队列 |
| AuditLog | 线索详情、后续复盘 | 记录动作 | 后台审计时间线 |
| Customer | Company Cockpit、客户详情、Agent context builder | 归并 Lead、绑定 Contact、创建 Opportunity | 客户列表、客户搜索、机会详情 |
| Contact | 客户详情、客户对话、Delivery Center | 绑定消息收件人、更新联系方式 | 客户详情、Conversation header |
| Conversation | 客户详情、Agent context builder、审计时间线 | 创建 Message、触发 Sales Agent | 客户详情、Opportunity 详情 |
| Message | 客户对话线程、Sales Agent、Quality/Risk Agent | 记录客户输入、人工回复、发送回写 | Conversation timeline |
| Opportunity | Company Cockpit、销售管线、CEO Agent | 阶段更新、下一步动作、触发 Sales Agent | 管线看板、客户详情、待跟进列表 |
| AgentProfile | AgentRegistry、ToolRouter、PolicyGuard | 注册角色、限制工具、约束输出类型 | Agent workbench、运行记录 |
| AgentRun | Agent 输出面板、AuditLog、AgentTask 兼容层 | 启动多步骤 workflow、记录状态、失败重试 | Opportunity 详情、Agent run 列表 |
| ToolInvocation | AgentRun 详情、审计排查 | 记录工具输入输出、失败原因 | Agent run 调试视图 |
| PolicyRule | PolicyGuard、ApprovalGate、审批中心 | 判断动作是否需要人工审批 | 审批规则列表、风险提示 |

## 接缝责任

| 接缝 | 生产端 owner | 消费端 owner | 验证 owner |
| --- | --- | --- | --- |
| 公开表单 -> Lead API | 后端 WP | 前端 WP | 联调 WP |
| Lead API -> Dashboard | 后端 WP | 前端后台 WP | 联调 WP |
| Agent workflow -> Artifact | Agent WP | 前端后台 WP | 联调 WP |
| Artifact -> Decision | Agent WP | 前端后台 WP | 联调 WP |
| Decision action -> AuditLog | 后端 WP | 前端后台 WP | 联调 WP |
| Lead -> Customer/Contact/Opportunity | 后端 Agent OS 模型 WP | Company Cockpit WP、Agent context WP | 集成 WP |
| Conversation/Message -> Sales Agent context | Conversation API WP | Agent workflow WP | Agent OS 集成 WP |
| Sales Agent -> Artifact/Decision | Agent workflow WP | Approval Center WP | Agent OS 集成 WP |
| Quality/Risk Agent -> review artifact | Agent workflow WP | Approval Center WP | Agent OS 集成 WP |
| PolicyRule -> ApprovalGate | PolicyGuard WP | Agent workflow WP、Decision API WP | 安全审查 WP |
| Approved Artifact -> DeliveryJob -> Message回写 | Delivery Center WP | Conversation UI WP、AuditLog WP | 端到端联调 WP |

## 一人公司 Agent OS 第一阶段消费者

| 业务链路 | 写入模型 | 读取模型 | 人工接管点 | Golden Journey |
| --- | --- | --- | --- | --- |
| 线索归并客户 | Customer、Contact、Opportunity、AuditLog | Lead | 归并冲突需要人工确认 | 新 Lead 提交后，后台能看到客户和机会 |
| 客户对话沉淀 | Conversation、Message、AuditLog | Customer、Contact、Opportunity | 人工可编辑消息草稿 | 客户问题能进入 Conversation timeline |
| Sales Agent 回复 | AgentRun、Artifact、Decision、AuditLog | Opportunity、Conversation、Message | 回复草稿必须审批 | 负责人能审批 Sales Agent 草稿 |
| Quality/Risk 审查 | AgentRun、Artifact、Decision | Artifact、PolicyRule | 高风险内容要求重写 | 对客草稿被审查后才能发送 |
| 审批后发送 | DeliveryJob、Message、AuditLog | approved Artifact、Contact | 发送前最终确认 | 已审批回复发送后能在对话线程回显 |
