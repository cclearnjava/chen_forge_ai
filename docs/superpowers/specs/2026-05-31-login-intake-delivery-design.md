# ChenForge AI 登录、需求提交与交付发送设计

## 背景

ChenForge AI 的 MVP 不只是收集客户线索，而是要形成一个可验证的一人公司运营闭环：客户提交 AI 落地需求，Agent 生成需求理解、回复草稿和方案草案，负责人审核修改后再发送给客户。

MVP 的客户侧正式触达通道先使用邮件。系统设计不把发送能力写死成邮件，而是抽象为 Delivery Center，后续可扩展到客户门户、企业微信客户联系、飞书、短信和人工复制发送。

## 目标

- 用户通过邮箱验证码登录或注册。
- 用户在前台提交业务需求，并可附加文档、截图和视频链接。
- 系统保存线索、附件元数据和提交上下文。
- 系统通知负责人有新需求进入。
- Agent 生成需求理解、客户回复草稿、方案草案和下一步建议。
- 负责人在后台审核、修改、要求重写、暂缓或批准发送。
- MVP 批准后通过邮件发送给客户。
- 所有对客发送都保存版本、状态和审计日志。

## 非目标

- MVP 不做手机号验证码。
- MVP 不做视频大文件上传，只保存视频链接。
- MVP 不做客户门户状态追踪。
- MVP 不做复杂 CRM、报价系统、合同系统和支付系统。
- Agent 不允许绕过人工审批直接发送客户消息。

## 用户流程

```text
访问 ChenForge AI
  -> 输入邮箱
  -> 获取验证码
  -> 验证通过并建立会话
  -> 填写公司、行业、需求、预算、时间和联系方式
  -> 上传文档 / 截图，填写视频链接
  -> 提交需求
  -> 页面提示已收到，并说明下一步
```

## 内部运营流程

```text
新需求创建
  -> 保存 Lead 和 LeadAttachment
  -> 创建内部 NotificationEvent
  -> 发送飞书 / 企业微信提醒给负责人
  -> Agent 生成 requirement_summary、customer_reply_draft、proposal_draft
  -> 生成待审批 Decision
  -> 负责人审核并可编辑 Artifact
  -> 批准后创建 DeliveryJob
  -> EmailDeliveryProvider 发送邮件
  -> 保存发送状态和 AuditLog
```

## 核心模块

### Auth

Auth 只负责邮箱验证码登录和会话管理。验证码需要有过期时间、重试限制和发送频率限制。MVP 可以使用 cookie session 或 JWT，但后端必须拥有失效能力。

### Intake

Intake 负责客户需求表单。Lead 必须绑定提交邮箱，附件作为 LeadAttachment 保存，文件内容本地开发存在 `backend/storage/uploads`，正式环境切换到对象存储。

### Agent Workflow

Agent 工作流生成面向负责人审核的 Artifact：

- `requirement_summary`：需求理解。
- `customer_reply_draft`：客户回复草稿。
- `proposal_draft`：方案草案。
- `discovery_questions`：澄清问题。
- `delivery_roadmap`：下一步路线。

所有客户可见 Artifact 必须 `requires_approval=true`。

### Review Workbench

后台评审台展示 Lead 原文、附件、AI 生成物和待决策项。负责人可以批准、修改后批准、要求重写、暂缓或归档。

### Delivery Center

Delivery Center 是统一的出站发送抽象。MVP 只实现 `email` 通道，但数据结构保留多通道扩展能力：

- `email`
- `feishu`
- `wecom`
- `sms`
- `client_portal`
- `manual_copy`

客户正式交付内容必须走 Delivery Center。内部提醒走 Notification 模块。

### Notification

Notification 只服务内部提醒。MVP 支持飞书或企业微信群机器人 Webhook，用于提醒负责人有新需求、Agent 生成失败、发送失败或有待审批项。

## 数据边界

- `Lead` 是客户需求根实体。
- `LeadAttachment` 保存附件元数据和存储路径。
- `VerificationCode` 保存邮箱验证码的哈希、过期时间和使用状态。
- `Artifact` 保存 Agent 或人工修改后的内容版本。
- `Decision` 保存人工审批状态。
- `DeliveryJob` 保存对客发送任务。
- `NotificationEvent` 保存内部提醒事件。
- `AuditLog` 保存关键动作记录。

## 安全约束

- 验证码只保存哈希，不保存明文。
- 附件限制类型和大小。
- 视频只保存链接，不直接上传。
- LLM 不接触密钥和系统环境变量。
- 对客内容必须人工审批。
- 发送给客户的内容必须保存最终版本。
- 失败的通知和邮件发送必须可重试。

## MVP 验收

- 用户可以用邮箱验证码登录。
- 用户可以提交需求、上传文档或截图、填写视频链接。
- 负责人可以在后台看到新 Lead 和附件。
- 新 Lead 会触发飞书或企业微信内部提醒。
- Agent 可以生成需求理解、回复草稿和方案草案。
- 负责人可以编辑并批准发送。
- 系统可以通过邮件把已批准内容发给客户。
- 后台能看到发送状态、发送时间和最终发送内容。
