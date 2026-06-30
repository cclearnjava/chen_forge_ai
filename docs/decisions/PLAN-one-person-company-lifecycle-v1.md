# PLAN：一人公司 Agent OS 客户生命周期 V1

## 目标

把 ChenForge AI 从“线索处理系统”推进到“一人公司 Agent OS”的第一块可运行业务底座。

本阶段要跑通：

```text
客户提交 Lead
  -> 系统自动生成 Customer / Contact / Conversation / Message / Opportunity
  -> 后台能查看客户、机会和第一条客户消息
  -> 后续 Sales Agent 能基于 Opportunity + Conversation 工作
```

## 面向产品的解释

当前系统已经能接收客户提交的需求，也已经有 Agent 诊断和人工审批的雏形。但如果要做“一人公司 Agent OS”，系统不能只停留在 `Lead`。`Lead` 只是一次提交；公司经营需要持续追踪客户、联系人、对话、销售机会和后续动作。

因此 V1 的产品重点是：

- 客户提交需求后，后台不仅出现一条线索，还要出现一个客户和一个销售机会。
- 负责人能看到客户是谁、说了什么、现在处于什么机会阶段、下一步该做什么。
- 后续 Sales Agent 不再只读 Lead 表单，而是读完整的客户对话和机会上下文。

## 本阶段范围

### 必须实现

- Lead 创建后自动生成客户生命周期对象。
- 后台可读取 Customer 列表和详情。
- 后台可读取 Opportunity 列表和详情。
- 后台可读取 Conversation 下的 Message。
- Opportunity 详情能展示关联客户、关联对话和第一条客户问题。
- 后端有测试覆盖核心链路。

### 本阶段不做

- 不做完整 CRM。
- 不做客户门户。
- 不做合同、财务、交付项目。
- 不做真实 Sales Agent 生成内容。
- 不做复杂机会自动评分。
- 不做多渠道消息同步，只先支持从 Lead 表单生成第一条消息。

## 当前已完成

### 后端模型

已新增：

- `Customer`
- `Contact`
- `Conversation`
- `Message`
- `Opportunity`

已新增枚举：

- `ConversationStatus`
- `MessageSenderType`
- `OpportunityStage`

### 后端服务

已新增：

- `create_lifecycle_from_lead(db, lead_id)`

该服务会：

- 查找 Lead。
- 防止同一个 Lead 重复生成生命周期对象。
- 创建 Customer。
- 创建主 Contact。
- 创建 Conversation。
- 把 `Lead.problem` 写成第一条客户 Message。
- 创建 Opportunity。
- 写入 `AuditLog(customer_lifecycle_created)`。

### 测试

已覆盖：

- 生命周期对象生成成功。
- 缺失 Lead 时 fail-closed。
- 重复执行时 fail-closed。
- 后端全量测试通过。

## 后端实现清单

### 1. Lead API 接入生命周期服务

文件建议：

- `backend/app/api/leads.py`
- `backend/app/services/customer_lifecycle.py`
- `backend/tests/test_leads.py` 或新增 `backend/tests/test_lead_lifecycle_api.py`

任务：

- 在 `POST /api/v1/leads` 创建 Lead 后调用 `create_lifecycle_from_lead`。
- API 响应返回：

```json
{
  "lead": {},
  "lifecycle": {
    "customer": {"id": "..."},
    "contact": {"id": "..."},
    "conversation": {"id": "..."},
    "message": {"id": "..."},
    "opportunity": {"id": "..."}
  }
}
```

验收：

- 提交 Lead 后，数据库同时出现 Customer、Contact、Conversation、Message、Opportunity。
- `Message.body_markdown` 等于客户提交的 `problem`。
- `Opportunity.stage` 默认为 `qualified`。
- 写入一条 `customer_lifecycle_created` 审计日志。

### 2. 事务边界整理

当前 `create_lifecycle_from_lead` 内部会 `commit`。接入 Lead API 时需要冻结事务策略。

推荐策略：

- Lead 和 lifecycle 同事务成功。
- 如果 lifecycle 失败，Lead 创建也回滚。
- 避免出现“Lead 有了，但客户管线缺失”的半套状态。

验收：

- 测试模拟 lifecycle 失败时，不产生半套 Customer/Opportunity。

### 3. Customer API

建议 endpoint：

```text
GET /api/v1/admin/customers
GET /api/v1/admin/customers/{customer_id}
```

列表返回字段：

- `id`
- `name`
- `owner_email`
- `industry`
- `company_size`
- `primary_contact`
- `opportunity_count`
- `created_at`
- `updated_at`

详情返回字段：

- customer 基础信息
- contacts
- opportunities
- recent conversations

验收：

- admin 能查看客户列表。
- admin 能搜索公司名或 owner_email。
- 非 admin 不能访问。

### 4. Opportunity API

建议 endpoint：

```text
GET /api/v1/admin/opportunities
GET /api/v1/admin/opportunities/{opportunity_id}
PATCH /api/v1/admin/opportunities/{opportunity_id}
```

列表支持：

- 按 `stage` 筛选。
- 按公司名或机会标题搜索。
- 按更新时间倒序。

详情返回：

- opportunity 基础信息
- customer
- primary_contact
- conversation
- recent messages

可更新字段：

- `stage`
- `next_step`
- `estimated_value`
- `probability`

验收：

