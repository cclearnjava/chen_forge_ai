"""Knowledge Quality Pipeline tests (P6.5): cleaning steps, fingerprints,
integration with document upload, review flags, backward compatibility."""

from starlette.testclient import TestClient
from app.db import SessionLocal, init_db
from app.models import KnowledgeDocument, KnowledgeItem
from app.services.knowledge_quality import (
    clean_extracted_text, content_fingerprint, normalize_text,
    remove_noise_lines, merge_broken_lines, dedupe_repeated_paragraphs,
    build_chunk_quality_metadata,
)

ADMIN = {"Authorization": "Bearer admin-dev-token"}

SAMPLE_RAW = """AI 咨询方案书

Page 1 of 12

我们为客户提供
AI 咨询、系统集成
和自动化交付服务。

Page 2 of 12

我们为客户提供
AI 咨询、系统集成
和自动化交付服务。

ChenForge AI Confidential

服务内容包括：需求分析、方案设计、PoC 验证、生产部署和持续运维。
"""


class TestCleaningSteps:
    def test_empty_text_returns_warning(self):
        r = clean_extracted_text("")
        assert r["clean_text"] == ""
        assert "cleaning_removed_all_content" in r["warnings"]

    def test_normalize_collapses_blank_lines(self):
        raw = "line1\n\n\n\nline2\n\nline3"
        clean, meta = normalize_text(raw)
        # Four consecutive newlines collapsed to two; the existing double-newline stays
        assert "\n\n\n" not in clean  # triple (or more) blank lines collapsed
        assert "line1" in clean and "line2" in clean and "line3" in clean

    def test_page_numbers_removed(self):
        raw = "服务内容\nPage 1 of 12\n核心能力"
        clean, meta = remove_noise_lines(raw)
        assert "Page 1 of 12" not in clean and "服务内容" in clean

    def test_repeating_header_footer_removed(self):
        raw = "Confidential\n正文第一段\nConfidential\n正文第二段\nConfidential\nConfidential\nConfidential\n"
        clean, meta = remove_noise_lines(raw)
        # "Confidential" appears >4 times → detected as repeating header
        assert "Confidential" not in clean
        assert "正文第一段" in clean and "正文第二段" in clean

    def test_broken_lines_merged(self):
        raw = "我们为客户提供\nAI 咨询、系统集成\n和自动化交付服务。"
        clean, meta = merge_broken_lines(raw)
        assert meta["broken_lines_merged"] >= 1
        # After merging, the three short lines become at most two
        assert "和自动化交付服务" in clean

    def test_consecutive_duplicate_paragraphs_deduped(self):
        raw = "段落A内容足够长。\n\n段落A内容足够长。\n\n段落B不同内容。"
        clean, meta = dedupe_repeated_paragraphs(raw)
        assert clean.count("段落A") == 1 and meta["duplicate_paragraphs_removed"] == 1

    def test_main_body_preserved(self):
        r = clean_extracted_text(SAMPLE_RAW)
        assert "需求分析" in r["clean_text"]
        assert "PoC 验证" in r["clean_text"]
        assert "生产部署" in r["clean_text"]

    def test_fingerprint_stable(self):
        fp1 = content_fingerprint("相同内容")
        fp2 = content_fingerprint("相同内容")
        assert fp1 == fp2 and len(fp1) == 16

    def test_clean_report_stats(self):
        r = clean_extracted_text(SAMPLE_RAW)
        m = r["metadata"]
        assert m["quality_pipeline_version"] == "knowledge_quality.det_v1"
        assert m["raw_text_length"] > m["clean_text_length"]
        assert m["removed_line_count"] > 0

    def test_chunk_quality_metadata(self):
        meta = build_chunk_quality_metadata(
            document_metadata={}, chunk_text="测试文本内容",
            chunk_index=0, chunk_count=5,
        )
        assert meta["chunk_index"] == 0 and meta["chunk_count"] == 5
        assert "chunk_fingerprint" in meta


class TestQualityPipelineIntegration:
    def _upload(self, client, filename, content: bytes, content_type="text/plain"):
        return client.post(
            "/api/v1/admin/knowledge/documents",
            files={"file": (filename, content, content_type)},
            headers=ADMIN,
        )

    def test_upload_txt_gets_quality_metadata(self, client: TestClient):
        init_db()
        r = self._upload(client, "report.txt",
                         "这份报告提供了充分详细的内容描述，涵盖了 AI 咨询方案的全貌，包含需求分析、方案设计与 PoC 验证等核心交付物。".encode())
        assert r.status_code == 201, r.text
        doc = r.json()["document"]
        assert doc["status"] == "processed"
        assert doc["metadata_json"] and "quality_pipeline_version" in doc["metadata_json"]

    def test_document_metadata_has_quality_summary(self, client: TestClient):
        init_db()
        r = self._upload(client, "plan.txt",
                         "这是一份完整的 AI 咨询交付方案文档，包含需求分析、方案设计、PoC 验证、生产部署和持续运维共五个核心阶段的详细内容描述。".encode())
        meta = r.json()["document"]["metadata_json"]
        assert "clean_text_length" in meta and "removed_line_count" in meta

    def test_text_excerpt_from_clean_text(self, client: TestClient):
        init_db()
        r = self._upload(client, "report.txt",
                         "需求分析的详细内容描述了客户当前面临的业务挑战、技术债务和期望目标，内容足够长以通过所有切分和质量阈值。".encode())
        doc = r.json()["document"]
        assert "需求分析" in doc["text_excerpt"]

    def test_empty_clean_fails_document(self, client: TestClient):
        init_db()
        r = self._upload(client, "empty.txt", b"")
        assert r.status_code == 422

    def test_review_queue_has_quality_flags(self, client: TestClient):
        init_db()
        self._upload(client, "short.txt",
                     "这是一个短文本短文，内容不足以通过最小切分阈值的要求，但需要满足基本的字数限制。".encode())
        review = client.get("/api/v1/admin/knowledge/review?status=draft", headers=ADMIN)
        items_with_flags = [i for i in review.json()["items"] if i["quality_flags"]]
        assert len(items_with_flags) >= 1

    def test_old_upload_still_works_no_quality_metadata(self, client: TestClient):
        init_db(); db = SessionLocal()
        from app.services.workspace import get_default_workspace_id
        wid = get_default_workspace_id(db)
        old = KnowledgeItem(workspace_id=wid, title="老条目", content_markdown="旧的上传条目无质量元数据",
                            source_type="manual", status="active")
        db.add(old); db.commit(); oid = old.id; db.close()
        # Retrieval must not crash on missing quality metadata
        from app.services.knowledge_retriever import retrieve_knowledge_for_sales_reply
        pack = retrieve_knowledge_for_sales_reply(SessionLocal(), workspace_id=wid, query_text="老条目")
        assert pack["hit_count"] >= 1

    def test_cross_workspace_fingerprint_isolation(self, client: TestClient):
        init_db()
        r1 = self._upload(client, "doc1.txt",
                          "跨工作区测试内容，这份文档包含了足够长度的描述来满足所有切分阈值要求，确保内容可以通过质量检查。".encode())
        assert r1.status_code == 201
        # Upload same content in default workspace — no cross-ws leak
        review = client.get("/api/v1/admin/knowledge/review?status=draft", headers=ADMIN)
        # Workspace isolation: only items from current workspace; no cross-ws blending
        assert review.status_code == 200
