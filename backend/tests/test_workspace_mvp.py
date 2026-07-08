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
        assert runs and all(r.workspace_id is not None for r in runs), "All AgentRuns must have workspace_id"
        arts = db2.query(Artifact).filter(Artifact.opportunity_id == opp_id).order_by(Artifact.created_at.desc()).all()
        assert arts and all(a.workspace_id is not None for a in arts), "All Artifacts must have workspace_id"
        decs = db2.query(Decision).filter(Decision.opportunity_id == opp_id).order_by(Decision.created_at.desc()).all()
        assert decs and all(d.workspace_id is not None for d in decs), "All Decisions must have workspace_id"
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

    def test_admin_list_excludes_other_workspace_data(self, client: TestClient):
        init_db()
        db = SessionLocal()
        ws2 = Workspace(slug="other-workspace", name="Other WS", is_default=False)
        db.add(ws2)
        db.commit()
        cust2 = Customer(workspace_id=ws2.id, name="WS2 Customer", owner_email="ws2@test.com")
        db.add(cust2)
        db.commit()
        db.close()
        r = client.get("/api/v1/admin/customers", headers=ADMIN)
        names = [c["name"] for c in r.json()["items"]]
        assert "WS2 Customer" not in names

    def test_admin_detail_returns_404_for_other_workspace(self, client: TestClient):
        init_db()
        db = SessionLocal()
        ws2 = Workspace(slug="other-ws-2", name="Other WS 2", is_default=False)
        db.add(ws2)
        db.commit()
        cust2 = Customer(workspace_id=ws2.id, name="WS2 Detail", owner_email="ws2d@test.com")
        db.add(cust2)
        db.commit()
        cust2_id = cust2.id
        db.close()
        r = client.get(f"/api/v1/admin/customers/{cust2_id}", headers=ADMIN)
        assert r.status_code == 404


    def test_opportunity_detail_returns_404_for_other_workspace(self, client: TestClient):
        init_db()
        db = SessionLocal()
        ws2 = Workspace(slug="other-ws-opp2", name="Other", is_default=False)
        db.add(ws2); db.commit()
        opp2 = Opportunity(workspace_id=ws2.id, customer_id="x", title="WS2 Opp", stage="lead")
        db.add(opp2); db.commit()
        opp2_id = opp2.id; db.close()
        r = client.get(f"/api/v1/admin/opportunities/{opp2_id}", headers=ADMIN)
        assert r.status_code == 404

    def test_conversation_messages_returns_404_for_other_workspace(self, client: TestClient):
        init_db()
        db = SessionLocal()
        ws2 = Workspace(slug="other-ws-conv2", name="Other", is_default=False)
        db.add(ws2); db.commit()
        from app.models import Conversation as CV, Customer as CU
        c2 = CU(workspace_id=ws2.id, name="W2", owner_email="w@t.com")
        db.add(c2); db.commit()
        cv2 = CV(workspace_id=ws2.id, customer_id=c2.id, title="W2C", channel="web")
        db.add(cv2); db.commit()
        cv2_id = cv2.id; db.close()
        r = client.get(f"/api/v1/admin/conversations/{cv2_id}/messages", headers=ADMIN)
        assert r.status_code == 404

    def test_decision_approve_returns_404_for_other_workspace(self, client: TestClient):
        init_db()
        db = SessionLocal()
        ws2 = Workspace(slug="other-ws-dec", name="Other", is_default=False)
        db.add(ws2); db.commit()
        dec2 = Decision(workspace_id=ws2.id, question="test", status="waiting")
        db.add(dec2); db.commit()
        dec2_id = dec2.id; db.close()
        r = client.post(f"/api/v1/decisions/{dec2_id}/approve", json={}, headers=ADMIN)
        assert r.status_code == 404

