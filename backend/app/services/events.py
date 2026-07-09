"""Event service — record system events and generate notifications via rules."""

from sqlalchemy.orm import Session
from app.models import (
    Event, EventSeverity, Notification, NotificationKind,
    NotificationReadStatus, NotificationDelivery,
    NotifDeliveryChannel, NotificationDeliveryStatus,
)

NOTIFICATION_RULES = {
    "lead.created": ("lead_created", EventSeverity.info, "新线索"),
    "message.customer_recorded": ("customer_reply_recorded", EventSeverity.info, "客户回复"),
    "external_message.received": ("customer_reply_recorded", EventSeverity.info, "新客户消息"),
    "decision.waiting": ("approval_required", EventSeverity.warning, "待审批"),
    "artifact.proposal_draft.created": ("proposal_ready", EventSeverity.info, "Proposal 就绪"),
    "artifact.quote_draft.created": ("quote_sow_ready", EventSeverity.info, "Quote/SOW 就绪"),
    "delivery_job.created": ("delivery_action_required", EventSeverity.warning, "待发送"),
    "delivery_job.sent": ("delivery_sent", EventSeverity.success, "已发送"),
    "delivery_job.failed": ("delivery_failed", EventSeverity.critical, "发送失败"),
}


def record_event(
    db: Session, *,
    workspace_id: str | None,
    type: str, source: str,
    subject_type: str | None = None, subject_id: str | None = None,
    title: str = "", summary: str | None = None,
    severity: EventSeverity = EventSeverity.info,
    actor: str = "system", payload_json: dict | None = None,
    target_type: str | None = None, target_id: str | None = None,
    target_url: str | None = None,
) -> Event | None:
    """Create an Event. If a notification rule matches, also create a Notification + in-app delivery."""
    event = Event(
        workspace_id=workspace_id, type=type, source=source,
        severity=severity, subject_type=subject_type, subject_id=subject_id,
        actor=actor, title=title, summary=summary, payload_json=payload_json,
    )
    db.add(event)
    db.flush()

    rule = NOTIFICATION_RULES.get(type)
    if rule:
        kind_str, sev, prefix = rule
        kind = NotificationKind(kind_str)
        notif = Notification(
            workspace_id=workspace_id, event_id=event.id, kind=kind,
            title=title or f"{prefix}", body=summary,
            severity=sev, target_type=target_type or subject_type,
            target_id=target_id or subject_id, target_url=target_url,
            status=NotificationReadStatus.unread,
        )
        db.add(notif)
        db.flush()

        # In-app delivery
        db.add(NotificationDelivery(
            workspace_id=workspace_id, notification_id=notif.id,
            channel=NotifDeliveryChannel.in_app,
            status=NotificationDeliveryStatus.delivered,
        ))

    return event
