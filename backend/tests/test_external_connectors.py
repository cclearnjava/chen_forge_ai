"""External Connector tests (P5): connector CRUD, inbound webhook, idempotency,
contact matching, workspace isolation, event + notification wiring."""

from starlette.testclient import TestClient
from app.db import SessionLocal, init_db
from app.models import (
    Contact, Conversation, Customer, Event, ExternalConnector, Message,
    Notification, Workspace,
)

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _make_connector(client, name="Mock 入口", provider="mock"):
    r = client.post("/api/v1/admin/connectors", json={"provider": provider, "name": name}, headers=ADMIN)
    assert r.status_code == 201, r.text
    return r.json()


def _inbound(client, token, **over):
    body = {"external_message_id": "m1", "sender": {"name": "王总", "email": "wang@ex.com"}, "body_markdown": "你好，想确认报价"}
    body.update(over)
    return client.post(f"/api/v1/connectors/{token}/inbound", json=body)


class TestConnectorManagement:
    def test_create_connector(self, client: TestClient):
        init_db()
        c = _make_connector(client)
        assert c["provider"] == "mock"
        assert c["status"] == "active"
        assert c["webhook_token"]
        assert c["webhook_path"].endswith("/inbound")

    def test_create_invalid_provider_rejected(self, client: TestClient):
        init_db()
        r = client.post("/api/v1/admin/connectors", json={"provider": "sms", "name": "x"}, headers=ADMIN)
        assert r.status_code == 422

    def test_list_only_current_workspace(self, client: TestClient):
        init_db(); db = SessionLocal()
        ws2 = Workspace(slug="conn-ws2", name="WS2", is_default=False)
        db.add(ws2); db.commit()
        other = ExternalConnector(workspace_id=ws2.id, provider="mock", name="WS2 Conn", webhook_token="tok-ws2")
        db.add(other); db.commit(); db.close()
        _make_connector(client, name="默认入口")
        r = client.get("/api/v1/admin/connectors", headers=ADMIN)
        names = [c["name"] for c in r.json()["items"]]
        assert "默认入口" in names
        assert "WS2 Conn" not in names

    def test_pause_connector_via_patch(self, client: TestClient):
        init_db()
        c = _make_connector(client)
        r = client.patch(f"/api/v1/admin/connectors/{c['id']}", json={"status": "paused"}, headers=ADMIN)
        assert r.status_code == 200
        assert r.json()["status"] == "paused"


class TestInbound:
    def test_active_connector_creates_message(self, client: TestClient):
        init_db()
        c = _make_connector(client)
        r = _inbound(client, c["webhook_token"])
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["deduplicated"] is False
        assert data["message"]["source"] == "external_mock"
        assert data["message"]["body_markdown"] == "你好，想确认报价"
        assert data["customer"] and data["contact"] and data["conversation"]

    def test_paused_connector_rejects_inbound(self, client: TestClient):
        init_db()
        c = _make_connector(client)
        client.patch(f"/api/v1/admin/connectors/{c['id']}", json={"status": "paused"}, headers=ADMIN)
        r = _inbound(client, c["webhook_token"])
        assert r.status_code == 422

    def test_unknown_token_404(self, client: TestClient):
        init_db()
        r = _inbound(client, "nope-token")
        assert r.status_code == 404

    def test_invalid_sender_422(self, client: TestClient):
        init_db()
        c = _make_connector(client)
        r = client.post(f"/api/v1/connectors/{c['webhook_token']}/inbound",
                        json={"external_message_id": "x", "sender": {"name": "无身份"}, "body_markdown": "hi"})
        assert r.status_code == 422

    def test_known_email_matches_existing_contact(self, client: TestClient):
        init_db(); db = SessionLocal()
        from app.services.workspace import get_default_workspace_id
        wid = get_default_workspace_id(db)
        cust = Customer(workspace_id=wid, name="老客户", owner_email="known@ex.com")
        db.add(cust); db.flush()
        db.add(Contact(workspace_id=wid, customer_id=cust.id, name="老王", email="known@ex.com", is_primary=True))
        db.commit(); cust_id = cust.id; db.close()
        c = _make_connector(client)
        r = _inbound(client, c["webhook_token"], sender={"name": "老王", "email": "known@ex.com"})
        assert r.json()["customer"]["id"] == cust_id

    def test_unknown_sender_creates_chain(self, client: TestClient):
        init_db()
        c = _make_connector(client)
        r = _inbound(client, c["webhook_token"], sender={"name": "新客户", "email": "new@ex.com"})
        data = r.json()
        assert data["customer"]["name"] == "新客户"
        assert data["contact"]["email"] == "new@ex.com"
        assert data["conversation"]["id"]

    def test_duplicate_message_deduplicated(self, client: TestClient):
        init_db()
        c = _make_connector(client)
        r1 = _inbound(client, c["webhook_token"], external_message_id="dup-1")
        r2 = _inbound(client, c["webhook_token"], external_message_id="dup-1")
        assert r1.json()["deduplicated"] is False
        assert r2.json()["deduplicated"] is True
        assert r1.json()["message"]["id"] == r2.json()["message"]["id"]
        db = SessionLocal()
        cnt = db.query(Message).filter(Message.external_message_id == "dup-1").count()
        db.close()
        assert cnt == 1

    def test_same_msg_id_different_connector_both_created(self, client: TestClient):
        init_db()
        c1 = _make_connector(client, name="入口1")
        c2 = _make_connector(client, name="入口2")
        _inbound(client, c1["webhook_token"], external_message_id="same-1")
        r2 = _inbound(client, c2["webhook_token"], external_message_id="same-1")
        assert r2.json()["deduplicated"] is False
        db = SessionLocal()
        cnt = db.query(Message).filter(Message.external_message_id == "same-1").count()
        db.close()
        assert cnt == 2

    def test_cross_workspace_email_not_matched(self, client: TestClient):
        init_db(); db = SessionLocal()
        ws2 = Workspace(slug="conn-iso", name="WS2", is_default=False)
        db.add(ws2); db.commit()
        cust2 = Customer(workspace_id=ws2.id, name="别的workspace客户", owner_email="shared@ex.com")
        db.add(cust2); db.flush()
        db.add(Contact(workspace_id=ws2.id, customer_id=cust2.id, name="他", email="shared@ex.com", is_primary=True))
        db.commit(); cust2_id = cust2.id; db.close()
        c = _make_connector(client)
        r = _inbound(client, c["webhook_token"], sender={"name": "同邮箱", "email": "shared@ex.com"})
        # must NOT reuse ws2's customer — a fresh one is created in default workspace
        assert r.json()["customer"]["id"] != cust2_id

    def test_records_event_and_notification(self, client: TestClient):
        init_db()
        c = _make_connector(client)
        r = _inbound(client, c["webhook_token"], external_message_id="evt-1")
        data = r.json()
        assert data["event_id"] and data["notification_id"]
        db = SessionLocal()
        ev = db.query(Event).filter(Event.type == "external_message.received", Event.id == data["event_id"]).first()
        nf = db.query(Notification).filter(Notification.id == data["notification_id"]).first()
        db.close()
        assert ev is not None and nf is not None

    def test_raw_payload_saved(self, client: TestClient):
        init_db()
        c = _make_connector(client)
        r = _inbound(client, c["webhook_token"], external_message_id="raw-1",
                     raw_payload={"provider": "mock", "trace": "abc"})
        mid = r.json()["message"]["id"]
        db = SessionLocal()
        m = db.query(Message).filter(Message.id == mid).first()
        raw = m.raw_payload_json; db.close()
        assert raw.get("trace") == "abc"