- admin 能查看机会列表和详情。
- admin 能更新阶段和下一步动作。
- 更新写入 AuditLog。

### 5. Conversation / Message API

建议 endpoint：

```text
GET /api/v1/admin/conversations/{conversation_id}/messages
POST /api/v1/admin/conversations/{conversation_id}/messages
```

第一阶段消息来源：

- `lead_form`
- `manual`
- `system`
- `delivery`

第一阶段 sender type：

- `customer`
- `owner`
- `agent`
- `system`

验收：

- admin 能查看某个 conversation 的消息。
- admin 能手动添加 owner message。
- 新消息写入 AuditLog。

### 6. Pydantic schema

建议新增：

- `CustomerOut`
- `ContactOut`
- `ConversationOut`
- `MessageOut`
- `OpportunityOut`
- `LifecycleOut`
- `OpportunityUpdate`
- `MessageCreate`

验收：

- API 不直接裸返回 SQLAlchemy 对象。
- enum 输出为字符串。
- 时间字段使用 ISO 8601。

## 前端实现清单

### 1. API client

建议新增：

- `fetchCustomers`
- `fetchCustomerDetail`
- `fetchOpportunities`
- `fetchOpportunityDetail`
- `updateOpportunity`
- `fetchConversationMessages`
- `createConversationMessage`

验收：

- 所有函数集中管理 API 路径。
- 错误响应能被 UI 显示。
- 类型字段与后端 schema 对齐。

### 2. Company Cockpit 首页模块

第一阶段展示：

- 客户总数。
- 新机会数量。
- 待跟进机会。
- 最近客户消息。

验收：

- 页面能让负责人一眼看到今天该跟进什么。
- 空态清晰，不需要解释性大段文案。

### 3. 客户列表页

字段：

- 公司名。
- 主联系人。
- 行业。
- 公司规模。
- 最近更新时间。
- 当前机会数量。

交互：

- 搜索客户。
- 点击进入客户详情。

### 4. 客户详情页

展示：

- 客户基础信息。
- 联系人。
- 关联 Lead。
- 关联 Opportunity。
- 最近 Conversation。
- 审计时间线占位。

验收：

- 从客户详情能跳到机会详情。
- 能看到客户从哪个 Lead 转化而来。

### 5. 机会列表页

展示方式：

- 第一版可以先做列表，不必先做 Kanban。

字段：

- 机会标题。
- 公司名。
- 阶段。
- desired outcome。
- next step。
- budget range。
- 创建时间/更新时间。

筛选：

- `lead`
- `qualified`
- `proposal`
- `negotiation`
- `won`
- `lost`
- `archived`

### 6. 机会详情页

展示：

- Opportunity 基础信息。
- 阶段修改。
- 关联客户。
- 关联联系人。
- 关联 Conversation。
- 下一步动作。
- 后续 Sales Agent 按钮占位。

验收：

- 负责人能判断这个机会当前在哪个阶段。
- 负责人能看到客户最初提交的问题。

### 7. Conversation 线程组件

展示：

- 客户消息。
- 人工消息。
- Agent 草稿占位。
- 系统消息。

输入：

- 第一阶段支持人工添加 owner message。

消息标签：

- `lead_form`
- `manual`
- `delivery`
- `system`

验收：

- Opportunity 详情页能显示第一条客户消息。
- 人工新增消息后，线程刷新可见。

### 8. Lead detail 串联

当前 Lead inbox 保留。

Lead detail 增加：

- “已生成客户”链接。
- “已生成机会”链接。
- lifecycle 缺失时显示缺失状态。

验收：

- 从老 Lead 工作台能跳到新客户经营管线。

## 端到端验收路径

### Golden Journey 1：Lead 自动进入客户管线

```text
客户提交需求
  -> Lead 创建成功
  -> Customer 创建成功
  -> Contact 创建成功
  -> Conversation 创建成功
  -> Message 创建成功
  -> Opportunity 创建成功
  -> 后台 Opportunity 列表可见
  -> Opportunity 详情可见第一条客户消息
```

### Golden Journey 2：负责人跟进机会

```text
负责人打开 Opportunity 详情
  -> 查看客户信息和客户问题
  -> 修改 next_step
  -> 添加一条 owner message
  -> AuditLog 记录动作
```

### Golden Journey 3：为 Sales Agent 做准备

```text
Opportunity 详情
  -> 能读取 customer
  -> 能读取 conversation
  -> 能读取 messages
  -> 后续 Sales Agent 可基于这些上下文生成回复草稿
```

## 推荐实施顺序

1. 后端接入 Lead API 自动创建 lifecycle。
2. 后端补 Customer / Opportunity / Conversation read API。
3. 前端做最小 Opportunity 列表。
4. 前端做 Opportunity 详情 + Conversation 线程。
5. 后端支持手动 Message 写入。
6. 前端支持人工添加消息。
7. Lead detail 增加客户和机会跳转。
8. 预留 Sales Agent 入口。

## 最小可发布版本

只要以下链路跑通，就可以认为 V1 具备产品价值：

```text
提交 Lead
  -> 后端自动生成客户生命周期对象
  -> 后台能看到 Opportunity 列表
  -> 点进 Opportunity 能看到客户信息和第一条客户消息
```

这时系统已经从“线索收集”迈入“一人公司 Agent OS”的经营底座阶段。
