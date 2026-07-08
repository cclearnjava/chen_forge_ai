"""Notification Center tests: API, summary, read/archive, workspace isolation."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.models import (
    Event, EventSeverity, Notification, NotificationKind,
    NotificationReadStatus, NotifDeliveryChannel, NotificationDeliveryStatus,
    Workspace,
)
from app.services.events import record_event
from app.services.workspace import get_default_workspace_id

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _test_wid():
    db = SessionLocal()
    from app.services.workspace import get_or_create_default_workspace
    wid = get_or_create_default_workspace(db).id
    db.close()
    return wid


class TestNotificationCenter:
    def test_record_event_creates_event(self, client: TestClient):
        init_db(); db = SessionLocal()
        e = record_event(db, workspace_id=None, type="lead.created", source="test",
                         subject_type="lead", subject_id="test-1",
                         title="Test lead created", summary="test summary")
        db.commit()
        assert e is not None and e.id is not None; db.close()

    def test_record_event_creates_notification_for_ruled_type(self, client: TestClient):
        init_db(); db = SessionLocal()
        record_event(db, workspace_id=None, type="decision.waiting", source="test",
                     subject_type="decision", subject_id="test-2", title="Approval required")
        db.commit()
        n = db.query(Notification).filter(Notification.kind == NotificationKind.approval_required).first()
        assert n is not None and n.status == NotificationReadStatus.unread
        db.close()

    def test_notification_list_returns_notifications(self, client: TestClient):
        init_db(); db = SessionLocal()
        wid = get_default_workspace_id(db)
        record_event(db, workspace_id=wid, type="lead.created", source="test", title="Test Lead", subject_type="lead", subject_id="t1")
        db.commit(); db.close()
        r = client.get("/api/v1/admin/notifications", headers=ADMIN)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_notification_summary(self, client: TestClient):
        init_db(); db = SessionLocal()
        wid = get_default_workspace_id(db)
        record_event(db, workspace_id=wid, type="decision.waiting", source="test", title="Approval needed", subject_type="decision", subject_id="t2")
        db.commit(); db.close()
        r = client.get("/api/v1/admin/notifications/summary", headers=ADMIN)
        assert r.status_code == 200
        assert r.json()["unread_count"] >= 1

    def test_mark_read(self, client: TestClient):
        init_db(); db = SessionLocal()
        wid = get_default_workspace_id(db)
        record_event(db, workspace_id=wid, type="lead.created", source="test", title="Mark Read Test", subject_type="lead", subject_id="t3")
        db.commit()
        n = db.query(Notification).order_by(Notification.created_at.desc()).first()
        nid = n.id; db.close()
        r = client.post(f"/api/v1/admin/notifications/{nid}/read", json={}, headers=ADMIN)
        assert r.status_code == 200

    def test_mark_all_read(self, client: TestClient):
        init_db(); db = SessionLocal()
        record_event(db, workspace_id=None, type="lead.created", source="test", title="ReadAll Test", subject_type="lead", subject_id="t4")
        db.commit(); db.close()
        r = client.post("/api/v1/admin/notifications/read-all", json={}, headers=ADMIN)
        assert r.status_code == 200

    def test_archive_notification(self, client: TestClient):
        init_db(); db = SessionLocal()
        wid = get_default_workspace_id(db)
        record_event(db, workspace_id=wid, type="lead.created", source="test", title="Archive Test", subject_type="lead", subject_id="t5")
        db.commit()
        n = db.query(Notification).order_by(Notification.created_at.desc()).first()
        nid = n.id; db.close()
        r = client.post(f"/api/v1/admin/notifications/{nid}/archive", json={}, headers=ADMIN)
        assert r.status_code == 200

    def test_other_workspace_notifications_not_visible(self, client: TestClient):
        init_db(); db = SessionLocal()
        ws2 = Workspace(slug="nf-ws2", name="NF WS2", is_default=False)
        db.add(ws2); db.commit()
        n2 = Notification(workspace_id=ws2.id, kind=NotificationKind.lead_created,
                          title="WS2 notification", severity=EventSeverity.info,
                          status=NotificationReadStatus.unread)
        db.add(n2); db.commit(); db.close()
        r = client.get("/api/v1/admin/notifications", headers=ADMIN)
        items = r.json()["items"]
        assert not any(n.get("workspace_id") == ws2.id for n in items if n.get("workspace_id"))
