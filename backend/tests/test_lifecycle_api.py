from app.auth.verification import create_verification_code
from app.db import SessionLocal
from app.models import Lead
from app.services.customer_lifecycle import create_lifecycle_from_lead

ADMIN_TOKEN = "admin-dev-token"
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def _create_test_lead() -> dict:
    """Create a lead with lifecycle and return (lead_id, lifecycle_dict, auth_headers)."""
    db = SessionLocal()
    lead = Lead(
        owner_email="api-test@example.com",
        company="API测试公司",
        contact_name="张总",
        contact_method="email",
        industry="金融科技",
        problem="风控规则太多人工维护不过来了，需要AI自动优化",
        desired_outcome="智能风控规则引擎",
        company_size="50-200",
        budget_range="5-10w",
    )
    db.add(lead)
    db.commit()

    lifecycle = create_lifecycle_from_lead(db, lead.id)
    db.commit()
    db.close()
    return {"lead_id": lead.id, "lifecycle": lifecycle}


def _get_user_headers(email: str = "api-test@example.com") -> dict:
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()
    from starlette.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestCustomerAPI:
    def test_list_customers(self, client):
        _create_test_lead()
        r = client.get("/api/v1/admin/customers", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert "id" in data["items"][0]
        assert "name" in data["items"][0]
        assert "primary_contact" in data["items"][0]
        assert "opportunity_count" in data["items"][0]

    def test_list_customers_search(self, client):
        _create_test_lead()
        r = client.get("/api/v1/admin/customers?q=API测试", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert all("API测试" in c["name"] for c in data["items"] if data["items"])

        r = client.get("/api/v1/admin/customers?q=NONEXISTENT_XYZ", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_customer_detail(self, client):
        data = _create_test_lead()
        cust_id = data["lifecycle"]["customer"]["id"]
        r = client.get(f"/api/v1/admin/customers/{cust_id}", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        c = r.json()["customer"]
        assert c["name"] == "API测试公司"
        assert len(c["contacts"]) >= 1
        assert len(c["opportunities"]) >= 1
        assert len(c["recent_conversations"]) >= 1

    def test_customer_not_found(self, client):
        r = client.get("/api/v1/admin/customers/nonexistent-id", headers=ADMIN_HEADERS)
        assert r.status_code == 404

    def test_customers_require_admin(self, client):
        r = client.get("/api/v1/admin/customers")
        assert r.status_code == 401

        user_headers = _get_user_headers()
        r = client.get("/api/v1/admin/customers", headers=user_headers)
        assert r.status_code == 403


class TestOpportunityAPI:
    def test_list_opportunities(self, client):
        _create_test_lead()
        r = client.get("/api/v1/admin/opportunities", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        opp = data["items"][0]
        assert "title" in opp
        assert "stage" in opp
        assert "company_name" in opp

    def test_list_opportunities_filter_by_stage(self, client):
        _create_test_lead()
        r = client.get("/api/v1/admin/opportunities?stage=qualified", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        for opp in r.json()["items"]:
            assert opp["stage"] == "qualified"

    def test_list_opportunities_filter_invalid_stage_returns_422(self, client):
        r = client.get("/api/v1/admin/opportunities?stage=INVALID_STAGE", headers=ADMIN_HEADERS)
        assert r.status_code == 422

    def test_list_opportunities_search(self, client):
        _create_test_lead()
        r = client.get("/api/v1/admin/opportunities?q=风控", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        assert r.json()["total"] >= 1
        assert "风控" in r.json()["items"][0]["title"]

    def test_list_opportunities_search_by_company(self, client):
        _create_test_lead()
        r = client.get("/api/v1/admin/opportunities?q=API测试", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_opportunity_detail(self, client):
        data = _create_test_lead()
        opp_id = data["lifecycle"]["opportunity"]["id"]
        r = client.get(f"/api/v1/admin/opportunities/{opp_id}", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        opp = r.json()["opportunity"]
        assert opp["title"] is not None
        assert opp["stage"] == "qualified"
        assert opp["customer"] is not None
        assert opp["customer"]["name"] == "API测试公司"
        assert len(opp["recent_messages"]) >= 1
        assert opp["recent_messages"][0]["sender_type"] == "customer"

    def test_opportunity_update_stage_and_next_step(self, client):
        data = _create_test_lead()
        opp_id = data["lifecycle"]["opportunity"]["id"]
        r = client.patch(
            f"/api/v1/admin/opportunities/{opp_id}",
            json={"stage": "proposal", "next_step": "准备技术方案"},
            headers=ADMIN_HEADERS,
        )
        assert r.status_code == 200
        opp = r.json()["opportunity"]
        assert opp["stage"] == "proposal"
        assert opp["next_step"] == "准备技术方案"

    def test_opportunity_update_invalid_stage_returns_422(self, client):
        data = _create_test_lead()
        opp_id = data["lifecycle"]["opportunity"]["id"]
        r = client.patch(
            f"/api/v1/admin/opportunities/{opp_id}",
            json={"stage": "INVALID"},
            headers=ADMIN_HEADERS,
        )
        assert r.status_code == 422

    def test_opportunity_not_found(self, client):
        r = client.get("/api/v1/admin/opportunities/nonexistent-id", headers=ADMIN_HEADERS)
        assert r.status_code == 404

    def test_opportunities_require_admin(self, client):
        r = client.get("/api/v1/admin/opportunities")
        assert r.status_code == 401

        user_headers = _get_user_headers()
        r = client.get("/api/v1/admin/opportunities", headers=user_headers)
        assert r.status_code == 403


class TestConversationAPI:
    def test_list_messages(self, client):
        data = _create_test_lead()
        conv_id = data["lifecycle"]["conversation"]["id"]
        r = client.get(f"/api/v1/admin/conversations/{conv_id}/messages", headers=ADMIN_HEADERS)
        assert r.status_code == 200
        messages = r.json()["messages"]
        assert len(messages) >= 1
        assert messages[0]["sender_type"] == "customer"
        assert messages[0]["source"] == "lead_form"

    def test_create_owner_message(self, client):
        data = _create_test_lead()
        conv_id = data["lifecycle"]["conversation"]["id"]
        r = client.post(
            f"/api/v1/admin/conversations/{conv_id}/messages",
            json={"body_markdown": "张总好，已收到需求，我来跟进", "sender_type": "owner", "source": "manual"},
            headers=ADMIN_HEADERS,
        )
        assert r.status_code == 201
        msg = r.json()["message"]
        assert msg["sender_type"] == "owner"
        assert msg["body_markdown"] == "张总好，已收到需求，我来跟进"
        assert msg["id"] is not None

    def test_create_message_with_invalid_sender_type_returns_422(self, client):
        data = _create_test_lead()
        conv_id = data["lifecycle"]["conversation"]["id"]
        r = client.post(
            f"/api/v1/admin/conversations/{conv_id}/messages",
            json={"body_markdown": "test", "sender_type": "INVALID"},
            headers=ADMIN_HEADERS,
        )
        assert r.status_code == 422

    def test_conversation_not_found(self, client):
        r = client.get("/api/v1/admin/conversations/nonexistent-id/messages", headers=ADMIN_HEADERS)
        assert r.status_code == 404

    def test_messages_require_admin(self, client):
        data = _create_test_lead()
        conv_id = data["lifecycle"]["conversation"]["id"]

        r = client.get(f"/api/v1/admin/conversations/{conv_id}/messages")
        assert r.status_code == 401

        user_headers = _get_user_headers()
        r = client.get(f"/api/v1/admin/conversations/{conv_id}/messages", headers=user_headers)
        assert r.status_code == 403
