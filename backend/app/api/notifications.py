from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.services.workspace_guard import get_current_workspace_id
from app.models import Notification, NotificationReadStatus

router = APIRouter(prefix="/admin/notifications", tags=["notifications"])


def _notif_to_dict(n: Notification) -> dict:
    return {
        "id": n.id, "workspace_id": n.workspace_id, "event_id": n.event_id,
        "kind": n.kind.value if hasattr(n.kind, "value") else n.kind,
        "title": n.title, "body": n.body,
        "severity": n.severity.value if hasattr(n.severity, "value") else n.severity,
        "status": n.status.value if hasattr(n.status, "value") else n.status,
        "target_type": n.target_type, "target_id": n.target_id, "target_url": n.target_url,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("")
def list_notifications(
    status: str | None = Query(None),
    kind: str | None = Query(None),
    severity: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    query = db.query(Notification).filter(Notification.workspace_id == wid)
    if status:
        query = query.filter(Notification.status == status)
    if kind:
        query = query.filter(Notification.kind == kind)
    if severity:
        query = query.filter(Notification.severity == severity)
    total = query.count()
    items = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [_notif_to_dict(n) for n in items], "total": total}


@router.get("/summary")
def get_notification_summary(
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    unread = db.query(Notification).filter(
        Notification.workspace_id == wid, Notification.status == NotificationReadStatus.unread
    ).count()
    critical = db.query(Notification).filter(
        Notification.workspace_id == wid, Notification.status == NotificationReadStatus.unread,
        Notification.severity == "critical",
    ).count()
    latest = db.query(Notification).filter(
        Notification.workspace_id == wid,
    ).order_by(Notification.created_at.desc()).limit(5).all()
    return {
        "unread_count": unread,
        "critical_count": critical,
        "latest": [_notif_to_dict(n) for n in latest],
    }


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    n = db.query(Notification).filter(
        Notification.id == notification_id, Notification.workspace_id == wid,
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    from datetime import datetime as dt
    n.status = NotificationReadStatus.read
    n.read_at = dt.utcnow()
    db.commit()
    return {"id": n.id, "status": n.status.value}


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    from datetime import datetime as dt
    now = dt.utcnow()
    count = db.query(Notification).filter(
        Notification.workspace_id == wid, Notification.status == NotificationReadStatus.unread,
    ).update({"status": NotificationReadStatus.read, "read_at": now})
    db.commit()
    return {"marked_read": count}


@router.post("/{notification_id}/archive")
def archive_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    n = db.query(Notification).filter(
        Notification.id == notification_id, Notification.workspace_id == wid,
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    from datetime import datetime as dt
    n.status = NotificationReadStatus.archived
    n.archived_at = dt.utcnow()
    db.commit()
    return {"id": n.id, "status": n.status.value}
