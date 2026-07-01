"""BE-07: Decision approval execution tests — TDD-first, expected to fail until BE-01→06 implemented."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.auth.verification import create_verification_code
from app.models import (
    AgentRun, Artifact, AuditLog, Decision, DecisionStatus,
    DeliveryJob, Lead, Message, Opportunity,
)

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _setup_lead_and_opportunity(client: TestClient) -> str:
    """Create a lead → lifecycle → return opportunity_id."""
    email = "approval-test@example.com"
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()

    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/api/v1/leads", json={
        "owner_email": email, "company": "审批测试公司", "contact_name": "赵总",
        "contact_method": "email", "industry": "金融科技",
        "problem": "审批执行闭环测试需要的十个字以上的业务问题描述",
        "desired_outcome": "智能审批引擎", "company_size": "50-200",
        "budget_range": "5-10w", "timeline": "2个月",
        "honeypot": "", "submitted_after_ms": 2000,
    }, headers=headers)

    lifecycle = r.json()["lifecycle"]
    return lifecycle["opportunity"]["id"]


def _run_sales_agent(client: TestClient, opportunity_id: str) -> dict:
    """Trigger sales reply workflow and return response JSON."""
    r = client.post(
        "/api/v1/admin/agent-runs/sales-reply",
        json={"opportunity_id": opportunity_id},
        headers=ADMIN,
    )
    assert r.status_code == 200
    return r.json()


def _get_waiting_decision_id(client: TestClient, opportunity_id: str) -> str:
    """Extract the latest waiting decision ID from opportunity detail."""
    r = client.get(f"/api/v1/admin/opportunities/{opportunity_id}", headers=ADMIN)
    decisions = r.json()["opportunity"]["decisions"]
    waiting = [d for d in decisions if d["status"] == "waiting"]
    assert waiting, "Expected at least one waiting decision"
    return waiting[0]["id"]


class TestDecisionApprovalExecution:
    def test_approve_creates_delivery_job(self, client: TestClient):
        """BE-02: approve creates a DeliveryJob pointing to the approved artifact."""
        init_db()
        opp_id = _setup_lead_and_opportunity(client)
        result = _run_sales_agent(client, opp_id)
        dec_id = _get_waiting_decision_id(client, opp_id)

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200

        db = SessionLocal()
        jobs = db.query(DeliveryJob).all()
        assert len(jobs) >= 1
        draft_artifact_id = result["artifacts"][0]["id"]
        assert jobs[-1].artifact_id == draft_artifact_id

    def test_approve_writes_message(self, client: TestClient):
        """BE-03: approve writes a Message to the Opportunity's conversation."""
        init_db()
        opp_id = _setup_lead_and_opportunity(client)
        result = _run_sales_agent(client, opp_id)
        dec_id = _get_waiting_decision_id(client, opp_id)

        # Count messages before
        db = SessionLocal()
        before = db.query(Message).count()

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200

        after = db.query(Message).count()
        assert after == before + 1
        last_msg = db.query(Message).order_by(Message.created_at.desc()).first()
        assert last_msg.source == "delivery"
        assert last_msg.body_markdown == result["artifacts"][0]["content_markdown"]

    def test_approve_writes_audit_log(self, client: TestClient):
        """BE-04: approve writes a decision_approved AuditLog."""
        init_db()
        opp_id = _setup_lead_and_opportunity(client)
        _run_sales_agent(client, opp_id)
        dec_id = _get_waiting_decision_id(client, opp_id)

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200

        db = SessionLocal()
        logs = db.query(AuditLog).filter(AuditLog.action == "decision_approved").all()
        assert len(logs) >= 1
        assert "decision_id" in (logs[-1].details_json or {})

    def test_approve_sets_decision_status(self, client: TestClient):
        """BE-01: approve sets Decision.status to approved."""
        init_db()
        opp_id = _setup_lead_and_opportunity(client)
        _run_sales_agent(client, opp_id)
        dec_id = _get_waiting_decision_id(client, opp_id)

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200

        db = SessionLocal()
        dec = db.query(Decision).filter(Decision.id == dec_id).one()
        assert dec.status == DecisionStatus.approved

    def test_request_rewrite_does_not_create_delivery_job(self, client: TestClient):
        """BE-05: request rewrite does NOT create DeliveryJob."""
        init_db()
        opp_id = _setup_lead_and_opportunity(client)
        _run_sales_agent(client, opp_id)
        dec_id = _get_waiting_decision_id(client, opp_id)

        db = SessionLocal()
        before = db.query(DeliveryJob).count()

        r = client.post(f"/api/v1/decisions/{dec_id}/request-rewrite", json={}, headers=ADMIN)
        assert r.status_code == 200

        after = db.query(DeliveryJob).count()
        assert after == before

    def test_request_rewrite_does_not_create_message(self, client: TestClient):
        """BE-05: request rewrite does NOT create Message."""
        init_db()
        opp_id = _setup_lead_and_opportunity(client)
        _run_sales_agent(client, opp_id)
        dec_id = _get_waiting_decision_id(client, opp_id)

        db = SessionLocal()
        before = db.query(Message).count()

        r = client.post(f"/api/v1/decisions/{dec_id}/request-rewrite", json={}, headers=ADMIN)
        assert r.status_code == 200

        after = db.query(Message).count()
        assert after == before

    def test_request_rewrite_writes_audit_log(self, client: TestClient):
        """BE-05: request rewrite writes decision_rewrite_requested AuditLog."""
        init_db()
        opp_id = _setup_lead_and_opportunity(client)
        _run_sales_agent(client, opp_id)
        dec_id = _get_waiting_decision_id(client, opp_id)

        r = client.post(f"/api/v1/decisions/{dec_id}/request-rewrite", json={}, headers=ADMIN)
        assert r.status_code == 200

        db = SessionLocal()
        logs = db.query(AuditLog).filter(AuditLog.action == "decision_rewrite_requested").all()
        assert len(logs) >= 1

    def test_double_approve_returns_409(self, client: TestClient):
        """BE-01: repeating approve on non-waiting decision returns 409."""
        init_db()
        opp_id = _setup_lead_and_opportunity(client)
        _run_sales_agent(client, opp_id)
        dec_id = _get_waiting_decision_id(client, opp_id)

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 200

        r = client.post(f"/api/v1/decisions/{dec_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 409
