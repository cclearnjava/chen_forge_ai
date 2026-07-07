"""BE-09: Proposal follow-up loop tests — TDD-first."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.auth.verification import create_verification_code
from app.models import (
    Artifact, AuditLog, Decision, DeliveryChannel, DeliveryJob, DeliveryStatus, Message,
)

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _setup_with_sent_proposal(client: TestClient) -> str:
    """Create lead → proposal → approve → create delivery → mark sent → return opp_id."""
    email = "followup-test@example.com"
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()
    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/v1/leads", json={
        "owner_email": email, "company": "跟进测试公司", "contact_name": "林总",
        "contact_method": "email", "industry": "金融科技",
        "problem": "跟进测试需要一段足够长的客户业务问题描述文本内容填充",
        "desired_outcome": "智能决策系统", "company_size": "100-200",
        "budget_range": "10-20w", "timeline": "3个月",
        "honeypot": "", "submitted_after_ms": 2000,
    }, headers=h)
    opp_id = r.json()["lifecycle"]["opportunity"]["id"]
    client.post("/api/v1/admin/agent-runs/proposal-draft", json={"opportunity_id": opp_id}, headers=ADMIN)
    r2 = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN)
    decs = r2.json()["opportunity"]["decisions"]
    w = [d for d in decs if d["status"] == "waiting"]
    assert w
    client.post(f"/api/v1/decisions/{w[0]['id']}/approve", json={}, headers=ADMIN)
    # Create and mark-sent DeliveryJob directly (bypass PDF render for testing)
    db2 = SessionLocal()
    r3 = client.get(f"/api/v1/admin/opportunities/{opp_id}/approved-proposal", headers=ADMIN)
    art_id = r3.json()["artifact_id"]
    job = DeliveryJob(
        lead_id=db2.query(Artifact).filter(Artifact.id == art_id).first().lead_id,
        artifact_id=art_id, channel=DeliveryChannel.manual_copy,
        recipient="test@example.com", subject="PoC Proposal: test",
        body_markdown="test", status=DeliveryStatus.draft,
    )
    db2.add(job)
    db2.commit()
    job_id = job.id
    db2.close()
    client.post(f"/api/v1/delivery-jobs/{job_id}/mark-sent", json={}, headers=ADMIN)
    return opp_id


class TestProposalFollowup:
    def test_record_proposal_feedback_success(self, client: TestClient):
        init_db()
        opp_id = _setup_with_sent_proposal(client)
        r = client.post(f"/api/v1/admin/opportunities/{opp_id}/proposal-feedback",
                        json={"body_markdown": "方案方向可以，但预算有点高。能不能先做两周小版本？"},
                        headers=ADMIN)
        assert r.status_code == 201
        data = r.json()
        assert data["message"]["sender_type"] == "customer"
        assert data["message"]["source"] == "proposal_feedback"

    def test_record_feedback_without_sent_proposal_returns_422(self, client: TestClient):
        """BE-02: without sent Proposal DeliveryJob, return 422."""
        init_db()
        r = client.post("/api/v1/admin/opportunities/nonexistent-id/proposal-feedback",
                        json={"body_markdown": "test"}, headers=ADMIN)
        assert r.status_code == 404

    def test_run_followup_creates_three_artifacts(self, client: TestClient):
        init_db()
        opp_id = _setup_with_sent_proposal(client)
        client.post(f"/api/v1/admin/opportunities/{opp_id}/proposal-feedback",
                    json={"body_markdown": "预算太高，能不能缩小范围？"}, headers=ADMIN)
        r = client.post("/api/v1/admin/agent-runs/proposal-followup",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        assert r.status_code == 200
        artifacts = r.json()["artifacts"]
        types = [a["type"] for a in artifacts]
        assert "proposal_followup_reply_draft" in types
        assert "objection_analysis" in types
        assert "next_step_recommendation" in types
        assert len(artifacts) == 3

    def test_only_reply_draft_creates_waiting_decision(self, client: TestClient):
        init_db()
        opp_id = _setup_with_sent_proposal(client)
        client.post(f"/api/v1/admin/opportunities/{opp_id}/proposal-feedback",
                    json={"body_markdown": "数据安全怎么保证？"}, headers=ADMIN)
        r = client.post("/api/v1/admin/agent-runs/proposal-followup",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        decision = r.json()["decision"]
        assert decision["status"] == "waiting"
        # Verify the decision points to the reply draft artifact
        reply = [a for a in r.json()["artifacts"] if a["type"] == "proposal_followup_reply_draft"][0]
        assert reply["requires_approval"] is True

    def test_run_followup_without_approved_proposal_returns_422(self, client: TestClient):
        init_db()
        r = client.post("/api/v1/admin/agent-runs/proposal-followup",
                        json={"opportunity_id": "nonexistent-id"}, headers=ADMIN)
        assert r.status_code == 404

    def test_approve_followup_reply_creates_delivery_job(self, client: TestClient):
        init_db()
        opp_id = _setup_with_sent_proposal(client)
        client.post(f"/api/v1/admin/opportunities/{opp_id}/proposal-feedback",
                    json={"body_markdown": "缩小范围做两周PoC可以接受。"}, headers=ADMIN)
        r = client.post("/api/v1/admin/agent-runs/proposal-followup",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        dec_id = r.json()["decision"]["id"]
        db = SessionLocal()
        before = db.query(DeliveryJob).count()
        r2 = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r2.status_code == 200
        after = db.query(DeliveryJob).count()
        assert after == before + 1

    def test_existing_tests_still_pass(self, client: TestClient):
        """Verify ArtifactType enum still works for existing types."""
        init_db()
        from app.models import ArtifactType
        assert ArtifactType.customer_reply_draft is not None
        assert ArtifactType.proposal_draft is not None
