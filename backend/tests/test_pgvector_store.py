"""pgvector store tests (P6.8) — no real Postgres required.

Covers config default, fail-fast on misconfiguration, SQL construction, and the
search fallback-to-empty behaviour that lets the Hybrid Retriever degrade to keyword.
"""

import uuid
import pytest
from starlette.testclient import TestClient
from app.config import settings
from app.db import SessionLocal, init_db
from app.models import KnowledgeItem, Workspace
from app.services import knowledge_vectors as kv

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _workspace(db):
    ws = Workspace(slug=f"pgv-{uuid.uuid4().hex[:8]}", name="PGV WS", is_default=False)
    db.add(ws); db.flush()
    return ws


def _item(db, wid, **over):
    defaults = {"title": f"pgv-{uuid.uuid4().hex[:4]}",
                "content_markdown": "pgvector 测试正文，足够长以通过质量与切分阈值检查。",
                "status": "active", "workspace_id": wid}
    defaults.update(over)
    it = KnowledgeItem(**defaults)
    db.add(it); db.commit()
    return it


@pytest.fixture
def pgvector_mode(monkeypatch):
    monkeypatch.setattr(settings, "vector_store", "pgvector")
    yield


class TestConfigDefault:
    def test_default_store_is_sqlite_json(self):
        assert settings.vector_store == "sqlite_json"


class TestFailFast:
    def test_index_on_sqlite_fails_fast(self, pgvector_mode):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it = _item(db, ws.id)
        with pytest.raises(ValueError, match="requires PostgreSQL"):
            kv.index_knowledge_item(db, ws.id, it.id)
        db.close()

    def test_index_fail_fast_writes_failed_status(self, pgvector_mode):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it = _item(db, ws.id)
        try:
            kv.index_knowledge_item(db, ws.id, it.id)
        except ValueError:
            pass
        st = kv.get_vector_status(db, ws.id, it.id)
        db.close()
        assert st["status"] == "failed"
        assert "PostgreSQL" in (st["error_message"] or "")

    def test_dim_zero_fails_fast(self, monkeypatch):
        # Force a "postgres" dialect so the dim check is reached, keep EMBEDDING_DIM=0
        monkeypatch.setattr(settings, "vector_store", "pgvector")
        monkeypatch.setattr(settings, "embedding_dim", 0)
        monkeypatch.setattr(kv, "_dialect_name", lambda db: "postgresql")
        with pytest.raises(ValueError, match="EMBEDDING_DIM"):
            kv._validate_pgvector_config(object())

    def test_valid_pg_config_passes(self, monkeypatch):
        monkeypatch.setattr(settings, "vector_store", "pgvector")
        monkeypatch.setattr(settings, "embedding_dim", 1536)
        monkeypatch.setattr(kv, "_dialect_name", lambda db: "postgresql")
        kv._validate_pgvector_config(object())  # should not raise

    def test_pgvector_write_failure_marks_vector_failed(self, monkeypatch):
        monkeypatch.setattr(settings, "vector_store", "pgvector")
        monkeypatch.setattr(settings, "embedding_dim", 64)
        monkeypatch.setattr(kv, "_dialect_name", lambda db: "postgresql")

        def fail_write(db, vec_id, vector):
            raise RuntimeError("pgvector extension is not enabled")

        monkeypatch.setattr(kv, "_upsert_pgvector_embedding", fail_write)

        init_db(); db = SessionLocal()
        ws = _workspace(db)
        it = _item(db, ws.id)
        with pytest.raises(ValueError, match="pgvector write failed"):
            kv.index_knowledge_item(db, ws.id, it.id)
        st = kv.get_vector_status(db, ws.id, it.id)
        db.close()
        assert st["status"] == "failed"
        assert "pgvector extension is not enabled" in (st["error_message"] or "")

    def test_reindex_api_preserves_failed_status(self, monkeypatch, client: TestClient):
        monkeypatch.setattr(settings, "vector_store", "pgvector")
        monkeypatch.setattr(settings, "embedding_dim", 64)
        monkeypatch.setattr(kv, "_dialect_name", lambda db: "postgresql")

        def fail_write(db, vec_id, vector):
            raise RuntimeError("pgvector extension is not enabled")

        monkeypatch.setattr(kv, "_upsert_pgvector_embedding", fail_write)

        create = client.post(
            "/api/v1/admin/knowledge",
            json={
                "title": f"pgv-api-{uuid.uuid4().hex[:4]}",
                "content_markdown": "pgvector API 失败状态测试正文，足够长以通过质量检查。",
                "status": "active",
            },
            headers=ADMIN,
        )
        assert create.status_code == 201
        item_id = create.json()["id"]

        res = client.post(f"/api/v1/admin/knowledge/{item_id}/vector/reindex", headers=ADMIN)
        assert res.status_code == 422

        status = client.get(f"/api/v1/admin/knowledge/{item_id}/vector", headers=ADMIN)
        assert status.status_code == 200
        body = status.json()
        assert body["status"] == "failed"
        assert "pgvector extension is not enabled" in (body["error_message"] or "")


class TestSearchSQL:
    def test_sql_has_isolation_filters(self):
        sql = kv._pgvector_search_sql()
        for token in ["kv.workspace_id = :ws", "kv.status = 'indexed'",
                      "kv.embedding_model = :model", "ki.status = 'active'",
                      "kv.embedding_vector <=>", "LIMIT :limit"]:
            assert token in sql

    def test_sql_has_no_stale_filter(self):
        # parity with sqlite path — stale is a display concern, not a search filter
        assert "content_hash" not in kv._pgvector_search_sql()

    def test_vector_literal_format(self):
        assert kv._vector_to_pg_literal([0.1, 0.2, 0.3]) == "[0.1,0.2,0.3]"


class TestSearchFallback:
    def test_pgvector_search_on_sqlite_returns_empty(self, pgvector_mode):
        # sqlite has no vector type / embedding_vector column → query errors → []
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _item(db, ws.id)
        res = kv.search_vectors(db, ws.id, "任意查询文本")
        db.close()
        assert res == []
