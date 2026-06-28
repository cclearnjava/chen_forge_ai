# ADR-005：Auth、Delivery Center、Notification 与附件架构

## 状态

Accepted

## 背景

ChenForge AI 的新 spec 从「单向线索收集」升级为「双向交付系统」。新增了四个跨模块能力：邮箱验证码登录、客户需求附件上传、对客发送中心、内部通知提醒。这些模块之间有隐式的数据流和契约依赖，必须在编码前冻结架构决策。

## 决策

### 1. Auth 方案：JWT

使用 JWT (access + refresh token)，不引入服务端 session store。

理由：
- SQLite 存储 session 会增加数据库写入压力，且后续迁移到无状态部署时会成为障碍。
- JWT 的 access token 短期有效（15 分钟），refresh token 长期有效（7 天），用 `refresh_token_used` 字段支持服务端失效。

MVP 实现：
- `POST /api/v1/auth/email/start`：发送验证码。
- `POST /api/v1/auth/email/verify`：校验验证码，返回 JWT pair。
- `POST /api/v1/auth/refresh`：刷新 access token。
- 验证码 10 分钟过期，5 分钟内不可重发，同邮箱每天最多 5 次。

### 2. 邮件 provider：Resend

使用 Resend API 发送邮件。

理由：
- 免费额度（100 emails/day）足够 MVP 使用。
- Python SDK (`resend`) 成熟。
- 发送状态回调方便追踪 DeliveryJob 状态。

Mailgun 或 SendGrid 作为备选，切换时只需替换 `EmailDeliveryProvider` 实现。

### 3. 通知通道：飞书群机器人 Webhook

使用飞书群机器人 Webhook 发送内部提醒。

MVP 发送时机：
- 新需求创建。
- Agent 任务失败。
- 有待审批项超过 30 分钟。
- 发送给客户的邮件失败。

Webhook URL 存储在环境变量 `FEISHU_WEBHOOK_URL`，不写死在代码中。

### 4. 附件存储：本地优先

附件存储到 `backend/storage/uploads`，数据库只保存元数据（文件名、类型、大小、storage_key）。

约束：
- 单文件限制 20MB。
- 允许类型：PDF、DOCX、XLSX、PNG、JPG、JPEG。
- 数据库只保存相对路径（`storage_key`），不保存绝对路径。
- 视频只保存链接（`video_links` JSON 字段），不上传文件。

后续切换到对象存储时，只需替换 storage backend，不改变模型和 API。

### 5. Delivery Center 抽象

`DeliveryCenter` 是统一出站接口，`EmailDeliveryProvider` 是 MVP 唯一实现。

```text
DeliveryCenter.send(delivery_job)
  → provider.send(payload)
  → 更新 DeliveryJob 状态
  → 写入 AuditLog
```

MVP 不实现：
- Provider 注册表 / 动态路由。
- 发送优先级队列。
- 批量发送。

只做：创建 DeliveryJob → 审查 → 发送 → 记录状态。

### 6. NotificationEvent 与 AuditLog 的边界

- `NotificationEvent`：内部提醒记录（发给了谁、什么渠道、成功/失败）。
- `AuditLog`：关键动作记录（谁做了什么、在什么时间、结果是什么）。

一条新需求创建会同时产生：
- 1 个 NotificationEvent（发给负责人）。
- 1 条 AuditLog（记录了谁提交的）。

### 7. Lead 绑定邮箱

Lead 新增 `owner_email` 字段，绑定提交时已验证的邮箱。

`POST /api/v1/leads` 不再是无认证的公开端点，它需要有效的客户 JWT，且 `owner_email` 必须等于 JWT 中的 email。

### 8. Artifact 版本化

对客 Artifact（customer_reply_draft、proposal_draft、sent_message）在负责人编辑时必须保留版本历史。

实现方式：
- `PATCH /api/v1/artifacts/{artifact_id}` 在更新时，先将当前 `content_markdown` 保存到 `version_history` JSON 字段。
- `version_history` 是一个 JSON 数组，每个元素包含 `content_markdown`、`edited_at` 和 `operator_note`。

## 消费方变更

新增消费方：
- 前端 Auth UI → `POST /api/v1/auth/*`。
- 前端需求提交页 → `POST /api/v1/leads/{lead_id}/attachments`。
- 后台 Delivery UI → `POST /api/v1/delivery-jobs`、`POST /api/v1/delivery-jobs/{id}/send`。
- Notification worker → `FEISHU_WEBHOOK_URL`。
- Email Delivery Provider → Resend API。

## 后果

- Auth 引入后，前端需要处理 token 过期和自动刷新。
- 邮件发送依赖外部服务 (Resend)，需要本地开发时提供 mock。
- 附件上传增加了 multipart/form-data 处理和后端存储管理。
- Notification worker 需要轻量的事件驱动机制（MVP 可以在 workflow runner 中同步调用）。
- 版本历史字段增加了 Artifact 模型的复杂度。
