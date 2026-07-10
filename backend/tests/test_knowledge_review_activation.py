"""Knowledge Review / Activation tests (P6.4): review queue, quality flags,
bulk actions, document review, workspace isolation, events."""

import uuid
from starlette.testclient import TestClient
from app.db import SessionLocal, init_db
from app.models import Event, KnowledgeDocument, KnowledgeItem, Workspace

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _item(client, **over):
    body = {"title": f"review-{uuid.uuid4().hex[:6]}", "content_markdown": "正文内容足够长以达到所有质量检查的通过阈值标准。"}
    body.update(over)
    r = client.post("/api/v1/admin/knowledge", json=body, headers=ADMIN)
    assert r.status_code == 201, r.text
    return r.json()


def _review(client, **qs):
    p = "&".join(f"{k}={v}" for k, v in qs.items() if v is not None)
    return client.get(f"/api/v1/admin/knowledge/review?{p}", headers=ADMIN)


def _bulk(client, item_ids, action, service_id=None):
    body = {"item_ids": item_ids, "action": action}
    if service_id is not None:
        body["service_id"] = service_id
    return client.post("/api/v1/admin/knowledge/review/bulk", json=body, headers=ADMIN)


class TestReviewQueue:
    def test_default_returns_draft_items(self, client: TestClient):
        init_db()
        _item(client, status="draft")
        _item(client, status="active")
        r = _review(client)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["item"]["status"] == "draft"

    def test_filter_by_document_id(self, client: TestClient):
        init_db()
        did = "doc-filter-1"
        _item(client, status="draft", metadata_json={"document_id": did})
        _item(client, status="draft", metadata_json={"document_id": "other-doc"})
        r = _review(client, document_id=did)
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["item"]["metadata_json"]["document_id"] == did

    def test_filter_by_quality_flag(self, client: TestClient):
        init_db()
        _item(client, status="draft", content_markdown="太短")
        _item(client, status="draft", content_markdown="足够长的内容文本，超过了质量检查的字符数阈值限制因此不会产生警告")
        r = _review(client, quality_flag="short_content")
        assert r.json()["total"] >= 1
        flags = [flag for it in r.json()["items"] for flag in it["quality_flags"]]
        assert "short_content" in flags


class TestQualityFlags:
    def test_short_content_flag(self, client: TestClient):
        init_db()
        it = _item(client, status="draft", content_markdown="短")
        r = _review(client)
        found = [i for i in r.json()["items"] if i["item"]["id"] == it["id"]]
        assert found and "short_content" in found[0]["quality_flags"]

    def test_missing_summary_flag(self, client: TestClient):
        init_db()
        it = _item(client, status="draft", summary=None)
        r = _review(client)
        found = [i for i in r.json()["items"] if i["item"]["id"] == it["id"]]
        assert found and "missing_summary" in found[0]["quality_flags"]

    def test_missing_service_flag(self, client: TestClient):
        init_db()
        it = _item(client, status="draft", service_id=None)
        r = _review(client)
        found = [i for i in r.json()["items"] if i["item"]["id"] == it["id"]]
        assert found and "missing_service" in found[0]["quality_flags"]

    def test_duplicate_title_flag(self, client: TestClient):
        init_db()
        _item(client, status="draft", title="同一个标题")
        _item(client, status="active", title="同一个标题")
        r = _review(client)
        found = [i for i in r.json()["items"] if i["item"]["title"] == "同一个标题"]
        assert len(found) >= 1
        assert "duplicate_title" in found[0]["quality_flags"]


