# TASK：External Connector MVP 产品与开发实现清单

## 背景

ChenForge AI 当前平台化路线是：

```text
P0：Workspace MVP
P1：Event & Notification Center MVP
P2：Service Catalog MVP
P3：Workspace Knowledge Engine MVP
P4：Context Builder 接入 Sales Reply Agent
P5：External Connector MVP
P6：Vector RAG / 文档上传 / pgvector
```

P0 到 P4 已经让系统具备了“经营主体、服务目录、知识库、上下文组装、Agent 回复草稿”的能力。

但当前客户消息主要来自系统内部已有数据或后台手动录入。真实使用时，客户不会先进入 ChenForge AI 后台，他们通常会通过邮箱、飞书、企业微信、微信、官网表单等外部渠道发起沟通。

本任务要完成 P5 的第一步：

> 建立 External Connector 抽象，让外部渠道消息能够标准化进入 Workspace 的 Customer / Contact / Conversation / Message，并触发 Event / Notification。

这一步不是直接完整接入所有第三方平台，也不是做复杂 OAuth。它要先把连接器模型、入站消息标准、联系人匹配、消息入库、事件通知的系统内闭环打通。

## 产品目标

作为一人公司或小团队负责人，我希望客户从邮箱、飞书、企业微信等渠道发来的消息，能够自动进入系统的客户会话，并及时提醒我处理。这样我不需要在多个工具之间来回切换，也不会漏掉客户回复。

目标链路：

```text
External Channel
  -> Connector Webhook
  -> Normalize Inbound Message
  -> Match or Create Contact / Customer
  -> Find or Create Conversation
  -> Create Message
  -> Record Event
  -> Generate Notification
  -> Owner reviews in Admin
  -> Optional Agent follow-up later
```

这一步的关键不是“接入某一个平台”，而是抽象出所有平台共用的入站消息能力。

## 这一步解决什么场景

### 场景 1：客户邮件回复方案

客户通过邮件回复：

```text
我们看了 PoC 方案，想进一步确认报价和交付周期。
```

系统应该：

- 根据发件人邮箱匹配已有 Contact。
- 找到该 Contact 最近的 open Conversation。
- 创建一条 `Message(sender_type=customer, source=external_email)`。
- 记录 `external_message.received` Event。
- 生成站内 Notification，提醒负责人有新客户消息。

### 场景 2：未知联系人从外部渠道咨询

某个新客户从飞书或企业微信发来：

```text
我们想了解你们能不能做 AI 客服系统。
```

系统找不到已有 Contact 时，应该：

- 创建 Customer。
- 创建 Contact。
- 创建 Conversation。
- 创建第一条客户 Message。
- 可选创建 Opportunity，或先只进入待处理 Conversation。
- 记录 Event 和 Notification。

MVP 推荐先创建 Customer / Contact / Conversation / Message，不自动创建 Opportunity。自动创建 Opportunity 留到后续规则化。

### 场景 3：重复 webhook 不应重复入库

第三方平台可能重复投递同一条消息。系统应该基于：

```text
workspace_id + connector_id + external_message_id
```

做到幂等处理。重复请求返回同一条 Message，不创建重复消息和重复通知。

### 场景 4：跨 Workspace 数据不能串

每个 Connector 必须属于一个 Workspace。入站消息只能进入该 Connector 所属 Workspace。

即使不同 Workspace 中存在相同邮箱或相同 external_user_id，也不能跨 Workspace 匹配 Contact 或 Conversation。

### 场景 5：暂时没有真实平台也能开发测试

在真实邮箱、飞书、企业微信接入前，系统需要提供 mock connector webhook。开发和测试可以直接向 mock endpoint 发送标准 payload，验证完整业务闭环。

## MVP 范围

### In Scope

- 新增 `ExternalConnector` 后端模型。
- 支持 connector 类型：
  - `mock`
  - `email`
  - `feishu`
  - `wechat_work`
- 新增 connector 管理 API。
- 新增 mock inbound webhook API。
- 定义 provider-agnostic inbound payload。
- 将入站消息标准化为 `Message`。
- 支持已知 Contact 匹配。
- 支持未知 Contact 创建 Customer / Contact / Conversation。
- 支持基于 `external_message_id` 幂等。
- 入站成功后记录 Event。
- 入站成功后触发 Notification Center。
- 前端新增 `/admin/connectors` 管理页。
- Opportunity / Conversation 中展示外部消息来源。
- 后端测试覆盖模型、API、幂等、Workspace 隔离、通知联动。
- 前端 lint/build 通过。

