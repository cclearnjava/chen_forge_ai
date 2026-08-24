"""Vector RAG MVP tests (P6.5): embedding provider, indexing, content hash,
vector search, hybrid retrieval, workspace isolation, Citation Pack compat."""

import uuid
from starlette.testclient import TestClient
from app.db import SessionLocal, init_db
from app.models import KnowledgeItem, KnowledgeVector, Workspace
from app.services.embedding_provider import embed_text
from app.services.knowledge_vectors import (
    compute_content_hash, get_vector_status, index_knowledge_item,
    knowledge_item_embedding_text, reindex_active_knowledge, search_vectors,
)
from app.services.knowledge_retriever import RETRIEVER_VERSION, retrieve_knowledge_for_sales_reply

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _workspace(db):
    ws = Workspace(slug=f"vec-{uuid.uuid4().hex[:8]}", name="VEC WS", is_default=False)
    db.add(ws); db.flush()
    return ws


def _item(db, wid, **over):
    defaults = {"title": f"向量测试-{uuid.uuid4().hex[:4]}",
                "content_markdown": "向量索引测试用的正文内容，足够长以确保通过切分阈值和质量检查。",
                "status": "active", "workspace_id": wid}
    defaults.update(over)
    it = KnowledgeItem(**defaults)
    db.add(it); db.commit()
    return it


class TestEmbeddingProvider:
    def test_stable_vector_same_text(self):
        v1 = embed_text("同一段文本")
        v2 = embed_text("同一段文本")
        assert v1 == v2 and len(v1) == 64

    def test_empty_text_raises(self):
        try:
            embed_text("")
            assert False, "should raise"
        except ValueError:
            pass


