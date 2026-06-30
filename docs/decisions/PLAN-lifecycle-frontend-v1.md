# PLAN：客户生命周期前端 UI V1

## 目标

为一人公司 Agent OS 的客户生命周期功能设计一版可直接实现的后台 UI。

本阶段前端要让负责人完成三件事：

```text
看见客户管线
  -> 判断哪个 Opportunity 需要跟进
  -> 打开 Opportunity 详情，查看客户信息和第一条客户消息
```

## 设计方向

### 视觉基调

沿用公开官网的“精密 AI 工坊”语言，但后台要更克制、更高密度：

- 背景继续使用 `paper` 和细网格，保留工坊感。
- 信息容器使用低对比边框，不做大面积营销卡片。
- 强调铜色 `copper` 作为行动和风险提示色。
- 蓝图色 `blueprint` 用于机会、管线、系统状态。
- 苔绿色 `moss` 用于客户和正向状态。
- 所有业务面板圆角不超过 8px。
- 后台不使用大 hero、不使用夸张渐变、不使用泛 AI 光效。

### 产品气质

后台是一个“一人公司经营驾驶舱”，不是 CRM 大系统。

关键词：

- 清楚。
- 可扫读。
- 可追责。
- 有下一步动作。
- 能让负责人一眼知道今天该跟进谁。

## 路由结构

第一阶段新增后台路由：

```text
/admin
  Company Cockpit 总览

/admin/customers
  客户列表

/admin/customers/[customerId]
  客户详情

/admin/opportunities
  机会列表

/admin/opportunities/[opportunityId]
  机会详情 + Conversation 线程

/admin/leads/[leadId]
  现有 Lead 详情增强：增加客户/机会跳转
```

如果当前项目还没有后台路由壳，先实现：

```text
/admin/opportunities
/admin/opportunities/[opportunityId]
```

这两页是最小可用版本。

## 全局后台布局

### Admin Shell

布局：

```text
┌────────────────────────────────────────────────────┐
│ Top Bar: ChenForge AI / 当前日期 / Owner 状态       │
├───────────────┬────────────────────────────────────┤
│ Side Nav      │ Page Content                        │
│               │                                    │
│ Cockpit       │                                    │
│ Leads         │                                    │
│ Customers     │                                    │
│ Opportunities │                                    │
│ Decisions     │                                    │
└───────────────┴────────────────────────────────────┘
```

桌面：

- 左侧固定导航宽度 `220px`。
- 主内容最大宽度不超过 `1440px`。
- 页面内使用 12 栏或 `grid-template-columns`。

移动端：

- 左侧导航折叠成顶部 tab。
- 表格降级为列表行。
- Opportunity 详情中的右侧栏下移。

### Top Bar

内容：

- 左侧：`ChenForge AI / Company Cockpit`
- 中间：当前视图标题。
- 右侧：`Admin`、今天待跟进数、刷新按钮。

控件：

- 刷新按钮使用图标。
- 不用大块 CTA。

### Side Nav

导航项：

- Cockpit
- Leads
- Customers
- Opportunities
- Decisions

每项显示：

- 图标。
- 文本。
- 可选计数 badge，例如 `Opportunities 12`。

当前项：

- 左侧 3px 铜色竖线。
- 背景为 `rgba(184, 95, 54, 0.08)`。

## 页面 1：Company Cockpit

### 页面目标

负责人打开后台后，能立刻看到：

- 今天新增了多少客户/机会。
- 哪些机会需要跟进。
- 最近客户说了什么。
- 哪些 Agent 输出待审批，后续接入。

### 信息架构

```text
Page Header
  标题：Company Cockpit
  副标题：今天需要推进的客户、机会和审批动作

Metric Strip
  客户总数
  Qualified 机会
  待跟进机会
  待审批草稿

Main Grid
  左：Opportunity Focus List
  右：Recent Customer Messages

Lower Band
  Pipeline Snapshot
  Audit Feed 占位
```

### 组件

#### Metric Strip

四个紧凑指标块：

- `Customers`
- `Qualified`
- `Needs Follow-up`
- `Waiting Approval`

字段：

- 数字。
- 环比或今日新增，第一版可显示 `Today +N`。
- 小图标。

#### Opportunity Focus List

显示 5-8 个最需要跟进的机会。