### Out of Scope

- 不做真实邮箱 IMAP/SMTP 收取。
- 不做飞书 OAuth。
- 不做企业微信 OAuth。
- 不做微信个人号接入。
- 不做双向发送。
- 不做附件解析。
- 不做消息撤回、编辑、已读回执。
- 不做自动创建 Opportunity 的复杂规则。
- 不自动运行 Sales Agent。
- 不做第三方平台签名校验的完整实现。
- 不做后台任务队列。

## 核心概念

### ExternalConnector

表示 Workspace 绑定的一个外部沟通渠道。

```text
ExternalConnector
  id
  workspace_id
  provider
  name
  status
  config_json
  secret_ref
  webhook_token
  last_received_at
  created_at
  updated_at
```

字段说明：

- `provider`：`mock | email | feishu | wechat_work`。
- `status`：`active | paused | disabled`。
- `config_json`：保存非敏感配置，例如邮箱地址、飞书 app 名称、企业微信 agent 名称。
- `secret_ref`：敏感配置引用，不直接存明文 token。
- `webhook_token`：MVP 本地 webhook 鉴权 token。
- `last_received_at`：最近一次成功收到消息的时间。

### Inbound Message Payload

MVP 使用统一入站格式，不直接暴露第三方平台原始 payload 给业务层。

```json
{
  "external_message_id": "mail-001",
  "external_thread_id": "thread-abc",
  "sender": {
    "external_user_id": "user-001",
    "name": "王总",
    "email": "wang@example.com",
    "phone": "13800000000"
  },
  "recipient": {
    "address": "owner@chenforge.ai"
  },
  "body_markdown": "我们想进一步确认报价和交付周期。",
  "occurred_at": "2026-07-09T10:30:00Z",
  "raw_payload": {
    "provider": "mock"
  }
}
```

### Message Source

当前 `Message.source` 已经是字符串字段。MVP 推荐直接使用字符串，不新增 enum 迁移压力。

新增约定：

```text
external_mock
external_email
external_feishu
external_wechat_work
```

### Connector Event

入站成功后记录：

```text
external_message.received
```

Event payload 至少包含：

```json
{
  "connector_id": "...",
  "provider": "email",
  "message_id": "...",
  "conversation_id": "...",
  "customer_id": "...",
  "contact_id": "...",
  "external_message_id": "mail-001"
}
```

### Notification

入站成功后应该生成站内通知：

```text
title: 新客户消息
body: 王总：我们想进一步确认报价和交付周期。
subject_type: message
subject_id: message.id
```

如果现有 Notification Rule 机制需要先配置规则，则本任务要补默认规则或在 inbound service 中显式创建 notification。MVP 推荐复用 `record_event` + 默认规则，保持通知中心的统一入口。

## 后端实现清单

### BE-01：新增 ExternalConnector 模型

文件：

```text
backend/app/models.py
```

新增枚举：

```text
ExternalConnectorProvider
  mock
  email
  feishu
  wechat_work

ExternalConnectorStatus
  active
  paused
  disabled
```

新增模型：

```text
ExternalConnector
```

字段：

```text
id: String(36)
workspace_id: FK workspaces.id, index, non-null
provider: enum, index, non-null
name: String(120), non-null
status: enum, default active, index
config_json: JSON, default {}
secret_ref: String(255), nullable
webhook_token: String(120), nullable, unique or indexed
last_received_at: DateTime, nullable
created_at: DateTime
updated_at: DateTime
```

索引建议：

```text
(workspace_id, provider)
(workspace_id, status)
webhook_token
```

验收：

- `init_db()` 能创建表。
- Connector 必须有 `workspace_id`。
- 默认状态为 `active`。

### BE-02：新增 Schema

文件：

```text
backend/app/schemas.py
```

新增：

```text
ExternalConnectorCreate
ExternalConnectorUpdate
ExternalConnectorOut
InboundMessageSenderIn
InboundMessageRecipientIn
InboundMessageCreateIn
InboundMessageCreateOut
```

约束：

- `provider` 只能是支持类型。
- `name` 必填。
- `external_message_id` 必填。
- `body_markdown` 必填。
- sender 至少有 `email | phone | external_user_id` 之一。

### BE-03：新增 Connector Service

文件：

```text
backend/app/services/external_connectors.py
```

职责：

- 创建 connector。
- 列表查询 connector。
- 更新 connector 状态。
- 根据 `webhook_token` 查找 active connector。
- 生成本地 webhook token。

