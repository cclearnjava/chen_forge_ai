"""BE-05: Customer reply recording tests — TDD-first."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.auth.verification import create_verification_code
from app.models import AuditLog, Conversation, Message, MessageSenderType, Opportunity

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _setup(client: TestClient) -> str:
    """Create lead → lifecycle → return opportunity_id."""
    email = "reply-record@example.com"
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()

    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/api/v1/leads", json={
        "owner_email": email, "company": "客户回复测试公司", "contact_name": "周总",
        "contact_method": "email", "industry": "医疗健康",
        "problem": "客户回复录制测试需要一段足够长的客户业务问题描述文本内容",
        "desired_outcome": "智能问诊系统", "company_size": "100-200",
        "budget_range": "10-20w", "timeline": "3个月",
        "honeypot": "", "submitted_after_ms": 2000,
    }, headers=headers)
    return r.json()["lifecycle"]["opportunity"]["id"]


class TestOpportunityMessageRecording:
    def test_record_customer_reply_creates_customer_message(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/messages",
                        json={"body_markdown": "我们希望先做两周的 PoC，确认能对接现有 CRM。"},
                        headers=ADMIN)
        assert r.status_code == 201
        data = r.json()
        assert data["message"]["sender_type"] == "customer"
        assert data["message"]["body_markdown"] == "我们希望先做两周的 PoC，确认能对接现有 CRM。"
        assert data["message"]["source"] == "manual"

    def test_record_customer_reply_updates_opportunity_next_step(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/messages",
                        json={"body_markdown": "客户问能不能两周内出结果。"},
                        headers=ADMIN)
        assert r.status_code == 201
        data = r.json()
        assert data["opportunity"]["next_step"] == "Review customer reply"

    def test_record_customer_reply_writes_audit_log(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/messages",
                        json={"body_markdown": "客户说预算可以加到 15w。"},
                        headers=ADMIN)
        assert r.status_code == 201

        db = SessionLocal()
        logs = db.query(AuditLog).filter(AuditLog.action == "customer_message_recorded").all()
        assert len(logs) >= 1
        details = logs[-1].details_json or {}
        assert details.get("source") == "manual"
        assert "message_id" in details

    def test_record_customer_reply_missing_opportunity_returns_404(self, client: TestClient):
        init_db()
        r = client.post("/api/v1/admin/opportunities/nonexistent-id/messages",
                        json={"body_markdown": "test"}, headers=ADMIN)
        assert r.status_code == 404

    def test_record_customer_reply_missing_conversation_returns_422(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        db = SessionLocal()
        opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
        opp.conversation_id = None
        db.commit()
        db.close()

        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/messages",
                        json={"body_markdown": "test"}, headers=ADMIN)
        assert r.status_code == 422

    def test_record_customer_reply_empty_body_returns_422(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/messages",
                        json={"body_markdown": ""}, headers=ADMIN)
        assert r.status_code == 422

    def test_cockpit_includes_recorded_customer_reply_in_ascending_order(self, client: TestClient):
        init_db()
        opp_id = _setup(client)

        client.post(f"/api/v1/admin/opportunities/{opp_id}/messages",
                    json={"body_markdown": "第一条客户回复"}, headers=ADMIN)
        client.post(f"/api/v1/admin/opportunities/{opp_id}/messages",
                    json={"body_markdown": "第二条客户回复"}, headers=ADMIN)

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/cockpit", headers=ADMIN)
        messages = r.json()["messages"]
        customer_msgs = [m for m in messages if m["sender_type"] == "customer"]
        assert len(customer_msgs) >= 2
        assert customer_msgs[-1]["body_markdown"] == "第二条客户回复"
