# WP-7: Delivery Center + Notification

- **Goal**: Delivery Center 抽象层、Resend email provider、飞书 Webhook 内部通知、DeliveryJob 状态机。
- **Write set**: `backend/app/services/delivery.py`, `backend/app/services/notification.py`, `backend/app/api/delivery.py`, `backend/tests/test_delivery.py`, `backend/tests/test_notification.py`
- **Depends on**: WP-1 (DeliveryJob, NotificationEvent models), WP-6 (approved Artifact)
- **Parallel with**: 无（依赖 WP-6）
- **Seam owner**: WP-7 负责对客发送的完整链路，WP-8 集成验证
- **Acceptance test**:
  - `POST /api/v1/delivery-jobs` 基于已审批 Artifact 创建 DeliveryJob（201）
  - 未审批 Artifact 创建 DeliveryJob 被拒绝（422）
  - `POST /api/v1/delivery-jobs/{id}/send` 触发发送（202）
  - Mock email provider 能记录发送内容和收件人（不实际发邮件）
  - DeliveryJob 状态从 queued → sending → sent 正常流转
  - 发送失败时 DeliveryJob.status = failed，有 error_message
  - `FEISHU_WEBHOOK_URL` 未设置时 Notification 静默跳过，不阻塞流程
  - 新 Lead 创建时自动触发 lead_created 通知
  - 发送成功/失败写入 AuditLog