函数建议：

```text
list_connectors(db, workspace_id)
create_connector(db, workspace_id, payload)
update_connector(db, workspace_id, connector_id, payload)
get_active_connector_by_token(db, token)
```

### BE-04：新增 Inbound Message Service

文件：

```text
backend/app/services/inbound_messages.py
```

核心函数：

```text
process_inbound_message(db, connector, payload) -> dict
```

处理流程：

```text
1. 校验 connector active。
2. 根据 workspace_id + connector_id + external_message_id 查重。
3. 查找 Contact：
   - 优先 email。
   - 其次 phone。
   - 最后 external_user_id，MVP 可存入 Contact.notes_json 或新字段后续再做。
4. 如果找不到 Contact：
   - 创建 Customer。
   - 创建 Contact。
   - 创建 Conversation。
5. 如果找到 Contact：
   - 找到该 Customer 最近 open Conversation。
   - 找不到则创建 Conversation。
6. 创建 Message：
   - sender_type = customer
   - sender_label = sender.name
   - body_markdown = payload.body_markdown
   - source = external_{provider}
   - external_message_id = payload.external_message_id
7. 更新 connector.last_received_at。
8. 记录 Event。
9. 触发 Notification。
10. 返回 message / customer / contact / conversation。
```

幂等规则：

```text
workspace_id + connector_id + external_message_id
```

当前 `Message` 没有 `connector_id` 字段。MVP 有两种选择：

方案 A：

- 新增 `Message.external_connector_id` 字段。
- 幂等查询精确。

方案 B：

- 暂不加字段。
- 通过 `workspace_id + source + external_message_id` 幂等。

推荐方案 A。原因是多个 email connector 或多个飞书 connector 时，`source + external_message_id` 可能冲突。

### BE-05：扩展 Message 模型

文件：

```text
backend/app/models.py
```

为 `Message` 新增：

```text
external_connector_id: FK external_connectors.id, nullable, index
external_thread_id: String(255), nullable, index
raw_payload_json: JSON, default {}
```

说明：

- `external_message_id` 已存在，继续复用。
- `external_thread_id` 用于后续对齐邮件 thread、飞书 open_chat_id、企业微信群 thread。
- `raw_payload_json` 用于审计和后续排查，但前端默认不展示。

### BE-06：新增 API Router

文件：

```text
backend/app/api/connectors.py
```

接口：

```text
GET /api/v1/admin/connectors
POST /api/v1/admin/connectors
PATCH /api/v1/admin/connectors/{connector_id}
POST /api/v1/connectors/{webhook_token}/inbound
```

返回：

- 管理接口使用当前默认 Workspace。
- inbound webhook 通过 token 识别 connector 和 Workspace。
- 成功返回 `InboundMessageCreateOut`。

错误：

```text
404 connector not found
409 duplicate message, return existing message payload
422 invalid sender
422 connector paused or disabled
```

幂等重复时也可以返回 `200`，并带：

```json
{
  "deduplicated": true
}
```

推荐重复请求返回 `200`，方便第三方 webhook 不反复重试。

### BE-07：接入 main.py

文件：

```text
backend/app/main.py
```

注册：

```text
from app.api.connectors import router as connectors_router
app.include_router(connectors_router, prefix="/api/v1")
```

### BE-08：通知联动

文件：

```text
backend/app/services/events.py
backend/app/services/inbound_messages.py
```

要求：

- 入站消息创建后记录 `external_message.received`。
- 生成 Notification。
- Notification subject 指向 Message。
- Notification payload 包含 conversation_id/customer_id/contact_id。

如果现有 `record_event` 需要通知规则才能生成通知，本任务需要确保默认规则存在：

```text
event_type = external_message.received
channel = in_app
enabled = true
```

### BE-09：后端测试

新增文件：

```text
backend/tests/test_external_connectors.py
```

测试用例：

1. 创建 connector 成功。
2. 列表只返回当前 Workspace connector。
3. paused connector 拒绝 inbound。
4. active connector 接收 inbound 后创建 Message。
5. 已知 email 匹配已有 Contact。
6. 未知 sender 创建 Customer / Contact / Conversation。
7. 重复 external_message_id 不重复创建 Message。
8. 相同 external_message_id 不同 connector 可以分别入库。
9. 跨 Workspace 不匹配 Contact。
10. 入站成功记录 Event。
11. 入站成功生成 Notification。
12. Message source 正确写为 `external_mock` / `external_email`。
13. raw_payload_json 保存原始 payload。

