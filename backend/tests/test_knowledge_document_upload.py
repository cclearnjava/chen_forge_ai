"""Knowledge document upload tests (P6): upload, extract, chunk, draft items,
fail-closed on bad input, workspace isolation, events."""

from starlette.testclient import TestClient
from app.db import SessionLocal, init_db
from app.models import Event, KnowledgeDocument, KnowledgeItem, Workspace

ADMIN = {"Authorization": "Bearer admin-dev-token"}

FAQ_MD = """# 常见问题

## PoC 一般多久？
通常 2-4 周，取决于数据准备情况。如果客户资料齐全，可以更快进入验证阶段。

## 是否直接接生产系统？
第一阶段建议只读或离线数据验证，不直接操作生产库，避免不可控风险。
"""

PLAIN_TXT = "这是一段没有任何标题结构的纯文本。" * 120  # long, forces length chunking


def _upload(client, filename, content: bytes, content_type="text/plain"):
    return client.post(
        "/api/v1/admin/knowledge/documents",
        files={"file": (filename, content, content_type)},
        headers=ADMIN,
    )


class TestKnowledgeDocumentUpload:
    def test_upload_txt_creates_document(self, client: TestClient):
        init_db()
        text = "这是一份足够长的纯文本文件，用于验证上传解析能够生成知识条目草稿，内容长度超过最小切分阈值四十个字符。"
        r = _upload(client, "note.txt", text.encode("utf-8"))
        assert r.status_code == 201, r.text
        d = r.json()["document"]
        assert d["status"] == "processed"
        assert d["file_ext"] == ".txt"
        assert d["parser"] == "text_v1"

    def test_upload_md_creates_draft_items(self, client: TestClient):
        init_db()
        r = _upload(client, "faq.md", FAQ_MD.encode("utf-8"), "text/markdown")
        assert r.status_code == 201
        body = r.json()
        assert body["item_count"] >= 2
        for it in body["items"]:
            assert it["status"] == "draft"
            assert it["source_type"] == "external_doc"

    def test_markdown_heading_split_multiple_items(self, client: TestClient):
        init_db()
        r = _upload(client, "faq.md", FAQ_MD.encode("utf-8"), "text/markdown")
        titles = [it["title"] for it in r.json()["items"]]
        assert any("PoC" in t for t in titles)
        assert any("生产" in t for t in titles)

    def test_long_text_length_chunking(self, client: TestClient):
        init_db()
        r = _upload(client, "long.txt", PLAIN_TXT.encode("utf-8"))
        assert r.status_code == 201
        # ~1440 chars / 1200 per chunk with overlap → at least 2 chunks
        assert r.json()["item_count"] >= 2

    def test_generated_item_metadata(self, client: TestClient):
        init_db()
        r = _upload(client, "faq.md", FAQ_MD.encode("utf-8"), "text/markdown")
        doc_id = r.json()["document"]["id"]
        for it in r.json()["items"]:
            assert it["metadata_json"]["document_id"] == doc_id
            assert "chunk_index" in it["metadata_json"]

    def test_unsupported_type_422(self, client: TestClient):
        init_db()
        r = _upload(client, "data.xlsx", b"\x50\x4b\x03\x04binary", "application/vnd.ms-excel")
        assert r.status_code == 422

    def test_empty_file_422(self, client: TestClient):
        init_db()
        r = _upload(client, "empty.txt", b"")
        assert r.status_code == 422

    def test_non_utf8_422(self, client: TestClient):
        init_db()
        r = _upload(client, "bad.txt", b"\xff\xfe\x00\x01invalid")
        assert r.status_code == 422

    def test_failure_creates_no_items_but_records_doc(self, client: TestClient):
        init_db()
        r = _upload(client, "data.xlsx", b"binary", "application/octet-stream")
        assert r.status_code == 422
        db = SessionLocal()
        failed = db.query(KnowledgeDocument).filter(KnowledgeDocument.status == "failed").all()
        db.close()
        assert len(failed) >= 1
        # failed document must have item_count == 0
        assert failed[0].item_count == 0

    def test_document_list_and_detail(self, client: TestClient):
        init_db()
        up = _upload(client, "faq.md", FAQ_MD.encode("utf-8"), "text/markdown")
        doc_id = up.json()["document"]["id"]
        lst = client.get("/api/v1/admin/knowledge/documents", headers=ADMIN)
        assert lst.status_code == 200 and lst.json()["total"] >= 1
        det = client.get(f"/api/v1/admin/knowledge/documents/{doc_id}", headers=ADMIN)
        assert det.status_code == 200 and det.json()["id"] == doc_id

    def test_workspace_isolation(self, client: TestClient):
        init_db(); db = SessionLocal()
        ws2 = Workspace(slug="kdoc-ws2", name="WS2", is_default=False)
        db.add(ws2); db.commit()
        other = KnowledgeDocument(workspace_id=ws2.id, filename="ws2.md",
                                  storage_path="x", status="processed")
        db.add(other); db.commit(); other_id = other.id; db.close()
        lst = client.get("/api/v1/admin/knowledge/documents", headers=ADMIN)
        names = [d["filename"] for d in lst.json()["items"]]
        assert "ws2.md" not in names
        det = client.get(f"/api/v1/admin/knowledge/documents/{other_id}", headers=ADMIN)
        assert det.status_code == 404

    def test_event_recorded_on_success(self, client: TestClient):
        init_db()
        r = _upload(client, "faq.md", FAQ_MD.encode("utf-8"), "text/markdown")
        doc_id = r.json()["document"]["id"]
        db = SessionLocal()
        ev = db.query(Event).filter(Event.type == "knowledge_document.processed",
                                    Event.subject_id == doc_id).first()
        db.close()
        assert ev is not None

    def test_event_recorded_on_failure(self, client: TestClient):
        init_db()
        _upload(client, "bad.bin", b"\xff\xfe", "application/octet-stream")
        db = SessionLocal()
        ev = db.query(Event).filter(Event.type == "knowledge_document.failed").first()
        db.close()
        assert ev is not None

    def test_uploaded_items_hidden_from_default_active_list(self, client: TestClient):
        init_db()
        up = _upload(client, "faq.md", FAQ_MD.encode("utf-8"), "text/markdown")
        uploaded_ids = {it["id"] for it in up.json()["items"]}
        assert len(uploaded_ids) >= 2
        # draft items appear only under status=draft, never in the default active list
        draft_ids = {it["id"] for it in client.get("/api/v1/admin/knowledge?status=draft", headers=ADMIN).json()["items"]}
        active_ids = {it["id"] for it in client.get("/api/v1/admin/knowledge", headers=ADMIN).json()["items"]}
        assert uploaded_ids <= draft_ids
        assert uploaded_ids.isdisjoint(active_ids)
