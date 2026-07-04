"""BE-T01→T04: Approved proposal query, JSON/PDF API, and side-effect tests."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.auth.verification import create_verification_code
from app.models import AuditLog, DeliveryJob, Message, Opportunity

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _setup_approved_proposal(client: TestClient) -> str:
    """Create lead → lifecycle → generate proposal → approve → return opportunity_id."""
    email = "pdf-export@example.com"
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()

    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/api/v1/leads", json={
        "owner_email": email, "company": "PDF导出测试公司", "contact_name": "冯总",
        "contact_method": "email", "industry": "金融科技",
        "problem": "PDF导出测试需要一段足够长的客户业务问题描述文本内容",
        "desired_outcome": "智能风控引擎", "company_size": "50-200",
        "budget_range": "8-15w", "timeline": "3个月",
        "honeypot": "", "submitted_after_ms": 2000,
    }, headers=headers)
    opp_id = r.json()["lifecycle"]["opportunity"]["id"]

    r = client.post("/api/v1/admin/agent-runs/proposal-draft",
                    json={"opportunity_id": opp_id}, headers=ADMIN)
    assert r.status_code == 200

    r2 = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN)
    decisions = r2.json()["opportunity"]["decisions"]
    waiting = [d for d in decisions if d["status"] == "waiting"]
    assert waiting
    client.post(f"/api/v1/decisions/{waiting[0]['id']}/approve", json={}, headers=ADMIN)

    return opp_id


class TestApprovedProposalQuery:
    def test_returns_latest_approved_proposal(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_proposal(client)

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal", headers=ADMIN)
        assert r.status_code == 200
        data = r.json()
        assert data["customer_name"] == "PDF导出测试公司"
        assert "markdown" in data
        assert data["artifact_id"] is not None
        assert data["decision_id"] is not None
        assert data["approved_at"] is not None

    def test_ignores_waiting_proposal(self, client: TestClient):
        """Only approved proposals are returned — waiting is ignored."""
        init_db()
        opp_id = _setup_approved_proposal(client)

        # Create a second proposal draft WITHOUT approving it
        client.post("/api/v1/admin/agent-runs/proposal-draft",
                    json={"opportunity_id": opp_id}, headers=ADMIN)

        # Should still return the approved one
        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal", headers=ADMIN)
        assert r.status_code == 200

    def test_returns_404_when_no_approved_proposal(self, client: TestClient):
        init_db()
        r = client.get("/api/v1/admin/opportunities/nonexistent-id/approved-proposal", headers=ADMIN)
        assert r.status_code == 404


class TestApprovedProposalJsonAPI:
    def test_json_api_returns_200_with_correct_fields(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_proposal(client)

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal", headers=ADMIN)
        assert r.status_code == 200
        data = r.json()
        assert "artifact_id" in data
        assert "decision_id" in data
        assert "markdown" in data
        assert "customer_name" in data
        assert "opportunity_title" in data

    def test_json_api_returns_404_without_approved_proposal(self, client: TestClient):
        init_db()
        r = client.get("/api/v1/admin/opportunities/nonexistent-id/approved-proposal", headers=ADMIN)
        assert r.status_code == 404


class TestApprovedProposalPdfAPI:
    def test_pdf_api_returns_pdf_content_type(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_proposal(client)

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal.pdf", headers=ADMIN)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"

    def test_pdf_api_returns_404_without_approved_proposal(self, client: TestClient):
        init_db()
        r = client.get("/api/v1/admin/opportunities/nonexistent-id/approved-proposal.pdf", headers=ADMIN)
        assert r.status_code == 404


class TestPdfSideEffects:
    def test_pdf_download_does_not_create_delivery_job(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_proposal(client)
        db = SessionLocal()
        before = db.query(DeliveryJob).count()

        client.get(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal.pdf", headers=ADMIN)
        after = db.query(DeliveryJob).count()
        assert after == before

    def test_pdf_download_does_not_create_message(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_proposal(client)
        db = SessionLocal()
        before = db.query(Message).count()

        client.get(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal.pdf", headers=ADMIN)
        after = db.query(Message).count()
        assert after == before

    def test_pdf_download_writes_audit_log(self, client: TestClient):
        init_db()
        opp_id = _setup_approved_proposal(client)

        client.get(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal.pdf", headers=ADMIN)

        db = SessionLocal()
        logs = db.query(AuditLog).filter(AuditLog.action == "approved_proposal_pdf_downloaded").all()
        assert len(logs) >= 1
        details = logs[-1].details_json or {}
        assert details.get("opportunity_id") == opp_id