运行：

```text
cd backend && .venv/bin/python -m pytest tests/test_external_connectors.py -q
cd backend && .venv/bin/python -m pytest -q
```

## 前端实现清单

### FE-01：扩展 admin-api

文件：

```text
frontend/src/lib/admin-api.ts
```

新增类型：

```text
ExternalConnectorProvider
ExternalConnectorStatus
ExternalConnectorOut
ExternalConnectorCreate
ExternalConnectorUpdate
InboundMessageCreate
InboundMessageOut
```

新增 API：

```text
fetchConnectors()
createConnector(payload)
updateConnector(connectorId, payload)
sendMockInboundMessage(webhookToken, payload)
```

### FE-02：AdminShell 增加 Connectors 导航

文件：

```text
frontend/src/components/admin/admin-shell.tsx
```

新增导航：

```text
/admin/connectors
Connectors
```

### FE-03：新增 Connectors 页面

文件：

```text
frontend/src/app/admin/connectors/page.tsx
```

页面目标：

- 展示当前 Workspace connector 列表。
- 支持创建 mock connector。
- 展示 provider、status、last_received_at。
- 展示本地 webhook URL。
- 支持 pause/resume。
- 提供 mock inbound 测试表单。

页面结构：

```text
Header
  title: External Connectors
  action: New mock connector

Connector list
  provider badge
  name
  status
  last received
  webhook url
  pause/resume

Mock inbound tester
  connector selector
  sender name
  sender email
  external message id
  body
  Send test inbound
```

### FE-04：Conversation Thread 展示外部来源

文件：

```text
frontend/src/components/admin/conversation-thread.tsx
```

要求：

- 如果 `message.source` 以 `external_` 开头，展示来源 badge：

```text
Email
Feishu
WeCom
Mock
```

- 不展示 raw_payload。
- 外部消息和人工消息在视觉上可区分。

### FE-05：Opportunity Detail 自动体现新消息

文件：

```text
frontend/src/app/admin/opportunities/[opportunityId]/page.tsx
```

要求：

- 如果外部消息进入了当前 Opportunity 关联的 Conversation，详情页刷新后能看到。
- 不需要实时 websocket。
- 不需要自动触发 Agent。

### FE-06：前端验证

运行：

```text
cd frontend && npm run lint
cd frontend && npm run build
```

注意：

- 当前本地沙箱中 Turbopack build 可能因为创建进程/绑定端口被拦截。
- 如果普通沙箱失败但报错是权限类，需要授权环境重跑确认真实 build。

## API 设计

### 创建 Connector

```http
POST /api/v1/admin/connectors
```

Request:

```json
{
  "provider": "mock",
  "name": "本地测试入口",
  "config_json": {
    "description": "用于开发测试的 mock inbound connector"
  }
}
```

Response:

```json
{
  "id": "...",
  "workspace_id": "...",
  "provider": "mock",
  "name": "本地测试入口",
  "status": "active",
  "config_json": {
    "description": "用于开发测试的 mock inbound connector"
  },
  "webhook_token": "...",
  "webhook_path": "/api/v1/connectors/{webhook_token}/inbound",
  "last_received_at": null,
  "created_at": "...",
  "updated_at": "..."
}
```

### 入站消息

```http
POST /api/v1/connectors/{webhook_token}/inbound
```

Request:

```json
{
  "external_message_id": "mock-001",
  "external_thread_id": "thread-001",
  "sender": {
    "external_user_id": "mock-user-001",
    "name": "王总",
    "email": "wang@example.com"
  },
  "body_markdown": "我们想确认 PoC 报价和交付周期。",
  "raw_payload": {
    "provider": "mock"
  }
}
```

Response:

```json
{
  "deduplicated": false,
  "connector_id": "...",
  "customer": {...},
  "contact": {...},
  "conversation": {...},
  "message": {...},
  "event_id": "...",
  "notification_id": "..."
}
```

## 数据流

```text
Admin creates mock connector
  -> connector.webhook_token generated

External system posts inbound message
  -> API finds connector by token
  -> inbound service normalizes payload
  -> idempotency check
  -> match/create Customer + Contact
  -> find/create Conversation
  -> create Message
  -> record Event
  -> create Notification
  -> return payload

Owner opens Admin
  -> Notifications page shows new customer message
  -> Opportunity / Conversation page shows external message
```

## 错误处理

### Connector 不存在

返回：

```text
404 connector not found
```

### Connector 非 active

返回：

```text
422 connector is not active
```

