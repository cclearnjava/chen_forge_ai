"""TEST-01: Workspace isolation contract — every admin endpoint must reject cross-workspace IDs."""

import uuid
from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.models import Conversation, Customer, Decision, DeliveryChannel, DeliveryJob, DeliveryStatus, Opportunity, Workspace

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _make_ws2():
    db = SessionLocal()
    slug = "iso-" + uuid.uuid4().hex[:8]
    ws2 = Workspace(slug=slug, name="Isolation Test WS", is_default=False)
    db.add(ws2); db.commit(); wid = ws2.id
    lid = "00000000-0000-0000-0000-000000000000"
    cust = Customer(workspace_id=wid, name="ISO Cust", owner_email="iso@t.com")
    db.add(cust); db.commit()
    conv = Conversation(workspace_id=wid, customer_id=cust.id, title="ISO Conv", channel="web")
    db.add(conv); db.commit()
    opp = Opportunity(workspace_id=wid, customer_id=cust.id, title="ISO Opp", stage="lead", lead_id=lid)
    db.add(opp); db.commit()
    dec = Decision(workspace_id=wid, lead_id=lid, question="ISO Dec", status="waiting")
    db.add(dec); db.commit()
    dj = DeliveryJob(workspace_id=wid, lead_id=lid, artifact_id=lid, channel="manual_copy", recipient="t", subject="t", body_markdown="t")
    db.add(dj); db.commit(); db.close()
    return cust.id, conv.id, opp.id, dec.id, dj.id


class TestWorkspaceIsolationContract:

    def test_customer_detail_rejects_other_ws(self, client: TestClient):
        init_db(); cid, *_ = _make_ws2()
        assert client.get(f"/api/v1/admin/customers/{cid}", headers=ADMIN).status_code == 404

    def test_opportunity_detail_rejects_other_ws(self, client: TestClient):
        init_db(); _, _, oid, _, _ = _make_ws2()
        assert client.get(f"/api/v1/admin/opportunities/{oid}", headers=ADMIN).status_code == 404

    def test_opportunity_cockpit_rejects_other_ws(self, client: TestClient):
        init_db(); _, _, oid, _, _ = _make_ws2()
        assert client.get(f"/api/v1/admin/opportunities/{oid}/cockpit", headers=ADMIN).status_code == 404

    def test_conversation_messages_rejects_other_ws(self, client: TestClient):
        init_db(); _, cvid, _, _, _ = _make_ws2()
        assert client.get(f"/api/v1/admin/conversations/{cvid}/messages", headers=ADMIN).status_code == 404

    def test_decision_approve_rejects_other_ws(self, client: TestClient):
        init_db(); _, _, _, did, _ = _make_ws2()
        assert client.post(f"/api/v1/decisions/{did}/approve", json={}, headers=ADMIN).status_code == 404

    def test_delivery_job_get_rejects_other_ws(self, client: TestClient):
        init_db(); _, _, _, _, djid = _make_ws2()
        assert client.get(f"/api/v1/delivery-jobs/{djid}", headers=ADMIN).status_code == 404

    def test_delivery_job_mark_sent_rejects_other_ws(self, client: TestClient):
        init_db(); _, _, _, _, djid = _make_ws2()
        assert client.post(f"/api/v1/delivery-jobs/{djid}/mark-sent", json={}, headers=ADMIN).status_code == 404
