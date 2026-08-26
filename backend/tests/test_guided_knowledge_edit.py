"""Guided Knowledge Edit MVP tests (P6.14)."""

import uuid

import pytest
from starlette.testclient import TestClient

from app.db import SessionLocal, init_db
from app.models import KnowledgeItem, KnowledgeVector, Workspace
from app.services.guided_knowledge_edit import apply_guided_knowledge_edit
from app.services.knowledge_improvement_suggestions import generate_improvement_suggestions
from app.services.knowledge_vectors import compute_content_hash, index_knowledge_item
from app.services.retrieval_feedback import create_retrieval_feedback

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _workspace(db):
    ws = Workspace(slug=f"gke-{uuid.uuid4().hex[:8]}", name="Guided Edit WS", is_default=False)
    db.add(ws)
    db.flush()
    return ws


def _item(db, wid, **over):
    data = {
        "workspace_id": wid,
        "title": "企业知识库 PoC 验收标准",
        "summary": "旧版验收标准摘要。",
        "content_markdown": "旧版验收标准只检查引用来源。",
        "source_type": "delivery_sop",
        "status": "active",
        "tags_json": ["rag"],
    }
    data.update(over)
    item = KnowledgeItem(**data)
    db.add(item)
    db.commit()
    return item


def _feedback(db, wid, feedback_type, item_id, **over):
    data = {
        "feedback_type": feedback_type,
        "source": "manual_review",
        "query": "企业知识库 PoC 怎么验收",
        "knowledge_item_id": item_id,
        "note": "需要人工更新知识条目",
    }
    data.update(over)
    return create_retrieval_feedback(db, wid, data, actor="admin@example.com")


def _suggestion(db, wid, item_id, feedback_type="outdated"):
    _feedback(db, wid, feedback_type, item_id)
    result = generate_improvement_suggestions(db, wid, {})
    db.commit()
    return result["suggestions"][0]


class TestGuidedKnowledgeEditService:
    def test_apply_edit_updates_knowledge_item_and_marks_suggestion_applied(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        suggestion = _suggestion(db, ws.id, item.id, "outdated")

        result = apply_guided_knowledge_edit(db, ws.id, suggestion.id, {
            "patch": {
                "summary": "新版验收标准摘要。",
                "content_markdown": "新版验收标准包括高频问题覆盖、引用质量和召回准确率。",
                "tags_json": ["rag", "验收", "poc"],
            },
            "reindex": False,
        }, actor="admin@example.com")
        db.commit()
        db.refresh(item)
        db.refresh(suggestion)
        db.close()

        assert result["item"].id == item.id
        assert item.summary == "新版验收标准摘要。"
        assert "召回准确率" in item.content_markdown
        assert item.tags_json == ["rag", "验收", "poc"]
        assert suggestion.status == "applied"
        assert suggestion.applied_at is not None
        assert (suggestion.metadata_json or {})["guided_edit"]["changed_fields"] == [
            "summary", "content_markdown", "tags_json",
        ]
        assert result["vector_status"] is None

    def test_apply_edit_can_reindex_active_item(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        index_knowledge_item(db, ws.id, item.id)
        db.commit()
        before_hash = compute_content_hash(item)
        suggestion = _suggestion(db, ws.id, item.id, "outdated")

        result = apply_guided_knowledge_edit(db, ws.id, suggestion.id, {
            "patch": {"content_markdown": "新版内容会触发重新索引。"},
            "reindex": True,
        }, actor="admin@example.com")
        db.commit()
        db.refresh(item)
        vec = db.query(KnowledgeVector).filter(KnowledgeVector.knowledge_item_id == item.id).first()
        db.close()

        assert result["vector_status"]["status"] == "indexed"
        assert vec.content_hash == compute_content_hash(item)
        assert vec.content_hash != before_hash

    def test_non_edit_suggestion_type_is_rejected(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        _feedback(db, ws.id, "helpful", item.id, query="知识库 PoC 验收")
        _feedback(db, ws.id, "helpful", item.id, query="RAG 项目怎么验收")
        suggestion = generate_improvement_suggestions(db, ws.id, {})["suggestions"][0]
        db.commit()

        with pytest.raises(ValueError, match="does not support guided edit"):
            apply_guided_knowledge_edit(db, ws.id, suggestion.id, {"patch": {"summary": "x"}}, actor="admin@example.com")
        db.close()

    def test_create_knowledge_suggestion_is_rejected(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        fb = create_retrieval_feedback(db, ws.id, {
            "feedback_type": "missing",
            "source": "manual_review",
            "query": "没有知识覆盖的问题",
        }, actor="admin@example.com")
        fb.expected_knowledge_item_id = None
        suggestion = generate_improvement_suggestions(db, ws.id, {})["suggestions"][0]
        db.commit()

        with pytest.raises(ValueError, match="does not support guided edit"):
            apply_guided_knowledge_edit(db, ws.id, suggestion.id, {"patch": {"summary": "x"}}, actor="admin@example.com")
        db.close()


class TestGuidedKnowledgeEditAPI:
    def test_apply_guided_edit_api(self, client: TestClient):
        init_db()
        create_item = client.post(
            "/api/v1/admin/knowledge",
            json={
                "title": "RAG PoC 验收标准 API",
                "summary": "旧摘要",
                "content_markdown": "旧正文",
                "source_type": "delivery_sop",
                "tags_json": ["rag"],
                "status": "active",
            },
            headers=ADMIN,
        )
        assert create_item.status_code == 201
        item_id = create_item.json()["id"]
        feedback = client.post(
            "/api/v1/admin/knowledge/retrieval-feedback",
            json={
                "feedback_type": "outdated",
                "source": "manual_review",
                "query": "企业知识库 PoC 怎么验收",
                "knowledge_item_id": item_id,
            },
            headers=ADMIN,
        )
        assert feedback.status_code == 201
        feedback_id = feedback.json()["id"]
        generated = client.post("/api/v1/admin/knowledge/improvement-suggestions/generate", json={}, headers=ADMIN)
        assert generated.status_code == 201
        suggestion_id = generated.json()["suggestions"][0]["id"]

        applied = client.post(
            f"/api/v1/admin/knowledge/improvement-suggestions/{suggestion_id}/apply-knowledge-edit",
            json={
                "patch": {
                    "summary": "新摘要",
                    "content_markdown": "新正文包含召回准确率。",
                    "tags_json": ["rag", "验收"],
                },
                "reindex": False,
            },
            headers=ADMIN,
        )
        assert applied.status_code == 200
        body = applied.json()
        assert body["item"]["summary"] == "新摘要"
        assert body["suggestion"]["status"] == "applied"
        assert body["vector_status"] is None
        resolved = client.patch(
            f"/api/v1/admin/knowledge/retrieval-feedback/{feedback_id}",
            json={"status": "resolved"},
            headers=ADMIN,
        )
        assert resolved.status_code == 200

    def test_unauthorized_guided_edit_api_is_rejected(self, client: TestClient):
        init_db()
        resp = client.post("/api/v1/admin/knowledge/improvement-suggestions/nope/apply-knowledge-edit", json={})
        assert resp.status_code in (401, 403)
