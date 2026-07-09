# TASK：External Connector Contact Identity Matching 产品与开发实现清单

## 背景

`External Connector MVP` 已经完成主闭环：

```text
External Connector
  -> Inbound Webhook
  -> Customer / Contact / Conversation / Message
  -> Event
  -> Notification
  -> /admin/connectors
```

当前实现中，入站消息匹配已有 Contact 的逻辑是：

```text
只按 sender.email 匹配 Contact.email
```

`phone` 和 `external_user_id` 虽然在 `InboundMessageSenderIn` 中允许传入，但当前只被保存在 `raw_payload_json` 中，没有参与联系人匹配。

这对邮箱渠道够用，但对飞书、企业微信、微信等非邮箱渠道不够稳。很多平台消息并不一定能拿到客户邮箱，但通常能拿到：

```text
external_user_id
phone
union_id / open_id / user_id
```

本任务要完成 External Connector 的身份匹配补强：

> 将 Contact 匹配从 email 扩展到 phone / external_user_id，让非邮箱渠道也能稳定归档到同一个客户和会话。

## 产品目标

作为系统使用者，我希望同一个客户即使通过不同渠道发消息，系统也能尽量识别为同一个 Contact，而不是每次都创建一个新客户。

完成后，以下场景应该成立：

```text
客户第一次通过官网留邮箱
客户第二次通过企业微信发消息，只带 external_user_id 或 phone
系统仍能匹配到已有 Contact
消息进入同一个 Customer / Conversation
负责人只看到连续客户上下文，而不是多个重复客户
```

这一步不是做复杂的客户主数据合并，也不是做跨 Workspace 身份图谱。它只补齐当前 External Connector 入站消息的确定性匹配能力。

## 这一步解决什么场景

### 场景 1：飞书只提供 external_user_id

飞书 webhook 入站 payload：

```json
{
  "external_message_id": "feishu-msg-001",
  "sender": {
    "external_user_id": "ou_demo_001",
    "name": "王总"
  },
  "body_markdown": "我们想继续聊 PoC 报价。"
}
```

如果当前 Workspace 中已有 Contact：

```text
external_user_id = ou_demo_001
```

系统应该匹配该 Contact，并把消息写入其 Customer 最近 open Conversation。

### 场景 2：企业微信只提供手机号

企业微信或人工同步入站 payload：

```json
{
  "external_message_id": "wecom-msg-001",
  "sender": {
    "phone": "13800000000",
    "name": "李总"
  },
  "body_markdown": "合同条款我们有两个问题。"
}
```

如果已有 Contact：

```text
phone = 13800000000
```

系统应该匹配该 Contact。

### 场景 3：同时提供 email / phone / external_user_id

当 payload 同时提供多个身份字段时，系统需要稳定的匹配优先级，避免同一条消息被错误归档。

推荐优先级：

```text
external_user_id + provider
  -> email
  -> phone
  -> create new Contact
```

原因：

- `external_user_id` 在同一个 provider 内通常是最稳定的渠道身份。
- email 是跨渠道常见身份，但可能为空。
- phone 可能格式不统一，需要标准化。

### 场景 4：跨 Workspace 不串数据

即使两个 Workspace 中存在相同 phone 或 external_user_id，也只能匹配当前 Connector 所属 Workspace 的 Contact。

## MVP 范围

### In Scope

- 为 Contact 增加结构化身份字段。
- Inbound Message 按 `external_user_id / email / phone` 匹配 Contact。
- 新建 Contact 时保存 `phone / external_user_id / external_provider`。
- 保持 Workspace 隔离。
- 保持幂等逻辑不变。
- 增加后端测试覆盖 phone / external_user_id 匹配。
- 更新 External Connector 相关文档中的当前限制。

### Out of Scope

- 不做跨 Workspace 身份合并。
- 不做多个 Contact 自动 merge。
- 不做复杂模糊匹配。
- 不做通讯录导入。
- 不接真实飞书 OAuth。
- 不接真实企业微信 OAuth。
- 不做 union_id/open_id 多平台身份图谱。
- 不做前端 Contact 编辑页。

## 设计决策

