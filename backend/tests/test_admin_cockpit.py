"""BE-04: Admin Cockpit API tests — TDD-first, expected to fail until BE-01→03 implemented."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.auth.verification import create_verification_code
from app.models import Conversation, Contact, Message, Opportunity

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _setup(client: TestClient) -> str:
    """Create lead → lifecycle → run sales agent → return opportunity_id."""
    email = "cockpit-test@example.com"
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()

    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/api/v1/leads", json={
        "owner_email": email, "company": "驾驶舱测试公司", "contact_name": "钱总",
        "contact_method": "email", "industry": "教育科技",
        "problem": "驾驶舱聚合测试需要一段足够长的客户业务问题描述文",
        "desired_outcome": "智能驾驶舱", "company_size": "20-50",
        "budget_range": "3-5w", "timeline": "1个月",
        "honeypot": "", "submitted_after_ms": 2000,
    }, headers=headers)

    opp_id = r.json()["lifecycle"]["opportunity"]["id"]

    # Also run sales agent to generate artifacts + decisions
    client.post("/api/v1/admin/agent-runs/sales-reply",
                json={"opportunity_id": opp_id}, headers=ADMIN)

    # Approve the decision to generate delivery_job
    r = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN)
    decisions = r.json()["opportunity"]["decisions"]
    waiting = [d for d in decisions if d["status"] == "waiting"]
    if waiting:
        client.post(f"/api/v1/decisions/{waiting[0]['id']}/approve", json={}, headers=ADMIN)

    return opp_id


class TestAdminCockpit:
    def test_get_cockpit_returns_opportunity_customer_conversation(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/cockpit", headers=ADMIN)
        assert r.status_code == 200
        data = r.json()
        assert data["opportunity"] is not None
        assert data["customer"] is not None
        assert data["customer"]["name"] == "驾驶舱测试公司"

    def test_get_cockpit_returns_messages_in_ascending_order(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/cockpit", headers=ADMIN)
        messages = r.json()["messages"]
        assert len(messages) >= 1
        timestamps = [m["created_at"] for m in messages]
        assert timestamps == sorted(timestamps)

    def test_get_cockpit_returns_artifacts_in_descending_order(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/cockpit", headers=ADMIN)
        artifacts = r.json()["artifacts"]
        assert len(artifacts) >= 1
        timestamps = [a["created_at"] for a in artifacts]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_get_cockpit_returns_decisions_in_descending_order(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/cockpit", headers=ADMIN)
        decisions = r.json()["decisions"]
        assert len(decisions) >= 1
        timestamps = [d["created_at"] for d in decisions]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_get_cockpit_returns_delivery_jobs(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/cockpit", headers=ADMIN)
        jobs = r.json()["delivery_jobs"]
        assert len(jobs) >= 1
        assert jobs[0]["channel"] == "manual_copy"

    def test_get_cockpit_returns_audit_logs(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/cockpit", headers=ADMIN)
        logs = r.json()["audit_logs"]
        assert len(logs) >= 1

    def test_get_cockpit_returns_agent_runs(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/cockpit", headers=ADMIN)
        runs = r.json()["agent_runs"]
        assert len(runs) >= 1

    def test_get_cockpit_missing_opportunity_returns_404(self, client: TestClient):
        init_db()
        r = client.get("/api/v1/admin/opportunities/nonexistent-id/cockpit", headers=ADMIN)
        assert r.status_code == 404

    def test_get_cockpit_without_conversation_returns_empty_messages(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        db = SessionLocal()
        opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
        opp.conversation_id = None
        db.commit()

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/cockpit", headers=ADMIN)
        assert r.status_code == 200
        assert r.json()["messages"] == []

    def test_get_cockpit_without_contact_returns_null_contact(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        db = SessionLocal()
        opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
        opp.primary_contact_id = None
        db.commit()

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/cockpit", headers=ADMIN)
        assert r.status_code == 200
        assert r.json()["contact"] is None
