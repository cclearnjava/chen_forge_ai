"""BE-05: DeliveryJob execution tests — TDD-first, expected to fail until BE-01→04 implemented."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.auth.verification import create_verification_code
from app.models import AuditLog, DeliveryJob, DeliveryStatus

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _setup_draft_delivery_job(client: TestClient) -> str:
    """Create lead → lifecycle → run sales agent → approve → return delivery_job_id."""
    email = "delivery-exec@example.com"
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()

    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/api/v1/leads", json={
        "owner_email": email, "company": "发送执行测试公司", "contact_name": "孙总",
        "contact_method": "email", "industry": "物流科技",
        "problem": "发送执行测试需要一段足够长的客户业务问题描述文本",
        "desired_outcome": "智能调度系统", "company_size": "100-200",
        "budget_range": "8-15w", "timeline": "2个月",
        "honeypot": "", "submitted_after_ms": 2000,
    }, headers=headers)
    opp_id = r.json()["lifecycle"]["opportunity"]["id"]

    client.post("/api/v1/admin/agent-runs/sales-reply",
                json={"opportunity_id": opp_id}, headers=ADMIN)

    r = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN)
    decisions = r.json()["opportunity"]["decisions"]
    waiting = [d for d in decisions if d["status"] == "waiting"]
    assert waiting, "Need a waiting decision to approve"
    client.post(f"/api/v1/decisions/{waiting[0]['id']}/approve", json={}, headers=ADMIN)

    db2 = SessionLocal()
    job = db2.query(DeliveryJob).order_by(DeliveryJob.created_at.desc()).first()
    job_id = job.id
    db2.close()
    return job_id


class TestDeliveryJobExecution:
    def test_mark_sent_updates_delivery_job_status(self, client: TestClient):
        init_db()
        job_id = _setup_draft_delivery_job(client)

        r = client.post(f"/api/v1/delivery-jobs/{job_id}/mark-sent",
                        json={"operator_note": "已通过邮件发送"}, headers=ADMIN)
        assert r.status_code == 200
        data = r.json()
        assert "delivery_job" in data
        assert data["delivery_job"]["status"] == "sent"

    def test_mark_sent_sets_sent_at(self, client: TestClient):
        init_db()
        job_id = _setup_draft_delivery_job(client)

        r = client.post(f"/api/v1/delivery-jobs/{job_id}/mark-sent",
                        json={"operator_note": "测试"}, headers=ADMIN)
        assert r.status_code == 200
        assert r.json()["delivery_job"]["sent_at"] is not None

    def test_mark_sent_writes_audit_log(self, client: TestClient):
        init_db()
        job_id = _setup_draft_delivery_job(client)

        r = client.post(f"/api/v1/delivery-jobs/{job_id}/mark-sent",
                        json={"operator_note": "已通过微信发送给客户"}, headers=ADMIN)
        assert r.status_code == 200

        db = SessionLocal()
        logs = db.query(AuditLog).filter(AuditLog.action == "delivery_job_marked_sent").all()
        assert len(logs) >= 1
        details = logs[-1].details_json or {}
        assert details.get("delivery_job_id") == job_id
        assert details.get("operator_note") == "已通过微信发送给客户"

    def test_mark_sent_missing_job_returns_404(self, client: TestClient):
        init_db()
        r = client.post("/api/v1/delivery-jobs/nonexistent-id/mark-sent",
                        json={}, headers=ADMIN)
        assert r.status_code == 404

    def test_mark_sent_twice_returns_409(self, client: TestClient):
        init_db()
        job_id = _setup_draft_delivery_job(client)

        r = client.post(f"/api/v1/delivery-jobs/{job_id}/mark-sent",
                        json={"operator_note": "第一次"}, headers=ADMIN)
        assert r.status_code == 200

        r = client.post(f"/api/v1/delivery-jobs/{job_id}/mark-sent",
                        json={"operator_note": "第二次"}, headers=ADMIN)
        assert r.status_code == 409

    def test_cockpit_reflects_sent_delivery_job(self, client: TestClient):
        init_db()
        job_id = _setup_draft_delivery_job(client)

        # Find the opportunity from the delivery job
        db = SessionLocal()
        job = db.query(DeliveryJob).filter(DeliveryJob.id == job_id).first()
        # Get opportunity_id via artifact
        from app.models import Artifact
        art = db.query(Artifact).filter(Artifact.id == job.artifact_id).first()
        opp_id = art.opportunity_id if art else None
        db.close()
        assert opp_id, "Should have an opportunity for this delivery job"

        # Mark sent
        r = client.post(f"/api/v1/delivery-jobs/{job_id}/mark-sent",
                        json={"operator_note": "已发送"}, headers=ADMIN)
        assert r.status_code == 200

        # Cockpit should show sent status
        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/cockpit", headers=ADMIN)
        jobs = r.json()["delivery_jobs"]
        sent_job = next((j for j in jobs if j["id"] == job_id), None)
        assert sent_job is not None
        assert sent_job["status"] == "sent"
        assert sent_job["sent_at"] is not None

    def test_mark_sent_requires_draft_status(self, client: TestClient):
        """BE-03: non-draft statuses (failed, cancelled, etc.) return 409."""
        init_db()
        job_id = _setup_draft_delivery_job(client)

        # Manually set job to failed, simulating a non-draft state
        db = SessionLocal()
        job = db.query(DeliveryJob).filter(DeliveryJob.id == job_id).first()
        job.status = DeliveryStatus.failed
        db.commit()
        db.close()

        r = client.post(f"/api/v1/delivery-jobs/{job_id}/mark-sent",
                        json={"operator_note": "尝试对 failed 状态标记"}, headers=ADMIN)
        assert r.status_code == 409