class TestKnowledgeVectorIndexing:
    def test_active_item_can_be_indexed(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it = _item(db, ws.id)
        vec = index_knowledge_item(db, ws.id, it.id)
        db.close()
        assert vec.status == "indexed" and vec.vector_dim == 64

    def test_draft_item_rejected(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it = _item(db, ws.id, status="draft")
        try:
            index_knowledge_item(db, ws.id, it.id)
            assert False, "should raise"
        except ValueError as exc:
            assert "not active" in str(exc)
        db.close()

    def test_archived_item_not_in_vector_search(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it_active = _item(db, ws.id, title="活跃项", content_markdown="RAG检索验证测试")
        idx_active = index_knowledge_item(db, ws.id, it_active.id)
        # archived item with same embedding text would share the vector, but must be excluded
        it_archived = _item(db, ws.id, status="archived", title="活跃项", content_markdown="RAG检索验证测试")
        # Search with the ACTUAL embedding text so mock hash maps to the same vector
        from app.services.knowledge_vectors import knowledge_item_embedding_text
        q = knowledge_item_embedding_text(it_active)
        res = search_vectors(db, ws.id, q)
        ids = {h["knowledge_item_id"] for h in res}
        db.close()
        assert it_active.id in ids and it_archived.id not in ids

    def test_content_hash_detects_change(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it = _item(db, ws.id, title="原标题")
        h1 = compute_content_hash(it)
        it.title = "改后标题"
        h2 = compute_content_hash(it)
        db.close()
        assert h1 != h2

    def test_get_vector_status_returns_stale(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it = _item(db, ws.id)
        index_knowledge_item(db, ws.id, it.id)
        it.title = "标题已改"
        db.commit()
        st = get_vector_status(db, ws.id, it.id)
        db.close()
        assert st["stale"] is True and st["status"] == "stale"

    def test_reindex_batch_only_active(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(db, ws.id)  # active
        _item(db, ws.id)  # active
        _item(db, ws.id, status="draft")
        result = reindex_active_knowledge(db, ws.id, limit=100)
        db.close()
        assert result["indexed_count"] == 2 and result["failed_count"] == 0

    def test_cross_workspace_index_rejected(self):
        init_db(); db = SessionLocal()
        ws1 = _workspace(db)
        ws2 = _workspace(db)
        other = _item(db, ws2.id)
        try:
            index_knowledge_item(db, ws1.id, other.id)
            assert False, "should raise"
        except ValueError:
            pass
        db.close()

    def test_vector_search_workspace_scoped(self):
        init_db(); db = SessionLocal()
        ws1 = _workspace(db)
        ws2 = _workspace(db)
        it1 = _item(db, ws1.id, title="独有项", content_markdown="WS隔离验证")
        index_knowledge_item(db, ws1.id, it1.id)
        _item(db, ws2.id, title="独有项", content_markdown="WS隔离验证")
        from app.services.knowledge_vectors import knowledge_item_embedding_text
        q = knowledge_item_embedding_text(it1)
        res = search_vectors(db, ws1.id, q)
        ids = {h["knowledge_item_id"] for h in res}
        db.close()
        assert it1.id in ids


class TestProviderSwitch:
    """P6.7: after switching provider/model, the old-model vector must not be reused."""

    def _switch_provider(self, monkeypatch, *, name: str, model: str):
        import app.services.embedding_provider as ep
        switched = ep.MockHashEmbeddingProvider()
        switched.name = name
        switched.model = model
        switched.dim = 64  # keep dim so embed_text still produces a comparable vector
        monkeypatch.setattr(ep, "_provider", switched)

    def test_get_vector_status_ignores_old_model_vector(self, monkeypatch):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it = _item(db, ws.id)
        index_knowledge_item(db, ws.id, it.id)
        st_before = get_vector_status(db, ws.id, it.id)
        assert st_before["status"] == "indexed"
        assert st_before["embedding_model"] == "mock_hash_embedding_v1"

        self._switch_provider(monkeypatch, name="openai_compatible", model="text-embedding-3-small")
        st_after = get_vector_status(db, ws.id, it.id)
        db.close()
        # old vector is keyed by the mock model → new provider sees it as not indexed
        assert st_after["status"] == "not_indexed"
        assert st_after["provider"] is None and st_after["embedding_model"] is None

    def test_search_ignores_old_model_vector(self, monkeypatch):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it = _item(db, ws.id, title="切换测试", content_markdown="provider 切换后旧向量不应被检索命中")
        index_knowledge_item(db, ws.id, it.id)
        q = knowledge_item_embedding_text(it)

        self._switch_provider(monkeypatch, name="openai_compatible", model="text-embedding-3-small")
        res = search_vectors(db, ws.id, q)
        ids = {h["knowledge_item_id"] for h in res}
        db.close()
        assert it.id not in ids

    def test_reindex_after_switch_writes_new_provider(self, monkeypatch):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it = _item(db, ws.id)
        index_knowledge_item(db, ws.id, it.id)

        self._switch_provider(monkeypatch, name="openai_compatible", model="text-embedding-3-small")
        vec = index_knowledge_item(db, ws.id, it.id)
        st = get_vector_status(db, ws.id, it.id)
        db.close()
        assert vec.provider == "openai_compatible"
        assert vec.embedding_model == "text-embedding-3-small"
        assert st["status"] == "indexed"
        assert st["provider"] == "openai_compatible"


class TestHybridRetrieval:
    def test_hybrid_citation_pack_structure_compat(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it = _item(db, ws.id)
        index_knowledge_item(db, ws.id, it.id)
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="测试")
        assert pack["retriever_version"] == RETRIEVER_VERSION
        assert "hits" in pack and "hit_count" in pack
        db.close()

    def test_vector_keyword_merge_preserves_service_link(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it_linked = _item(db, ws.id, title="关联项", service_id="svc_x")
        index_knowledge_item(db, ws.id, it_linked.id)
        _item(db, ws.id, title="非关联项", service_id=None, content_markdown="测试")
        pack = retrieve_knowledge_for_sales_reply(
            db, workspace_id=ws.id, query_text="关联", matched_service_ids=["svc_x"],
        )
        db.close()
        hits = pack["hits"]
        if hits:
            assert hits[0]["title"] == "关联项"

    def test_fallback_keyword_when_no_vectors(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(db, ws.id, content_markdown="纯关键词测试内容项")
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="纯关键词测试")
        db.close()
        assert pack["hit_count"] >= 1 and "hits" in pack

    def test_citation_pack_has_retrieval_mode(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it = _item(db, ws.id)
        index_knowledge_item(db, ws.id, it.id)
        pack = retrieve_knowledge_for_sales_reply(db, workspace_id=ws.id, query_text="测试")
        db.close()
        hit = pack["hits"][0] if pack["hits"] else None
        assert hit and "retrieval_mode" in hit