字段：

- 公司名。
- 机会标题。
- 阶段。
- 下一步动作。
- 最近更新时间。

交互：

- 点击整行进入 Opportunity 详情。
- stage 用小型 badge。
- next_step 为空时显示 `未设置下一步`，并用铜色提示。

#### Recent Customer Messages

显示最近消息。

字段：

- 公司名。
- 发送人。
- 消息摘要。
- 来源 `lead_form/manual/delivery`。
- 时间。

### 空态

无机会时：

```text
暂无机会。新客户提交需求后，系统会自动生成客户、对话和机会。
```

按钮：

- `查看 Leads`

## 页面 2：Customers 列表

### 页面目标

让负责人查找客户，并判断客户是否已经进入机会管线。

### 布局

```text
Header
  Customers
  Search input

Customer Table
  Company
  Primary Contact
  Industry
  Company Size
  Opportunities
  Updated
```

### 表格行

字段：

- 公司名，主文字。
- owner_email，次文字。
- 主联系人姓名和邮箱。
- 行业。
- 公司规模。
- 机会数量。
- 更新时间。

交互：

- 点击公司名进入客户详情。
- 搜索框支持公司名和邮箱。

### 移动端

每个客户显示为列表项：

```text
公司名
联系人 / 行业
机会数量 / 更新时间
```

## 页面 3：Customer 详情

### 页面目标

展示一个客户的上下文：是谁、从哪个 Lead 来、有哪些联系人和机会。

### 布局

```text
Header
  公司名
  owner_email

Two Column
  左：Customer Profile + Contacts
  右：Opportunities + Recent Conversations
```

### Customer Profile

字段：

- 公司名。
- owner_email。
- 行业。
- 公司规模。
- source_lead_id。
- 创建时间。

### Contacts

字段：

- 姓名。
- email。
- contact_method。
- 是否 primary。

### Opportunities

字段：

- title。
- stage。
- desired_outcome。
- next_step。

交互：

- 点击进入 Opportunity 详情。

### Recent Conversations

字段：

- title。
- channel。
- status。
- 更新时间。

## 页面 4：Opportunities 列表

### 页面目标

这是 V1 最重要页面。负责人用它管理所有潜在项目机会。

### 布局

```text
Header
  Opportunities
  Search input
  Stage segmented control

Table/List
  Opportunity
  Company
  Stage
  Desired Outcome
  Next Step
  Budget
  Updated
```

### Stage 筛选

使用 segmented control：

- All
- Lead
- Qualified
- Proposal
- Negotiation
- Won
- Lost
- Archived

选中项：

- 背景 `blueprint`。
- 文本白色。

### Opportunity 行

字段：

- title，主文字。
- company_name，次文字。
- stage badge。
- desired_outcome。
- next_step。
- budget_range。
- 更新时间。

行状态：

- `next_step` 为空：铜色左边线。
- `stage=qualified`：蓝图色 badge。
- `stage=proposal`：铜色 badge。
- `stage=won`：苔绿色 badge。
- `stage=lost/archived`：低对比灰色 badge。

交互：

- 点击行进入详情。
- 搜索支持机会标题和公司名。

## 页面 5：Opportunity 详情

### 页面目标

让负责人看见完整上下文，并完成下一步跟进。

### 桌面布局

```text
Header
  机会标题
  Stage selector
  Updated time

Main Grid
  左 2/3：Conversation Thread
  右 1/3：Opportunity Inspector
```

### Header

字段：

- title。
- company name。
- stage selector。
- next_step 摘要。

动作：

- 保存阶段/下一步。
- 后续预留：`Run Sales Agent`。

### Opportunity Inspector

分组：

1. Customer
   - 公司名。
   - owner_email。
   - industry。
   - company_size。

2. Contact
   - 姓名。
   - email。
   - contact_method。

3. Opportunity
   - desired_outcome。
   - budget_range。
   - estimated_value。
   - probability。
   - problem_summary。

4. Next Step
   - 可编辑 textarea。
   - 保存按钮。

### Conversation Thread

消息类型：

- customer：左侧，边框 `blueprint`。
- owner：右侧，边框 `moss`。
- agent：左侧，虚线边框，带 `Draft` 标记。
- system：居中小字。

每条消息显示：

