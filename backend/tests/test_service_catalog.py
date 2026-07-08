"""Service Catalog tests: API, workspace isolation, seed."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.models import Service, ServiceDeliverable, ServicePackage, ServiceRiskRule, ServiceStatus, Workspace

ADMIN = {"Authorization": "Bearer admin-dev-token"}


class TestServiceCatalog:
    def test_seed_defaults_creates_services(self, client: TestClient):
        init_db()
        r = client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] >= 5
        assert any(s["slug"] == "ai-agent-consulting" for s in data["services"])

    def test_seed_defaults_is_idempotent(self, client: TestClient):
        init_db()
        r1 = client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r2 = client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        assert r1.json()["count"] == r2.json()["count"]

    def test_list_services(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN)
        assert r.status_code == 200
        assert r.json()["total"] >= 5

    def test_list_services_filter_by_status(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services?status=active", headers=ADMIN)
        assert r.status_code == 200
        for s in r.json()["items"]:
            assert s["status"] == "active"

    def test_get_service_detail(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN)
        sid = r.json()["items"][0]["id"]
        r2 = client.get(f"/api/v1/admin/services/{sid}", headers=ADMIN)
        assert r2.status_code == 200

    def test_update_service(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN)
        sid = r.json()["items"][0]["id"]
        r2 = client.patch(f"/api/v1/admin/services/{sid}", json={"target_customer": "Updated target"}, headers=ADMIN)
        assert r2.status_code == 200
        assert r2.json()["target_customer"] == "Updated target"

    def test_deactivate_and_reactivate(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN)
        sid = r.json()["items"][0]["id"]
        r2 = client.post(f"/api/v1/admin/services/{sid}/deactivate", headers=ADMIN)
        assert r2.status_code == 200
        assert r2.json()["status"] == "inactive"
        r3 = client.post(f"/api/v1/admin/services/{sid}/activate", headers=ADMIN)
        assert r3.status_code == 200
        assert r3.json()["status"] == "active"

    def test_archive_service(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN)
        sid = r.json()["items"][0]["id"]
        r2 = client.post(f"/api/v1/admin/services/{sid}/archive", headers=ADMIN)
        assert r2.status_code == 200
        assert r2.json()["status"] == "archived"

    def test_other_workspace_services_not_visible(self, client: TestClient):
        init_db(); db = SessionLocal()
        ws2 = Workspace(slug="svc-ws2", name="WS2", is_default=False)
        db.add(ws2); db.commit()
        svc2 = Service(workspace_id=ws2.id, name="WS2 Service", slug="ws2-svc", status=ServiceStatus.active)
        db.add(svc2); db.commit(); svc2_id = svc2.id; db.close()
        r = client.get("/api/v1/admin/services", headers=ADMIN)
        slugs = [s["slug"] for s in r.json()["items"]]
        assert "ws2-svc" not in slugs
        r2 = client.get(f"/api/v1/admin/services/{svc2_id}", headers=ADMIN)
        assert r2.status_code == 404


    def test_create_package(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN)
        sid = r.json()["items"][0]["id"]
        r2 = client.post(f"/api/v1/admin/services/{sid}/packages", json={"name": "PoC Package"}, headers=ADMIN)
        assert r2.status_code == 201
        r3 = client.get(f"/api/v1/admin/services/{sid}/packages", headers=ADMIN)
        assert len(r3.json()["items"]) >= 1

    def test_create_and_delete_deliverable(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN)
        sid = r.json()["items"][0]["id"]
        r2 = client.post(f"/api/v1/admin/services/{sid}/deliverables", json={"title": "PoC Report"}, headers=ADMIN)
        assert r2.status_code == 201
        did = r2.json()["id"]
        r3 = client.delete(f"/api/v1/admin/services/{sid}/deliverables/{did}", headers=ADMIN)
        assert r3.status_code == 200

    def test_create_risk_rule(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN)
        sid = r.json()["items"][0]["id"]
        r2 = client.post(f"/api/v1/admin/services/{sid}/risk-rules", json={"title": "No data risk", "severity": "high", "disqualifies": True}, headers=ADMIN)
        assert r2.status_code == 201
        r3 = client.get(f"/api/v1/admin/services/{sid}/risk-rules", headers=ADMIN)
        assert len(r3.json()["items"]) >= 1


    def test_update_package(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN)
        sid = r.json()["items"][0]["id"]
        r2 = client.post(f"/api/v1/admin/services/{sid}/packages", json={"name": "Basic"}, headers=ADMIN)
        pid = r2.json()["id"]
        r3 = client.patch(f"/api/v1/admin/services/{sid}/packages/{pid}", json={"name": "Basic Plus"}, headers=ADMIN)
        assert r3.status_code == 200
        assert r3.json()["name"] == "Basic Plus"

    def test_update_deliverable(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN)
        sid = r.json()["items"][0]["id"]
        r2 = client.post(f"/api/v1/admin/services/{sid}/deliverables", json={"title": "Report"}, headers=ADMIN)
        did = r2.json()["id"]
        r3 = client.patch(f"/api/v1/admin/services/{sid}/deliverables/{did}", json={"title": "Updated Report"}, headers=ADMIN)
        assert r3.status_code == 200
        assert r3.json()["title"] == "Updated Report"

    def test_update_risk_rule(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN)
        sid = r.json()["items"][0]["id"]
        r2 = client.post(f"/api/v1/admin/services/{sid}/risk-rules", json={"title": "Data risk", "severity": "low"}, headers=ADMIN)
        rid = r2.json()["id"]
        r3 = client.patch(f"/api/v1/admin/services/{sid}/risk-rules/{rid}", json={"severity": "high"}, headers=ADMIN)
        assert r3.status_code == 200


    def test_create_package_returns_full_object(self, client: TestClient):
        init_db(); client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN); sid = r.json()["items"][0]["id"]
        r2 = client.post(f"/api/v1/admin/services/{sid}/packages", json={"name": "Full", "description": "desc", "price_min": 10000, "price_max": 50000, "duration": "4 weeks"}, headers=ADMIN)
        assert r2.status_code == 201
        d = r2.json(); assert d["name"] == "Full"; assert d["description"] == "desc"; assert d["price_min"] == 10000; assert "created_at" in d

    def test_update_package_returns_full_object(self, client: TestClient):
        init_db(); client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN); sid = r.json()["items"][0]["id"]
        r2 = client.post(f"/api/v1/admin/services/{sid}/packages", json={"name": "Orig"}, headers=ADMIN)
        pid = r2.json()["id"]
        r3 = client.patch(f"/api/v1/admin/services/{sid}/packages/{pid}", json={"name": "Updated", "description": "new desc"}, headers=ADMIN)
        assert r3.status_code == 200
        d = r3.json(); assert d["name"] == "Updated"; assert "description" in d

    def test_create_package_missing_name_returns_422(self, client: TestClient):
        init_db(); client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN); sid = r.json()["items"][0]["id"]
        r2 = client.post(f"/api/v1/admin/services/{sid}/packages", json={}, headers=ADMIN)
        assert r2.status_code == 422

    def test_invalid_severity_returns_422(self, client: TestClient):
        init_db(); client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        r = client.get("/api/v1/admin/services", headers=ADMIN); sid = r.json()["items"][0]["id"]
        r2 = client.post(f"/api/v1/admin/services/{sid}/risk-rules", json={"title": "Bad", "severity": "INVALID"}, headers=ADMIN)
        assert r2.status_code == 422

    def test_other_ws_cannot_read_sub_resources(self, client: TestClient):
        init_db(); db = SessionLocal()
        from app.models import Workspace as WS
        ws2 = WS(slug="sub-ws2", name="WS2", is_default=False); db.add(ws2); db.commit()
        svc2 = Service(workspace_id=ws2.id, name="WS2 Svc", slug="ws2-svc", status=ServiceStatus.active); db.add(svc2); db.commit()
        pkg = ServicePackage(workspace_id=ws2.id, service_id=svc2.id, name="WS2 Pkg"); db.add(pkg); db.commit()
        svc2_id = svc2.id; pkg_id = pkg.id; db.close()
        r = client.get(f"/api/v1/admin/services/{svc2_id}/packages", headers=ADMIN)
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert len(r.json()["items"]) == 0
        r2 = client.patch(f"/api/v1/admin/services/{svc2_id}/packages/{pkg_id}", json={"name": "x"}, headers=ADMIN)
        assert r2.status_code == 404
