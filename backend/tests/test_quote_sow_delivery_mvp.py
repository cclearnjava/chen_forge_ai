"""BE-06: Quote/SOW delivery MVP tests — TDD-first."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.auth.verification import create_verification_code
from app.models import AuditLog, DeliveryChannel, DeliveryJob, DeliveryStatus, Message, Opportunity

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _setup_approved_quote_sow(client: TestClient) -> str:
    """Create lead → proposal → approve → sent → feedback → quote/sow → approve → return opp_id."""
    email = "qsdelivery-test@example.com"
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()
    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.post("/api/v1/leads", json={
        "owner_email": email, "company": "QS发送测试公司", "contact_name": "马总",
        "contact_method": "email", "industry": "医疗健康",
        "problem": "QS发送测试需要一段足够长的客户业务问题描述文本内容填充",
        "desired_outcome": "智能分诊系统", "company_size": "100-200",
        "budget_range": "15-25w", "timeline": "3个月",
        "honeypot": "", "submitted_after_ms": 2000,
    }, headers=h)
    opp_id = r.json()["lifecycle"]["opportunity"]["id"]
    # Proposal → approve → sent
    client.post("/api/v1/admin/agent-runs/proposal-draft", json={"opportunity_id": opp_id}, headers=ADMIN)
    r2 = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN)
    w = [d for d in r2.json()["opportunity"]["decisions"] if d["status"] == "waiting"]
    client.post(f"/api/v1/decisions/{w[0]['id']}/approve", json={}, headers=ADMIN)
    r3 = client.get(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal", headers=ADMIN)
    art_id = r3.json()["artifact_id"]
    db2 = SessionLocal()
    from app.models import Artifact
    art = db2.query(Artifact).filter(Artifact.id == art_id).first()
    job = DeliveryJob(lead_id=art.lead_id if art else None, artifact_id=art_id,
                      channel=DeliveryChannel.manual_copy, recipient="test@test.com",
                      subject="PoC: test", body_markdown="test", status=DeliveryStatus.draft)
    db2.add(job); db2.commit(); db2.close()
    client.post(f"/api/v1/delivery-jobs/{job.id}/mark-sent", json={}, headers=ADMIN)
    # Feedback + Quote/SOW → approve
    client.post(f"/api/v1/admin/opportunities/{opp_id}/proposal-feedback",
                json={"body_markdown": "方向可以，预算控制在 5 万以内做两周 PoC。"}, headers=ADMIN)
    client.post("/api/v1/admin/agent-runs/quote-sow", json={"opportunity_id": opp_id}, headers=ADMIN)
    r4 = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN)
    w2 = [d for d in r4.json()["opportunity"]["decisions"] if d["status"] == "waiting"]
    if w2:
        client.post(f"/api/v1/decisions/{w2[0]['id']}/approve", json={}, headers=ADMIN)
    return opp_id


class TestQuoteSowDeliveryMvp:
    def test_get_approved_quote_sow_returns_200(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_quote_sow(client)
        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/approved-quote-sow", headers=ADMIN)
        assert r.status_code == 200
        data = r.json()
        assert data["quote_artifact_id"] is not None
        assert data["sow_artifact_id"] is not None

    def test_get_approved_quote_sow_without_returns_404(self, client: TestClient):
        init_db()
        r = client.get("/api/v1/admin/opportunities/nonexistent-id/approved-quote-sow", headers=ADMIN)
        assert r.status_code == 404

    def test_create_delivery_job_returns_201(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_quote_sow(client)
        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-quote-sow/delivery-job",
                        json={}, headers=ADMIN)
        assert r.status_code == 201
        assert r.json()["delivery_job"]["status"] == "draft"

    def test_create_delivery_job_is_idempotent(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_quote_sow(client)
        r1 = client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-quote-sow/delivery-job",
                         json={}, headers=ADMIN)
        r2 = client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-quote-sow/delivery-job",
                         json={}, headers=ADMIN)
        assert r1.json()["delivery_job"]["id"] == r2.json()["delivery_job"]["id"]

    def test_mark_sent_writes_message(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_quote_sow(client)
        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-quote-sow/delivery-job",
                        json={}, headers=ADMIN)
        job_id = r.json()["delivery_job"]["id"]
        db = SessionLocal()
        before = db.query(Message).count()
        client.post(f"/api/v1/delivery-jobs/{job_id}/mark-sent", json={}, headers=ADMIN)
        after = db.query(Message).count()
        assert after == before + 1

    def test_mark_sent_writes_audit_log(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_quote_sow(client)
        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-quote-sow/delivery-job",
                        json={}, headers=ADMIN)
        job_id = r.json()["delivery_job"]["id"]
        client.post(f"/api/v1/delivery-jobs/{job_id}/mark-sent", json={}, headers=ADMIN)
        db = SessionLocal()
        logs = db.query(AuditLog).filter(AuditLog.action == "quote_sow_sent").all()
        assert len(logs) >= 1

    def test_mark_sent_advances_opportunity(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_quote_sow(client)
        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/approved-quote-sow/delivery-job",
                        json={}, headers=ADMIN)
        client.post(f"/api/v1/delivery-jobs/{r.json()['delivery_job']['id']}/mark-sent",
                    json={}, headers=ADMIN)
        db = SessionLocal()
        opp = db.query(Opportunity).filter(Opportunity.id == opp_id).one()
        assert opp.stage.value == "contracting"