- sender_label。
- sender_type。
- source。
- created_at。
- body_markdown。

### Message Composer

位置：

- Conversation Thread 底部。

字段：

- textarea：输入人工回复或内部记录。
- sender_type 固定默认 `owner`。
- source 默认 `manual`。

按钮：

- `Add Message`

第一版说明：

- 这个按钮只写入消息线程，不代表已经发送客户。
- 后续对客发送必须走 DeliveryJob。

### 详情页空态

如果没有消息：

```text
暂无消息。客户提交需求后，第一条问题会自动进入对话线程。
```

如果没有 next_step：

```text
还没有下一步动作。建议先补一条负责人可执行的跟进动作。
```

## 页面 6：Lead Detail 串联增强

现有 Lead 详情页增加一个 `Lifecycle` 区块。

### 区块内容

如果已生成：

```text
Customer: 陈记连锁门店 [打开]
Opportunity: 企业知识库 / RAG 问答 PoC [打开]
Conversation: 首次咨询 [打开]
```

如果缺失：

```text
尚未生成客户生命周期对象
```

按钮：

- 第一版可以不提供手动生成按钮。
- 如果提供，必须调用后端 fail-closed 服务。

## API Client 设计

建议文件：

```text
frontend/src/lib/api.ts
frontend/src/lib/types.ts
```

### types.ts

需要定义：

- `Customer`
- `Contact`
- `Conversation`
- `Message`
- `Opportunity`
- `CustomerListItem`
- `OpportunityListItem`
- `PaginatedResponse<T>`

### api.ts

函数：

- `fetchCustomers(params)`
- `fetchCustomerDetail(customerId)`
- `fetchOpportunities(params)`
- `fetchOpportunityDetail(opportunityId)`
- `updateOpportunity(opportunityId, payload)`
- `fetchConversationMessages(conversationId)`
- `createConversationMessage(conversationId, payload)`

错误处理：

- 统一解析 `{detail}` 或标准错误格式。
- 非 2xx 抛出 `ApiError`。

## 组件拆分

建议组件：

```text
frontend/src/components/admin/admin-shell.tsx
frontend/src/components/admin/admin-nav.tsx
frontend/src/components/admin/metric-strip.tsx
frontend/src/components/admin/stage-badge.tsx
frontend/src/components/admin/opportunity-table.tsx
frontend/src/components/admin/customer-table.tsx
frontend/src/components/admin/conversation-thread.tsx
frontend/src/components/admin/message-composer.tsx
frontend/src/components/admin/opportunity-inspector.tsx
frontend/src/components/admin/empty-state.tsx
```

## 状态设计

每个页面必须有：

- loading。
- error。
- empty。
- loaded。

### Loading

使用稳定高度 skeleton，不让布局跳动。

### Error

显示：

- 错误摘要。
- retry 按钮。

### Empty

不做营销式说明，只提示下一步动作。

## 第一阶段验收

### 验收路径 A：机会列表

```text
打开 /admin/opportunities
  -> 能看到 Opportunity 列表
  -> 能按 stage 筛选
  -> 能按公司名搜索
  -> 点击行进入详情
```

### 验收路径 B：机会详情

```text
打开 Opportunity 详情
  -> 能看到客户信息
  -> 能看到 primary contact
  -> 能看到第一条客户消息
  -> 能修改 stage 和 next_step
```

### 验收路径 C：人工消息

```text
在 Opportunity 详情输入消息
  -> 点击 Add Message
  -> 消息出现在 Conversation Thread
  -> 刷新后仍存在
```

## 推荐实现顺序

1. `types.ts` 和 `api.ts`。
2. `AdminShell` 和基础后台样式。
3. `/admin/opportunities` 列表页。
4. `/admin/opportunities/[opportunityId]` 详情页。
5. `ConversationThread` 和 `MessageComposer`。
6. `/admin/customers` 列表页。
7. `/admin/customers/[customerId]` 详情页。
8. `/admin` Cockpit 总览。
9. Lead detail 增加生命周期跳转。

## 最小可实现 UI

如果只做一天内可见结果，优先实现：

```text
/admin/opportunities
/admin/opportunities/[opportunityId]
ConversationThread
MessageComposer
```

这四块完成后，负责人已经可以从机会列表进入客户上下文，并添加人工跟进消息。
