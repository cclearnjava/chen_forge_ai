"""Knowledge Retriever tests (P6.3): scoring, filtering, citation pack structure,
workspace isolation, service-link boost, document source traces."""

import uuid
from app.db import SessionLocal, init_db
from app.models import KnowledgeDocument, KnowledgeItem, Workspace
from app.services.knowledge_retriever import RETRIEVER_VERSION, retrieve_knowledge_for_sales_reply


def _workspace(db):
    ws = Workspace(slug=f"rtr-{uuid.uuid4().hex[:8]}", name="RTR WS", is_default=False)
    db.add(ws); db.flush()
    return ws


def _item(db, wid, **over):
    defaults = {"title": "RAG PoC 验收标准", "content_markdown": "PoC 阶段建议先覆盖 20-50 个高频问题的验收测试", "summary": "RAG 交付常见验收要求", "source_type": "delivery_sop", "status": "active", "tags_json": ["rag", "验收"], "workspace_id": wid}
    defaults.update(over)
    it = KnowledgeItem(**defaults)
    db.add(it); db.commit()
    return it


class TestKnowledgeRetriever:
    def test_returns_citation_pack_structure(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(db, ws.id)
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="RAG PoC 验收")
        assert pack["retriever_version"] == RETRIEVER_VERSION
        assert "hits" in pack and "hit_count" in pack
        assert pack["hit_count"] >= 1 and pack["no_hit_reason"] is None

    def test_title_hit_returns_item(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(db, ws.id, title="完全独特的标题XYZ123")
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="XYZ123")
        assert any(h["knowledge_item_id"] for h in pack["hits"])
        assert "title" in pack["hits"][0]["match_reasons"]

    def test_summary_hit_recorded(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(db, ws.id, title="无关标题", summary="独特摘要UNIQUEZZZ")
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="UNIQUEZZZ")
        assert pack["hit_count"] >= 1
        assert "summary" in pack["hits"][0]["match_reasons"]

    def test_content_hit_recorded(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(db, ws.id, title="无关", summary="无关", content_markdown="正文中唯一关键词CONTENTKEY")
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="CONTENTKEY")
        assert pack["hit_count"] >= 1
        assert "content" in pack["hits"][0]["match_reasons"]

    def test_tags_hit_recorded(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(db, ws.id, title="无关", tags_json=["唯一标签TAGZZZ"])
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="TAGZZZ")
        assert pack["hit_count"] >= 1
        assert "tags" in pack["hits"][0]["match_reasons"]

    def test_service_link_boosts_sorting(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(db, ws.id, title="服务关联项", service_id="svc_1", content_markdown="测试")
        _item(db, ws.id, title="非关联项", service_id=None, content_markdown="测试")
        pack = retrieve_knowledge_for_sales_reply(
            db, workspace_id=ws.id, query_text="测试", matched_service_ids=["svc_1"],
        )
        # service-linked item must be first (higher score)
        hits = pack["hits"]
        linked = [h for h in hits if h["title"] == "服务关联项"]
        assert linked and "service_link" in linked[0]["match_reasons"]
        assert hits[0]["title"] == "服务关联项"

    def test_draft_excluded(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(db, ws.id, status="draft", content_markdown="草稿关键词XYZ")
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="XYZ")
        assert pack["hit_count"] == 0

    def test_archived_excluded(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(db, ws.id, status="archived", content_markdown="已归档关键词XYZ")
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="XYZ")
        assert pack["hit_count"] == 0

    def test_no_hit_empty_pack(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="不存在的内容")
        assert pack["hit_count"] == 0 and pack["hits"] == []
        assert "no_hit_reason" in pack and pack["no_hit_reason"] is not None

    def test_no_active_knowledge_reason(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="x")
        assert pack["no_hit_reason"] == "no_active_knowledge"

    def test_cross_workspace_excluded(self):
        init_db(); db = SessionLocal()
        ws1 = _workspace(db)
        ws2 = _workspace(db)
        _item(db, ws2.id, content_markdown="跨WS关键词")
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws1.id, query_text="跨WS关键词")
        assert pack["hit_count"] == 0

    def test_external_doc_source_includes_document_info(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        doc = KnowledgeDocument(workspace_id=ws.id, filename="sop.docx",
                                storage_path="x", status="processed")
        db.add(doc); db.commit()
        _item(db, ws.id, source_type="external_doc",
              content_markdown="来自文档的验收标准说明且内容足够长能够通过所有阈值检测",
              metadata_json={"document_id": doc.id, "chunk_index": 2})
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="验收标准文档")
        hits = [h for h in pack["hits"] if h["source_type"] == "external_doc"]
        assert hits
        src = hits[0]["source"]
        assert src["document_id"] == doc.id
        assert src["document_filename"] == "sop.docx"
        assert src["chunk_index"] == 2

    def test_external_doc_source_does_not_leak_other_workspace_filename(self):
        init_db(); db = SessionLocal()
        ws1 = _workspace(db)
        ws2 = _workspace(db)
        foreign_doc = KnowledgeDocument(workspace_id=ws2.id, filename="secret-other-ws.pdf",
                                        storage_path="x", status="processed")
        db.add(foreign_doc); db.commit()
        _item(db, ws1.id, source_type="external_doc",
              content_markdown="来自文档的验收标准说明且内容足够长能够通过所有阈值检测",
              metadata_json={"document_id": foreign_doc.id, "chunk_index": 1})
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws1.id, query_text="验收标准文档")
        hits = [h for h in pack["hits"] if h["source_type"] == "external_doc"]
        assert hits
        src = hits[0]["source"]
        assert src["document_id"] == foreign_doc.id
        assert src["document_filename"] is None

    def test_mock_reranker_can_reorder_existing_candidates(self, monkeypatch):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(
            db,
            ws.id,
            title="通用实施说明",
            summary="销售流程说明",
            content_markdown="企业微信 企业微信 企业微信 企业微信 企业微信 企业微信",
        )
        _item(
            db,
            ws.id,
            title="企业微信客服自动回复",
            summary="客户消息及时响应",
            content_markdown="企业微信",
        )
        from app.config import settings
        import app.services.reranker_provider as rp

        monkeypatch.setattr(settings, "reranker_provider", "mock")
        monkeypatch.setattr(settings, "reranker_model", "mock_overlap_reranker_v1")
        rp._provider = None
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="企业微信客服自动回复")
        db.close()

        assert pack["reranker_enabled"] is True
        assert pack["reranker_provider"] == "mock"
        assert pack["hits"][0]["title"] == "企业微信客服自动回复"
        assert pack["hits"][0]["reranked"] is True
        assert pack["hits"][0]["rerank_score"] is not None

    def test_reranker_failure_falls_back_to_original_order(self, monkeypatch):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(db, ws.id, title="更高分候选", content_markdown="报价方案流程边界")
        _item(db, ws.id, title="较低分候选", content_markdown="报价")

        from app.config import settings
        import app.services.reranker_provider as rp

        class FailingReranker:
            name = "mock"
            model = "broken"

            def rerank(self, query, candidates):
                raise RuntimeError("reranker unavailable")

        monkeypatch.setattr(settings, "reranker_provider", "mock")
        rp._provider = FailingReranker()
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="报价方案流程")
        db.close()

        assert pack["reranker_enabled"] is True
        assert pack["reranker_error"] == "reranker unavailable"
        assert pack["hits"][0]["title"] == "更高分候选"
        assert all("rerank_score" not in h for h in pack["hits"])