### 决策 1：Contact 增加结构化字段

当前 Contact 模型：

```text
email
contact_method
```

不足以表达平台身份。只把外部身份放进 `raw_payload_json` 会导致下次消息无法直接匹配。

推荐新增字段：

```text
phone: String(50), nullable, index
external_provider: String(50), nullable, index
external_user_id: String(255), nullable, index
```

说明：

- `phone` 存标准化后的手机号。
- `external_provider` 存 `mock / email / feishu / wechat_work`。
- `external_user_id` 存第三方平台用户 ID。

### 决策 2：external_user_id 匹配必须带 provider

不同平台的 user id 可能重名或格式相似。匹配时必须同时使用：

```text
workspace_id + external_provider + external_user_id
```

不能只用 `external_user_id`。

### 决策 3：phone 做轻量标准化

MVP 不引入复杂手机号库。先做轻量标准化：

```text
去除空格、横线、括号
保留数字和前导 +
```

示例：

```text
"138 0000 0000" -> "13800000000"
"+86 138-0000-0000" -> "+8613800000000"
```

暂不做国家区号推断。

### 决策 4：匹配优先级固定

匹配顺序：

```text
1. workspace_id + external_provider + external_user_id
2. workspace_id + email
3. workspace_id + normalized phone
4. create new Customer / Contact / Conversation
```

如果同一个 payload 同时命中不同 Contact，MVP 采用优先级最高者，不自动合并。

## 后端实现清单

### BE-01：扩展 Contact 模型

文件：

```text
backend/app/models.py
```

在 `Contact` 增加字段：

```text
phone: Mapped[str | None] = mapped_column(String(50), index=True)
external_provider: Mapped[str | None] = mapped_column(String(50), index=True)
external_user_id: Mapped[str | None] = mapped_column(String(255), index=True)
```

验收：

- `init_db()` 能创建新字段。
- 旧测试不受影响。

### BE-02：扩展 Contact 输出 Schema

文件：

```text
backend/app/schemas.py
```

更新相关 Contact 输出：

```text
ContactOut
Cockpit contact/customer payload
InboundMessageCreateOut.contact
```

要求至少能在 inbound API 返回中看到：

```json
{
  "id": "...",
  "name": "王总",
  "email": null,
  "phone": "13800000000",
  "external_provider": "wechat_work",
  "external_user_id": "userid_demo_001"
}
```

### BE-03：新增 phone 标准化 helper

文件：

```text
backend/app/services/inbound_messages.py
```

新增函数：

```text
normalize_phone(value: str | None) -> str | None
```

规则：

- 空值返回 `None`。
- 去除空格、横线、括号。
- 仅保留数字和开头的 `+`。
- 标准化后为空则返回 `None`。

### BE-04：抽取 Contact 匹配函数

文件：

```text
backend/app/services/inbound_messages.py
```

新增函数：

```text
find_contact_for_inbound_sender(db, workspace_id, provider, sender) -> Contact | None
```

匹配顺序：

```text
external_provider + external_user_id
email
phone
```

所有查询必须带：

```text
Contact.workspace_id == workspace_id
```

### BE-05：新建 Contact 时保存身份字段

文件：

```text
backend/app/services/inbound_messages.py
```

当找不到 Contact 并创建新 Contact 时，保存：

```text
email = sender.email
phone = normalize_phone(sender.phone)
external_provider = connector.provider
external_user_id = sender.external_user_id
contact_method = email or phone or external_user_id
```

Customer 的 `owner_email` 当前是非空字段。若没有 email，继续使用空字符串，保持现有行为不变。

### BE-06：已有 Contact 回填缺失身份

当通过 email 匹配到已有 Contact，但 payload 同时提供 phone 或 external_user_id，且 Contact 对应字段为空时，可以回填：

```text
phone
external_provider
external_user_id
```

规则：

- 只填空字段。
- 不覆盖已有值。
- 如果已有 external_provider/external_user_id 与 payload 不同，不做覆盖，不做 merge。

这能让客户先通过邮箱进入系统，后续再通过飞书/企微进入时逐步补齐身份。

### BE-07：API 返回 contact 身份字段

