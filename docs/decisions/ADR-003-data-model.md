# ADR-003：核心数据模型

## 状态

Accepted

## 背景

MVP 的核心价值链是：访问者通过邮箱验证码登录，提交业务问题和附件，系统保存线索，Agent 生成需求理解、客户回复草稿和 proposal，人工负责人审核修改后批准发送。数据模型必须服务这个闭环，而不是提前扩展成完整 CRM。

## 决策

MVP 锁定 9 个核心模型：

1. `Lead`
   - 表示客户提交的业务问题。
   - 是诊断、proposal 和交付计划的根实体。

2. `LeadAttachment`
   - 表示客户上传的文档和截图。
   - 数据库只保存元数据、大小、类型和 storage key。

3. `VerificationCode`
   - 表示邮箱验证码。
   - 只保存验证码哈希、过期时间、使用状态和重试次数。

4. `AgentTask`
   - 表示一次 Agent 执行。
   - 保存输入、输出、状态、错误、开始和完成时间。

5. `Artifact`
   - 表示 Agent 或人工产出的生成物。
   - 内容同时支持 Markdown 和 JSON。
   - 对客生成物必须有 `requires_approval`。
   - 对客发送前的最终版本也保存为 Artifact。

6. `Decision`
   - 表示人工审批动作。
   - 状态包括 waiting、approved、edited_and_approved、deferred、rewrite_requested。

7. `DeliveryJob`
   - 表示对客户的正式发送任务。
   - MVP 只实现 email channel，但保留 channel 字段用于后续扩展。

8. `NotificationEvent`
   - 表示内部提醒事件。
   - MVP 支持飞书或企业微信群机器人 Webhook。

9. `AuditLog`
   - 表示关键动作记录。
   - 用于复盘和追踪责任边界。

## 消费方

- 公开官网消费 `Lead create`。
- 邮箱验证码登录消费 `VerificationCode`。
- 需求提交页消费 `LeadAttachment create`。
- 后台线索列表消费 `Lead list`。
- 后台线索详情消费 `Lead detail`、`LeadAttachment list`、`Artifact list`、`Decision list`、`DeliveryJob list`。
- Agent workflow 消费 `Lead`，生产 `AgentTask`、`Artifact`、`Decision`、`AuditLog`。
- Quality Reviewer 消费 `Artifact`，生产 review artifact 和 decision recommendation。
- Delivery Center 消费已审批 `Artifact`，生产 `DeliveryJob` 和 `AuditLog`。
- Notification worker 消费 `Lead`、`AgentTask`、`Decision`、`DeliveryJob` 的事件，生产 `NotificationEvent`。

## 不纳入 MVP 的模型

- ClientAccount。
- Payment。
- Contract。
- ClientPortalUser。
- NotificationSubscription。
- Full CRM pipeline。
- SMS verification。
- Video file object。

## 后果

- 后台不是完整 CRM，只是运营控制台。
- 线索状态足够表达 MVP，但不能承载复杂销售流程。
- 邮件是第一版正式发送通道，但发送模型不绑定邮件。
- 附件存储可从本地磁盘迁移到对象存储。
- 后续扩展客户门户时，需要新增用户、权限和客户组织模型。
