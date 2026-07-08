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

    def test_lead_creation_generates_notification(self, client: TestClient):
        init_db()
        from app.auth.verification import create_verification_code
        email = "nf-lead@example.com"
        db = SessionLocal(); code = create_verification_code(db, email); db.close()
        r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = client.post("/api/v1/leads", json={
            "owner_email": email, "company": "NFLeadTest", "contact_name": "T",
            "contact_method": "email", "industry": "Tech",
            "problem": "Notification integration test with sufficient text",
            "desired_outcome": "Test", "company_size": "10-50", "budget_range": "1-3w",
            "timeline": "1m", "honeypot": "", "submitted_after_ms": 2000,
        }, headers=h)
        assert r.status_code == 201
        # Verify notification was generated
        r2 = client.get("/api/v1/admin/notifications", headers=ADMIN)
        items = r2.json()["items"]
        lead_notifs = [n for n in items if n["kind"] == "lead_created"]
        assert len(lead_notifs) >= 1

    def test_approve_creates_delivery_notification(self, client: TestClient):
        init_db()
        from app.auth.verification import create_verification_code
        email = "nf-approve@example.com"
        db = SessionLocal(); code = create_verification_code(db, email); db.close()
        r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = client.post("/api/v1/leads", json={
            "owner_email": email, "company": "NFApproveTest", "contact_name": "T",
            "contact_method": "email", "industry": "Tech",
            "problem": "Approve notification integration test text here",
            "desired_outcome": "Test", "company_size": "10-50", "budget_range": "1-3w",
            "timeline": "1m", "honeypot": "", "submitted_after_ms": 2000,
        }, headers=h)
        opp_id = r.json()["lifecycle"]["opportunity"]["id"]
        client.post("/api/v1/admin/agent-runs/sales-reply", json={"opportunity_id": opp_id}, headers=ADMIN)
        r2 = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN)
        w = [d for d in r2.json()["opportunity"]["decisions"] if d["status"] == "waiting"]
        assert w
        client.post(f"/api/v1/decisions/{w[0]['id']}/approve", json={}, headers=ADMIN)
        r3 = client.get("/api/v1/admin/notifications", headers=ADMIN)
        items = r3.json()["items"]
        kinds = [n["kind"] for n in items]
        assert "approval_required" in kinds or "delivery_action_required" in kinds
