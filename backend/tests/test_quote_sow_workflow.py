"""BE-08: Quote/SOW workflow tests — TDD-first."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.auth.verification import create_verification_code
from app.models import (
    Artifact, AuditLog, Decision, DeliveryChannel, DeliveryJob, DeliveryStatus,
    Message, Opportunity, OpportunityStage,
)

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _setup_with_sent_proposal_and_feedback(client: TestClient) -> str:
    """Create lead → proposal → approve → sent → feedback → return opp_id."""
    email = "quotesow-test@example.com"
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()
    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/v1/leads", json={
        "owner_email": email, "company": "报价SOW测试公司", "contact_name": "杨总",
        "contact_method": "email", "industry": "教育科技",
        "problem": "报价SOW测试需要一段足够长的客户业务问题描述文本内容填充",
        "desired_outcome": "智能教学系统", "company_size": "50-200",
        "budget_range": "10-20w", "timeline": "3个月",
        "honeypot": "", "submitted_after_ms": 2000,
    }, headers=h)
    opp_id = r.json()["lifecycle"]["opportunity"]["id"]
    client.post("/api/v1/admin/agent-runs/proposal-draft", json={"opportunity_id": opp_id}, headers=ADMIN)
    r2 = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN)
    decs = r2.json()["opportunity"]["decisions"]
    w = [d for d in decs if d["status"] == "waiting"]
    client.post(f"/api/v1/decisions/{w[0]['id']}/approve", json={}, headers=ADMIN)
    # Create and sent DeliveryJob directly (bypass PDF render)
    r3 = client.get(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal", headers=ADMIN)
    art_id = r3.json()["artifact_id"]
    db2 = SessionLocal()
    art = db2.query(Artifact).filter(Artifact.id == art_id).first()
    job = DeliveryJob(
        lead_id=art.lead_id if art else None, artifact_id=art_id,
        channel=DeliveryChannel.manual_copy, recipient="test@example.com",
        subject="PoC Proposal: test", body_markdown="test", status=DeliveryStatus.draft,
    )
    db2.add(job)
    db2.commit()
    db2.close()
    client.post(f"/api/v1/delivery-jobs/{job.id}/mark-sent", json={}, headers=ADMIN)
    # Record proposal feedback
    client.post(f"/api/v1/admin/opportunities/{opp_id}/proposal-feedback",
                json={"body_markdown": "方向可以，预算控制在 5 万以内做两周 PoC。"}, headers=ADMIN)
    return opp_id


class TestQuoteSowWorkflow:
    def test_generates_three_artifacts(self, client: TestClient):
        init_db()
        opp_id = _setup_with_sent_proposal_and_feedback(client)
        r = client.post("/api/v1/admin/agent-runs/quote-sow",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        assert r.status_code == 200
        artifacts = r.json()["artifacts"]
        types = [a["type"] for a in artifacts]
        assert "quote_draft" in types
        assert "sow_draft" in types
        assert "commercial_review" in types
        assert len(artifacts) == 3

    def test_quote_and_sow_require_approval(self, client: TestClient):
        init_db()
        opp_id = _setup_with_sent_proposal_and_feedback(client)
        r = client.post("/api/v1/admin/agent-runs/quote-sow",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        for a in r.json()["artifacts"]:
            if a["type"] in ("quote_draft", "sow_draft"):
                assert a["requires_approval"] is True
            elif a["type"] == "commercial_review":
                assert a["requires_approval"] is False

    def test_creates_waiting_decision(self, client: TestClient):
        init_db()
        opp_id = _setup_with_sent_proposal_and_feedback(client)
        r = client.post("/api/v1/admin/agent-runs/quote-sow",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        dec = r.json()["decision"]
        assert dec["status"] == "waiting"

    def test_missing_opportunity_returns_404(self, client: TestClient):
        init_db()
        r = client.post("/api/v1/admin/agent-runs/quote-sow",
                        json={"opportunity_id": "nonexistent-id"}, headers=ADMIN)
        assert r.status_code == 404

    def test_repeat_creates_new_versions(self, client: TestClient):
        init_db()
        opp_id = _setup_with_sent_proposal_and_feedback(client)
        r1 = client.post("/api/v1/admin/agent-runs/quote-sow",
                         json={"opportunity_id": opp_id}, headers=ADMIN)
        r2 = client.post("/api/v1/admin/agent-runs/quote-sow",
                         json={"opportunity_id": opp_id}, headers=ADMIN)
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["artifacts"][0]["id"] != r2.json()["artifacts"][0]["id"]

    def test_approve_quote_advances_opportunity_stage(self, client: TestClient):
        init_db()
        opp_id = _setup_with_sent_proposal_and_feedback(client)
        r = client.post("/api/v1/admin/agent-runs/quote-sow",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        dec_id = r.json()["decision"]["id"]
        r2 = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r2.status_code == 200
        db = SessionLocal()
        opp = db.query(Opportunity).filter(Opportunity.id == opp_id).one()
        assert opp.stage == OpportunityStage.negotiation

    def test_approve_quote_does_not_create_delivery_job(self, client: TestClient):
        init_db()
        opp_id = _setup_with_sent_proposal_and_feedback(client)
        r = client.post("/api/v1/admin/agent-runs/quote-sow",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        db = SessionLocal()
        before = db.query(DeliveryJob).count()
        client.post(f"/api/v1/decisions/{r.json()['decision']['id']}/approve", json={}, headers=ADMIN)
        after = db.query(DeliveryJob).count()
        assert after == before

    def test_approve_quote_does_not_create_message(self, client: TestClient):
        init_db()
        opp_id = _setup_with_sent_proposal_and_feedback(client)
        r = client.post("/api/v1/admin/agent-runs/quote-sow",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        db = SessionLocal()
        before = db.query(Message).count()
        client.post(f"/api/v1/decisions/{r.json()['decision']['id']}/approve", json={}, headers=ADMIN)
        after = db.query(Message).count()
        assert after == before

    def test_approve_quote_writes_audit_log(self, client: TestClient):
        init_db()
        opp_id = _setup_with_sent_proposal_and_feedback(client)
        r = client.post("/api/v1/admin/agent-runs/quote-sow",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        client.post(f"/api/v1/decisions/{r.json()['decision']['id']}/approve", json={}, headers=ADMIN)
        db = SessionLocal()
        logs = db.query(AuditLog).filter(AuditLog.action == "quote_sow_approved").all()
        assert len(logs) >= 1
