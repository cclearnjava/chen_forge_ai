"""Workspace Knowledge Engine tests: CRUD, search, filter, archive, workspace isolation."""

from starlette.testclient import TestClient
from app.db import SessionLocal, init_db
from app.models import KnowledgeItem, KnowledgeSource, Workspace

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _create(client, **over):
    body = {"title": "RAG 验收标准", "content_markdown": "RAG 项目常见验收标准正文"}
    body.update(over)
    return client.post("/api/v1/admin/knowledge", json=body, headers=ADMIN)


class TestKnowledgeEngine:
    def test_create_item_returns_full_object(self, client: TestClient):
        init_db()
        r = _create(client, summary="摘要", tags_json=["rag", "acceptance"], source_type="methodology")
        assert r.status_code == 201
        d = r.json()
        assert d["title"] == "RAG 验收标准"
        assert d["status"] == "active"
        assert d["tags_json"] == ["rag", "acceptance"]
        assert d["source_type"] == "methodology"
        assert "created_at" in d and "workspace_id" in d

    def test_create_requires_title(self, client: TestClient):
        init_db()
        r = client.post("/api/v1/admin/knowledge", json={"content_markdown": "x"}, headers=ADMIN)
        assert r.status_code == 422

    def test_create_requires_content(self, client: TestClient):
        init_db()
        r = client.post("/api/v1/admin/knowledge", json={"title": "x"}, headers=ADMIN)
        assert r.status_code == 422

    def test_invalid_status_rejected(self, client: TestClient):
        init_db()
        r = _create(client, status="bogus")
        assert r.status_code == 422

    def test_invalid_source_type_rejected(self, client: TestClient):
        init_db()
        r = _create(client, source_type="nope")
        assert r.status_code == 422

    def test_list_defaults_to_active_only(self, client: TestClient):
        init_db()
        _create(client, title="active one")
        _create(client, title="draft one", status="draft")
        r = client.get("/api/v1/admin/knowledge", headers=ADMIN)
        assert r.status_code == 200
        titles = [i["title"] for i in r.json()["items"]]
        assert "active one" in titles
        assert "draft one" not in titles

    def test_filter_by_status_draft(self, client: TestClient):
        init_db()
        _create(client, title="draft only", status="draft")
        r = client.get("/api/v1/admin/knowledge?status=draft", headers=ADMIN)
        titles = [i["title"] for i in r.json()["items"]]
        assert "draft only" in titles

    def test_search_by_title(self, client: TestClient):
        init_db()
        _create(client, title="独特标题UNIQUEXYZ")
        r = client.get("/api/v1/admin/knowledge?q=UNIQUEXYZ", headers=ADMIN)
        assert any("UNIQUEXYZ" in i["title"] for i in r.json()["items"])

    def test_search_by_content(self, client: TestClient):
        init_db()
        _create(client, title="内容搜索", content_markdown="正文包含关键词ZZZCONTENT")
        r = client.get("/api/v1/admin/knowledge?q=ZZZCONTENT", headers=ADMIN)
        assert len(r.json()["items"]) >= 1

    def test_filter_by_tag(self, client: TestClient):
        init_db()
        _create(client, title="标签A", tags_json=["alpha"])
        _create(client, title="标签B", tags_json=["beta"])
        r = client.get("/api/v1/admin/knowledge?tag=alpha", headers=ADMIN)
        titles = [i["title"] for i in r.json()["items"]]
        assert "标签A" in titles and "标签B" not in titles

    def test_filter_by_source_type(self, client: TestClient):
        init_db()
        _create(client, title="faq项", source_type="faq")
        _create(client, title="案例项", source_type="case_study")
        r = client.get("/api/v1/admin/knowledge?source_type=faq", headers=ADMIN)
        for i in r.json()["items"]:
            assert i["source_type"] == "faq"

    def test_filter_by_service_id(self, client: TestClient):
        init_db()
        client.post("/api/v1/admin/services/seed-defaults", headers=ADMIN)
        sid = client.get("/api/v1/admin/services", headers=ADMIN).json()["items"][0]["id"]
        _create(client, title="关联服务的知识", service_id=sid)
        r = client.get(f"/api/v1/admin/knowledge?service_id={sid}", headers=ADMIN)
        assert any(i["service_id"] == sid for i in r.json()["items"])

    def test_service_id_must_belong_to_workspace(self, client: TestClient):
        init_db()
        r = _create(client, service_id="nonexistent-service")
        assert r.status_code == 422

    def test_detail_scoped_to_workspace(self, client: TestClient):
        init_db()
        kid = _create(client).json()["id"]
        r = client.get(f"/api/v1/admin/knowledge/{kid}", headers=ADMIN)
        assert r.status_code == 200
        r2 = client.get("/api/v1/admin/knowledge/does-not-exist", headers=ADMIN)
        assert r2.status_code == 404

    def test_update_fields(self, client: TestClient):
        init_db()
        kid = _create(client).json()["id"]
        r = client.patch(f"/api/v1/admin/knowledge/{kid}",
                         json={"title": "改后标题", "tags_json": ["x"], "status": "draft"}, headers=ADMIN)
        assert r.status_code == 200
        d = r.json()
        assert d["title"] == "改后标题" and d["tags_json"] == ["x"] and d["status"] == "draft"

    def test_archive_hides_from_default_list(self, client: TestClient):
        init_db()
        kid = _create(client, title="将被归档").json()["id"]
        r = client.post(f"/api/v1/admin/knowledge/{kid}/archive", headers=ADMIN)
        assert r.status_code == 200
        assert r.json()["status"] == "archived"
        assert r.json()["archived_at"] is not None
        titles = [i["title"] for i in client.get("/api/v1/admin/knowledge", headers=ADMIN).json()["items"]]
        assert "将被归档" not in titles
        arch = [i["title"] for i in client.get("/api/v1/admin/knowledge?status=archived", headers=ADMIN).json()["items"]]
        assert "将被归档" in arch

    def test_sources_seed_and_list(self, client: TestClient):
        init_db()
        r = client.get("/api/v1/admin/knowledge/sources", headers=ADMIN)
        assert r.status_code == 200
        assert len(r.json()["items"]) >= 5

    def test_create_source(self, client: TestClient):
        init_db()
        r = client.post("/api/v1/admin/knowledge/sources", json={"name": "外部文档"}, headers=ADMIN)
        assert r.status_code == 201
        assert r.json()["name"] == "外部文档"

    def test_cross_workspace_isolation(self, client: TestClient):
        init_db(); db = SessionLocal()
        ws2 = Workspace(slug="kn-ws2", name="KN WS2", is_default=False)
        db.add(ws2); db.commit()
        item2 = KnowledgeItem(workspace_id=ws2.id, title="WS2 私有知识",
                              content_markdown="其他 workspace 的内容", status="active")
        db.add(item2); db.commit(); item2_id = item2.id; db.close()
        # not visible in list
        titles = [i["title"] for i in client.get("/api/v1/admin/knowledge", headers=ADMIN).json()["items"]]
        assert "WS2 私有知识" not in titles
        # not readable
        assert client.get(f"/api/v1/admin/knowledge/{item2_id}", headers=ADMIN).status_code == 404
        # not updatable
        assert client.patch(f"/api/v1/admin/knowledge/{item2_id}", json={"title": "hack"}, headers=ADMIN).status_code == 404
        # not archivable
        assert client.post(f"/api/v1/admin/knowledge/{item2_id}/archive", headers=ADMIN).status_code == 404

    def test_event_recorded_on_create(self, client: TestClient):
        init_db()
        kid = _create(client).json()["id"]
        db = SessionLocal()
        from app.models import Event
        ev = db.query(Event).filter(Event.type == "knowledge_item.created",
                                    Event.subject_id == kid).first()
        db.close()
        assert ev is not None
