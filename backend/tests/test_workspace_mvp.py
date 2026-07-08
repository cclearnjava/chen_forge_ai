"""BE-11: Workspace MVP regression tests."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.auth.verification import create_verification_code
from app.models import (
    AgentRun, Artifact, AuditLog, Customer, Decision, DeliveryJob, Lead,
    Message, Opportunity, Workspace,
)

ADMIN = {"Authorization": "Bearer admin-dev-token"}


class TestWorkspaceMvp:
    def test_default_workspace_is_created_once(self, client: TestClient):
        init_db()
        db = SessionLocal()
        ws1 = db.query(Workspace).filter(Workspace.slug == "chenforge-ai-consulting").first()
        assert ws1 is not None
        ws2 = db.query(Workspace).filter(Workspace.is_default == True).first()
        assert ws2 is not None
        assert ws1.id == ws2.id
        from app.services.workspace import get_or_create_default_workspace
        ws3 = get_or_create_default_workspace(db)
        assert ws3.id == ws1.id
        db.close()

    def test_current_workspace_api_returns_default_workspace(self, client: TestClient):
        init_db()
        r = client.get("/api/v1/admin/workspace/current", headers=ADMIN)
        assert r.status_code == 200
        data = r.json()
        assert data["slug"] == "chenforge-ai-consulting"
        assert data["is_default"] is True

    def test_current_workspace_api_requires_admin(self, client: TestClient):
        init_db()
        r = client.get("/api/v1/admin/workspace/current")
        assert r.status_code in (401, 403)

    def test_lead_lifecycle_records_have_workspace_id(self, client: TestClient):
        init_db()
        email = "ws-lifecycle@example.com"
        db = SessionLocal()
        code = create_verification_code(db, email)
        db.close()
        r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = client.post("/api/v1/leads", json={
            "owner_email": email, "company": "WS测试", "contact_name": "测试",
            "contact_method": "email", "industry": "科技",
            "problem": "Workspace测试需要一段足够长的业务问题描述文本",
            "desired_outcome": "测试", "company_size": "10-50", "budget_range": "1-3w",
            "timeline": "1个月", "honeypot": "", "submitted_after_ms": 2000,
        }, headers=h)
        assert r.status_code == 201
        db2 = SessionLocal()
        lead_id = r.json()["lead"]["id"]
        lead = db2.query(Lead).filter(Lead.id == lead_id).first()
        assert lead.workspace_id is not None
        cust = db2.query(Customer).filter(Customer.source_lead_id == lead_id).first()
        assert cust is not None and cust.workspace_id is not None
        opp = db2.query(Opportunity).filter(Opportunity.lead_id == lead_id).first()
        assert opp is not None and opp.workspace_id is not None
        db2.close()

    def test_sales_reply_workflow_records_have_workspace_id(self, client: TestClient):
        init_db()
        email = "ws-sales@example.com"
        db = SessionLocal()
        code = create_verification_code(db, email)
        db.close()
        r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = client.post("/api/v1/leads", json={
            "owner_email": email, "company": "WSSales测试", "contact_name": "测试",
            "contact_method": "email", "industry": "科技",
            "problem": "Sales Reply workspace测试需要足够长的业务描述",
            "desired_outcome": "测试", "company_size": "10-50", "budget_range": "1-3w",
            "timeline": "1个月", "honeypot": "", "submitted_after_ms": 2000,
        }, headers=h)
        opp_id = r.json()["lifecycle"]["opportunity"]["id"]
        client.post("/api/v1/admin/agent-runs/sales-reply", json={"opportunity_id": opp_id}, headers=ADMIN)
        db2 = SessionLocal()
        runs = db2.query(AgentRun).filter(AgentRun.opportunity_id == opp_id).order_by(AgentRun.created_at.desc()).all()
        assert any(r.workspace_id is not None for r in runs), "At least one recent AgentRun must have workspace_id"
        arts = db2.query(Artifact).filter(Artifact.opportunity_id == opp_id).order_by(Artifact.created_at.desc()).all()
        assert any(a.workspace_id is not None for a in arts), "At least one recent Artifact must have workspace_id"
        decs = db2.query(Decision).filter(Decision.opportunity_id == opp_id).order_by(Decision.created_at.desc()).all()
        assert any(d.workspace_id is not None for d in decs), "At least one recent Decision must have workspace_id"
        db2.close()

    def test_delivery_mark_sent_records_have_workspace_id(self, client: TestClient):
        init_db()
        email = "ws-delivery@example.com"
        db = SessionLocal()
        code = create_verification_code(db, email)
        db.close()
        r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = client.post("/api/v1/leads", json={
            "owner_email": email, "company": "WSDelivery测试", "contact_name": "测试",
            "contact_method": "email", "industry": "科技",
            "problem": "Delivery workspace测试需要足够长的业务描述",
            "desired_outcome": "测试", "company_size": "10-50", "budget_range": "1-3w",
            "timeline": "1个月", "honeypot": "", "submitted_after_ms": 2000,
        }, headers=h)
        opp_id = r.json()["lifecycle"]["opportunity"]["id"]
        client.post("/api/v1/admin/agent-runs/sales-reply", json={"opportunity_id": opp_id}, headers=ADMIN)
        r2 = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN)
        w = [d for d in r2.json()["opportunity"]["decisions"] if d["status"] == "waiting"]
        client.post(f"/api/v1/decisions/{w[0]['id']}/approve", json={}, headers=ADMIN)
        db2 = SessionLocal()
        job = db2.query(DeliveryJob).order_by(DeliveryJob.created_at.desc()).first()
        assert job is not None and job.workspace_id is not None
        msg = db2.query(Message).filter(Message.source == "delivery").order_by(Message.created_at.desc()).first()
        assert msg is not None and msg.workspace_id is not None
        log = db2.query(AuditLog).filter(AuditLog.action == "decision_approved").order_by(AuditLog.created_at.desc()).first()
        assert log is not None
        db2.close()
