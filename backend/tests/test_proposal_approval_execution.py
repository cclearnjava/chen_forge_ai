"""BE-05: Proposal approval execution tests — TDD-first."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.auth.verification import create_verification_code
from app.models import AuditLog, Decision, DecisionStatus, DeliveryJob, Message, Opportunity, OpportunityStage

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _setup_proposal_decision(client: TestClient) -> str:
    """Create lead → lifecycle → generate proposal draft → return decision_id."""
    email = "proposal-approval@example.com"
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()

    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/api/v1/leads", json={
        "owner_email": email, "company": "提案审批测试公司", "contact_name": "郑总",
        "contact_method": "email", "industry": "教育科技",
        "problem": "提案审批测试需要一段足够长的客户业务问题描述",
        "desired_outcome": "智能评估系统", "company_size": "50-200",
        "budget_range": "5-10w", "timeline": "3个月",
        "honeypot": "", "submitted_after_ms": 2000,
    }, headers=headers)
    opp_id = r.json()["lifecycle"]["opportunity"]["id"]

    r = client.post("/api/v1/admin/agent-runs/proposal-draft",
                    json={"opportunity_id": opp_id}, headers=ADMIN)
    assert r.status_code == 200

    r2 = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN)
    decisions = r2.json()["opportunity"]["decisions"]
    waiting = [d for d in decisions if d["status"] == "waiting"]
    assert waiting, "Expected waiting proposal decision"
    return waiting[0]["id"]


def _setup_customer_reply_decision(client: TestClient) -> str:
    """Create lead → lifecycle → run sales agent → return waiting decision_id."""
    email = "cr-approval@example.com"
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()

    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/api/v1/leads", json={
        "owner_email": email, "company": "CR回归测试公司", "contact_name": "王总",
        "contact_method": "email", "industry": "物流科技",
        "problem": "客户回复审批回归测试需要一段足够长的描述文本",
        "desired_outcome": "智能调度", "company_size": "100-200",
        "budget_range": "8-15w", "timeline": "2个月",
        "honeypot": "", "submitted_after_ms": 2000,
    }, headers=headers)
    opp_id = r.json()["lifecycle"]["opportunity"]["id"]

    client.post("/api/v1/admin/agent-runs/sales-reply",
                json={"opportunity_id": opp_id}, headers=ADMIN)

    r2 = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN)
    decisions = r2.json()["opportunity"]["decisions"]
    waiting = [d for d in decisions if d["status"] == "waiting"]
    assert waiting, "Expected waiting customer reply decision"
    return waiting[0]["id"]


class TestProposalApprovalExecution:
    def test_approve_proposal_sets_decision_approved(self, client: TestClient):
        init_db()
        dec_id = _setup_proposal_decision(client)

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200
        db = SessionLocal()
        dec = db.query(Decision).filter(Decision.id == dec_id).one()
        assert dec.status == DecisionStatus.approved

    def test_approve_proposal_moves_opportunity_to_proposal_stage(self, client: TestClient):
        init_db()
        dec_id = _setup_proposal_decision(client)

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200

        db = SessionLocal()
        dec = db.query(Decision).filter(Decision.id == dec_id).first()
        opp = db.query(Opportunity).filter(Opportunity.id == dec.opportunity_id).one()
        assert opp.stage == OpportunityStage.proposal

    def test_approve_proposal_updates_next_step(self, client: TestClient):
        init_db()
        dec_id = _setup_proposal_decision(client)

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200

        db = SessionLocal()
        dec = db.query(Decision).filter(Decision.id == dec_id).first()
        opp = db.query(Opportunity).filter(Opportunity.id == dec.opportunity_id).one()
        assert opp.next_step == "Review approved proposal with customer"

    def test_approve_proposal_writes_audit_log(self, client: TestClient):
        init_db()
        dec_id = _setup_proposal_decision(client)

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200

        db = SessionLocal()
        logs = db.query(AuditLog).filter(AuditLog.action == "proposal_approved").all()
        assert len(logs) >= 1
        details = logs[-1].details_json or {}
        assert details.get("artifact_type") == "proposal_draft"

    def test_approve_proposal_does_not_create_delivery_job(self, client: TestClient):
        init_db()
        dec_id = _setup_proposal_decision(client)

        db = SessionLocal()
        before = db.query(DeliveryJob).count()

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200

        after = db.query(DeliveryJob).count()
        assert after == before

    def test_approve_proposal_does_not_create_message(self, client: TestClient):
        init_db()
        dec_id = _setup_proposal_decision(client)

        db = SessionLocal()
        before = db.query(Message).count()

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200

        after = db.query(Message).count()
        assert after == before

    def test_approve_proposal_twice_returns_409(self, client: TestClient):
        init_db()
        dec_id = _setup_proposal_decision(client)

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 409

    def test_customer_reply_approval_still_creates_delivery_job(self, client: TestClient):
        """BE-04: regression — customer reply approval must still work."""
        init_db()
        dec_id = _setup_customer_reply_decision(client)

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200

        db = SessionLocal()
        dec = db.query(Decision).filter(Decision.id == dec_id).first()
        jobs = db.query(DeliveryJob).filter(DeliveryJob.artifact_id == dec.artifact_id).all()
        assert len(jobs) >= 1