class TestBulkActions:
    def test_bulk_activate(self, client: TestClient):
        init_db()
        i1 = _item(client, status="draft")
        i2 = _item(client, status="draft")
        r = _bulk(client, [i1["id"], i2["id"]], "activate")
        assert r.status_code == 200 and r.json()["updated_count"] == 2
        for it in r.json()["items"]:
            assert it["status"] == "active"

    def test_bulk_archive(self, client: TestClient):
        init_db()
        i1 = _item(client, status="draft")
        r = _bulk(client, [i1["id"]], "archive")
        assert r.status_code == 200
        assert r.json()["items"][0]["status"] == "archived"
        assert r.json()["items"][0]["archived_at"] is not None

    def test_bulk_activate_hides_from_default_review(self, client: TestClient):
        init_db()
        i1 = _item(client, status="draft")
        _bulk(client, [i1["id"]], "activate")
        r = _review(client)
        ids = [it["item"]["id"] for it in r.json()["items"]]
        assert i1["id"] not in ids

    def test_unknown_item_422(self, client: TestClient):
        init_db()
        r = _bulk(client, ["does-not-exist"], "activate")
        assert r.status_code == 422

    def test_set_service_requires_service_id(self, client: TestClient):
        init_db()
        i1 = _item(client, status="draft")
        r = _bulk(client, [i1["id"]], "set_service")
        assert r.status_code == 422
        assert "service_id is required" in r.json()["detail"]

    def test_cross_workspace_item_rejected(self, client: TestClient):
        init_db(); db = SessionLocal()
        ws2 = Workspace(slug=f"rvw-ws2-{uuid.uuid4().hex[:6]}", name="RVW WS2", is_default=False)
        db.add(ws2); db.commit()
        other = KnowledgeItem(workspace_id=ws2.id, title="别人的草稿", content_markdown="别的 workspace 的内容项，足够长以符合所有要求", status="draft")
        db.add(other); db.commit(); oid = other.id; db.close()
        r = _bulk(client, [oid], "activate")
        assert r.status_code == 422

    def test_review_document_ref_does_not_leak_other_workspace_filename(self, client: TestClient):
        init_db(); db = SessionLocal()
        ws2 = Workspace(slug=f"rvw-doc-ws2-{uuid.uuid4().hex[:6]}", name="RVW DOC WS2", is_default=False)
        db.add(ws2); db.commit()
        foreign_doc = KnowledgeDocument(workspace_id=ws2.id, filename="secret-other-workspace.pdf",
                                        storage_path="x", status="processed")
        db.add(foreign_doc); db.commit()
        db.close()

        item = _item(client, status="draft", source_type="external_doc",
                     metadata_json={"document_id": foreign_doc.id})
        r = _review(client, document_id=foreign_doc.id)
        assert r.status_code == 200
        found = [it for it in r.json()["items"] if it["item"]["id"] == item["id"]]
        assert found
        assert found[0]["document"] is None


class TestDocumentReview:
    def test_returns_counts(self, client: TestClient):
        init_db(); db = SessionLocal()
        from app.services.workspace import get_default_workspace_id
        wid = get_default_workspace_id(db); db.close()
        doc = KnowledgeDocument(workspace_id=wid, filename="review-test.md",
                                storage_path="x", status="processed")
        db2 = SessionLocal(); db2.add(doc); db2.commit(); did = doc.id; db2.close()
        i1 = _item(client, status="draft", source_type="external_doc",
                    metadata_json={"document_id": did})
        i2 = _item(client, status="active", source_type="external_doc",
                    metadata_json={"document_id": did})
        r = client.get(f"/api/v1/admin/knowledge/documents/{did}/review", headers=ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["counts"]["total"] == 2
        assert body["counts"]["draft"] == 1 and body["counts"]["active"] == 1
        assert body["document"]["filename"] == "review-test.md"

    def test_event_recorded_on_bulk(self, client: TestClient):
        init_db()
        i1 = _item(client, status="draft")
        ba = _bulk(client, [i1["id"]], "activate")
        db = SessionLocal()
        ev = db.query(Event).filter(Event.type == "knowledge_review.bulk_activated",
                                    Event.subject_type == "knowledge_item").first()
        db.close()
        assert ev is not None