文件：

```text
backend/app/api/connectors.py
```

更新 `_contact_dict`：

```text
phone
external_provider
external_user_id
```

### BE-08：后端测试

文件：

```text
backend/tests/test_external_connectors.py
```

新增测试：

1. `test_external_user_id_matches_existing_contact`
2. `test_external_user_id_is_provider_scoped`
3. `test_phone_matches_existing_contact`
4. `test_phone_normalized_before_matching`
5. `test_new_contact_saves_phone_and_external_user_id`
6. `test_email_match_backfills_missing_phone_and_external_identity`
7. `test_phone_match_is_workspace_scoped`
8. `test_external_user_id_match_is_workspace_scoped`

运行：

```text
cd backend && .venv/bin/python -m pytest tests/test_external_connectors.py -q
cd backend && .venv/bin/python -m pytest -q
```

## 前端实现清单

### FE-01：更新 admin-api 类型

文件：

```text
frontend/src/lib/admin-api.ts
```

更新 `InboundMessageResult.contact`：

```text
phone?: string | null
external_provider?: string | null
external_user_id?: string | null
```

### FE-02：Mock inbound 测试表单增加 phone/external_user_id

文件：

```text
frontend/src/app/admin/connectors/page.tsx
```

增加输入项：

```text
sender.phone
sender.external_user_id
```

用途：

- 开发时可直接模拟飞书/企业微信无邮箱入站。
- 验证 phone/external_user_id 是否能匹配已有 Contact。

### FE-03：测试结果展示更多身份信息

文件：

```text
frontend/src/app/admin/connectors/page.tsx
```

入站成功后展示：

```text
客户名
Contact email
Contact phone
external_provider / external_user_id
是否 deduplicated
```

### FE-04：前端验证

运行：

```text
cd frontend && npm run lint
cd frontend && npm run build
```

## 匹配流程

```text
Inbound payload
  -> connector determines workspace_id/provider
  -> normalize sender.phone
  -> match Contact by workspace + provider + external_user_id
  -> if none, match Contact by workspace + email
  -> if none, match Contact by workspace + phone
  -> if found, optionally backfill empty identity fields
  -> if none, create Customer + Contact with all available identities
  -> find/create Conversation
  -> create Message
```

## 验收标准

### 后端验收

- 通过 `external_user_id + provider` 能匹配已有 Contact。
- 相同 `external_user_id` 不同 provider 不误匹配。
- 通过 phone 能匹配已有 Contact。
- phone 标准化后能匹配。
- 新建 Contact 会保存 phone / external_provider / external_user_id。
- email 命中已有 Contact 时，会回填空的 phone / external identity。
- phone / external_user_id 匹配都严格限制在当前 Workspace。
- 原有 email 匹配行为不变。
- 原有幂等行为不变。
- 原有 Event / Notification 行为不变。
- `tests/test_external_connectors.py` 通过。
- 后端全量测试通过。

### 前端验收

- `/admin/connectors` mock inbound 表单能填写 phone。
- `/admin/connectors` mock inbound 表单能填写 external_user_id。
- 入站测试结果能展示 Contact 的 phone / external identity。
- `npm run lint` 通过。
- `npm run build` 通过。

## 不建议现在做的事

- 不做 Contact merge UI。
- 不做客户去重后台任务。
- 不做跨 Workspace 身份共享。
- 不做复杂手机号国家区号推断。
- 不做 provider OAuth。
- 不做真实飞书/企微通讯录同步。

## 完成定义

当以下条件全部满足时，本任务完成：

```text
1. Contact 模型有 phone / external_provider / external_user_id。
2. Inbound sender.external_user_id 可匹配已有 Contact。
3. Inbound sender.phone 可匹配已有 Contact。
4. 匹配逻辑严格 Workspace scoped。
5. external_user_id 匹配严格 provider scoped。
6. 新建 Contact 保存可用身份字段。
7. email 命中时可回填空身份字段。
8. External Connector 原有 15 个测试继续通过。
9. 新增身份匹配测试通过。
10. 后端全量测试通过。
11. 前端 lint/build 通过。
```
