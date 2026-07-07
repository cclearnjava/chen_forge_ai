"""BE-05: Proposal delivery MVP tests — TDD-first."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.auth.verification import create_verification_code
from app.models import AuditLog, DeliveryJob, Message

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _setup_approved_proposal(client: TestClient) -> str:
    """Create lead → lifecycle → generate proposal → approve → return opportunity_id."""
    email = "proposal-delivery@example.com"
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()
    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/v1/leads", json={
        "owner_email": email, "company": "提案发送测试公司", "contact_name": "何总",
        "contact_method": "email", "industry": "医疗健康",
        "problem": "提案发送测试需要一段足够长的客户业务问题描述文本内容",
        "desired_outcome": "智能诊断系统", "company_size": "100-200",
        "budget_range": "10-20w", "timeline": "3个月",
        "honeypot": "", "submitted_after_ms": 2000,
    }, headers=h)
    opp_id = r.json()["lifecycle"]["opportunity"]["id"]
    r = client.post("/api/v1/admin/agent-runs/proposal-draft", json={"opportunity_id": opp_id}, headers=ADMIN)
    assert r.status_code == 200
    r2 = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN)
    decs = r2.json()["opportunity"]["decisions"]
    w = [d for d in decs if d["status"] == "waiting"]
    assert w
    client.post(f"/api/v1/decisions/{w[0]['id']}/approve", json={}, headers=ADMIN)
    return opp_id


class TestProposalDeliveryMvp:
    def test_create_delivery_job_with_approved_proposal(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_proposal(client)
        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal/delivery-job",
                        json={}, headers=ADMIN)
        assert r.status_code == 201
        data = r.json()
        assert "delivery_job" in data
        assert data["delivery_job"]["status"] == "draft"
        assert "PoC Proposal" in data["delivery_job"]["subject"]

    def test_create_delivery_job_without_approved_proposal_returns_404(self, client: TestClient):
        init_db()
        r = client.post("/api/v1/admin/opportunities/nonexistent-id/approved-proposal/delivery-job",
                        json={}, headers=ADMIN)
        assert r.status_code == 404

    def test_create_delivery_job_is_idempotent(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_proposal(client)
        r1 = client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal/delivery-job",
                         json={}, headers=ADMIN)
        assert r1.status_code == 201
        r2 = client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal/delivery-job",
                         json={}, headers=ADMIN)
        assert r2.status_code in (200, 201)
        assert r1.json()["delivery_job"]["id"] == r2.json()["delivery_job"]["id"]

    def test_create_delivery_job_writes_audit_log(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_proposal(client)
        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal/delivery-job",
                        json={"operator_note": "准备通过微信发送"}, headers=ADMIN)
        assert r.status_code == 201
        db = SessionLocal()
        logs = db.query(AuditLog).filter(AuditLog.action == "proposal_delivery_job_created").all()
        assert len(logs) >= 1
        details = logs[-1].details_json or {}
        assert details.get("delivery_job_id") is not None

    def test_create_duplicate_does_not_write_duplicate_audit(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_proposal(client)
        client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal/delivery-job",
                    json={}, headers=ADMIN)
        db = SessionLocal()
        before = len(db.query(AuditLog).filter(AuditLog.action == "proposal_delivery_job_created").all())
        client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal/delivery-job",
                    json={}, headers=ADMIN)
        after = len(db.query(AuditLog).filter(AuditLog.action == "proposal_delivery_job_created").all())
        assert after == before  # no duplicate audit log on idempotent return

    def test_mark_sent_proposal_writes_conversation_message(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_proposal(client)
        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal/delivery-job",
                        json={}, headers=ADMIN)
        job_id = r.json()["delivery_job"]["id"]
        db = SessionLocal()
        before = db.query(Message).count()
        r2 = client.post(f"/api/v1/delivery-jobs/{job_id}/mark-sent",
                         json={"operator_note": "已通过邮件发送给客户"}, headers=ADMIN)
        assert r2.status_code == 200
        after = db.query(Message).count()
        assert after == before + 1

    def test_mark_sent_proposal_writes_proposal_sent_audit_log(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_proposal(client)
        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal/delivery-job",
                        json={}, headers=ADMIN)
        job_id = r.json()["delivery_job"]["id"]
        client.post(f"/api/v1/delivery-jobs/{job_id}/mark-sent",
                    json={"operator_note": "已发送"}, headers=ADMIN)
        db = SessionLocal()
        logs = db.query(AuditLog).filter(AuditLog.action == "proposal_sent").all()
        assert len(logs) >= 1