不创建 Message，不记录业务 Event。

### sender 无可识别身份

返回：

```text
422 sender must include email, phone, or external_user_id
```

### 重复消息

返回：

```text
200 deduplicated = true
```

返回已有 Message，不创建重复 Event 和 Notification。

### 创建中途失败

整个 inbound 处理必须由 API transaction 控制。失败时不应留下半截 Customer / Contact / Message。

## 安全与边界

### Workspace 隔离

- Connector 属于 Workspace。
- Inbound 只能写入 Connector 所属 Workspace。
- Contact 查找必须带 `workspace_id`。
- Conversation 查找必须带 `workspace_id`。
- Message 创建必须带 `workspace_id`。

### Webhook Token

MVP 使用随机 token 鉴权：

```text
/api/v1/connectors/{webhook_token}/inbound
```

生产环境后续需要：

- provider 签名校验。
- token rotate。
- IP allowlist。
- rate limit。

这些不在本任务内完成。

### Raw Payload

`raw_payload_json` 仅用于审计和排查。前端不默认展示，避免误暴露敏感信息。

## 前后端验收标准

### 后端验收

- 能创建 active mock connector。
- 能通过 webhook token 接收入站消息。
- 已知 email 能匹配已有 Contact。
- 未知 sender 能创建 Customer / Contact / Conversation / Message。
- 重复 external_message_id 不重复创建 Message。
- 不同 connector 的相同 external_message_id 不冲突。
- paused / disabled connector 拒绝 inbound。
- 入站消息 source 正确。
- 入站消息 raw_payload_json 正确保存。
- 入站成功记录 `external_message.received` Event。
- 入站成功生成 Notification。
- 跨 Workspace 不会匹配或写入错误数据。
- 后端专项测试通过。
- 后端全量测试通过。

### 前端验收

- `/admin/connectors` 可访问。
- 页面能展示 connector 列表。
- 可以创建 mock connector。
- 可以复制或查看 webhook URL。
- 可以发送 mock inbound 测试消息。
- 成功后能看到 message/customer/conversation 结果提示。
- Conversation Thread 能展示外部来源 badge。
- Notifications 页面能看到新客户消息提醒。
- `npm run lint` 通过。
- `npm run build` 通过。

## 推荐实现顺序

### Step 1：后端模型和 schema

先实现 `ExternalConnector` 和 `Message.external_connector_id/external_thread_id/raw_payload_json`。

### Step 2：connector service 和 API

实现 connector 列表、创建、更新。

### Step 3：inbound service

实现标准 payload 入库、Contact 匹配、Conversation 创建、Message 创建。

### Step 4：幂等和 Workspace 隔离测试

先用后端专项测试把入站闭环锁住。

### Step 5：Event + Notification

把 `external_message.received` 接入通知中心。

### Step 6：前端 Connectors 页面

实现 `/admin/connectors` 和 mock inbound tester。

### Step 7：Conversation 来源展示

在 Conversation Thread 里展示 external source badge。

### Step 8：全量验证

运行：

```text
backend tests/test_external_connectors.py
backend full pytest
frontend npm run lint
frontend npm run build
```

## 不建议现在做的事

- 不建议一上来接真实飞书 OAuth。
- 不建议一上来接企业微信 OAuth。
- 不建议直接接个人微信。
- 不建议在 Connector MVP 中引入任务队列。
- 不建议自动触发 Sales Agent。
- 不建议自动创建 Opportunity。
- 不建议把第三方 raw payload 直接传给前端。
- 不建议为每个 provider 写完全不同的业务逻辑。

## 完成定义

当以下条件全部满足时，本任务完成：

```text
1. Workspace 可以创建 ExternalConnector。
2. ExternalConnector 有 active / paused / disabled 状态。
3. mock inbound webhook 可以接收标准消息。
4. 入站消息能匹配已有 Contact。
5. 入站消息能为未知 sender 创建 Customer / Contact / Conversation。
6. 入站消息能创建 Message。
7. Message 记录 external_connector_id、external_thread_id、external_message_id、raw_payload_json。
8. 重复 webhook 不重复创建 Message。
9. 跨 Workspace 不泄漏数据。
10. 入站成功记录 Event。
11. 入站成功生成 Notification。
12. 前端 `/admin/connectors` 可管理 mock connector。
13. 前端能发送 mock inbound 测试消息。
14. Conversation Thread 能展示外部来源。
15. 后端专项测试通过。
16. 后端全量测试通过。
17. 前端 lint/build 通过。
```

