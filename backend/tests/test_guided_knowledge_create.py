"""Guided Knowledge Create MVP tests (P6.15)."""

import uuid

import pytest
from starlette.testclient import TestClient

from app.db import SessionLocal, init_db
from app.models import KnowledgeItem, KnowledgeVector, Workspace
from app.services.guided_knowledge_create import apply_guided_knowledge_create
from app.services.knowledge_improvement_suggestions import generate_improvement_suggestions
from app.services.retrieval_feedback import create_retrieval_feedback

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _workspace(db):
    ws = Workspace(slug=f"gkc-{uuid.uuid4().hex[:8]}", name="Guided Create WS", is_default=False)
    db.add(ws)
    db.flush()
    return ws


def _create_knowledge_suggestion(db, wid, query="企业微信客服自动回复怎么做"):
    fb = create_retrieval_feedback(db, wid, {
        "feedback_type": "missing",
        "source": "manual_review",
        "query": query,
        "note": "当前知识库没有覆盖这个问题",
    }, actor="admin@example.com")
    fb.expected_knowledge_item_id = None
    suggestion = generate_improvement_suggestions(db, wid, {})["suggestions"][0]
    db.commit()
    return suggestion


class TestGuidedKnowledgeCreateService:
    def test_create_knowledge_item_from_create_knowledge_suggestion(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        suggestion = _create_knowledge_suggestion(db, ws.id)

        result = apply_guided_knowledge_create(db, ws.id, suggestion.id, {
            "item": {
                "title": "企业微信客服自动回复实施说明",
                "summary": "说明企业微信客服自动回复的适用场景和实施边界。",
                "content_markdown": "企业微信客服自动回复适合高频咨询、预约和售后状态查询。",
                "source_type": "service_note",
                "tags_json": ["企业微信", "客服", "自动回复"],
                "status": "active",
            },
            "reindex": False,
        }, actor="admin@example.com")
        db.commit()
        db.refresh(suggestion)
        db.close()

        item = result["item"]
        assert item.title == "企业微信客服自动回复实施说明"
        assert item.workspace_id == ws.id
        assert item.status == "active"
        assert suggestion.status == "applied"
        assert suggestion.applied_at is not None
        assert (suggestion.metadata_json or {})["guided_create"]["knowledge_item_id"] == item.id
        assert result["vector_status"] is None

    def test_create_knowledge_can_reindex_active_item(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        suggestion = _create_knowledge_suggestion(db, ws.id)

        result = apply_guided_knowledge_create(db, ws.id, suggestion.id, {
            "item": {
                "title": "RAG 客服自动回复 FAQ",
                "summary": "FAQ",
                "content_markdown": "用于回答企业微信客服自动回复相关问题。",
                "source_type": "faq",
                "tags_json": ["rag"],
                "status": "active",
            },
            "reindex": True,
        }, actor="admin@example.com")
        db.commit()
        vec = db.query(KnowledgeVector).filter(KnowledgeVector.knowledge_item_id == result["item"].id).first()
        db.close()

        assert result["vector_status"]["status"] == "indexed"
        assert vec is not None
        assert vec.status == "indexed"

    def test_non_create_knowledge_suggestion_is_rejected(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = KnowledgeItem(
            workspace_id=ws.id,
            title="已有知识",
            summary="旧摘要",
            content_markdown="旧正文",
            source_type="manual",
            status="active",
            tags_json=["old"],
        )
        db.add(item)
        db.commit()
        create_retrieval_feedback(db, ws.id, {
            "feedback_type": "outdated",
            "source": "manual_review",
            "query": "已有知识怎么更新",
            "knowledge_item_id": item.id,
        }, actor="admin@example.com")
        suggestion = generate_improvement_suggestions(db, ws.id, {})["suggestions"][0]
        db.commit()

        with pytest.raises(ValueError, match="does not support guided create"):
            apply_guided_knowledge_create(db, ws.id, suggestion.id, {
                "item": {
                    "title": "新知识",
                    "content_markdown": "新正文",
                    "source_type": "manual",
                    "status": "active",
                },
            }, actor="admin@example.com")
        db.close()


class TestGuidedKnowledgeCreateAPI:
    def test_apply_guided_create_api(self, client: TestClient):
        init_db()
        feedback = client.post(
            "/api/v1/admin/knowledge/retrieval-feedback",
            json={
                "feedback_type": "missing",
                "source": "manual_review",
                "query": "企业微信客服自动回复怎么做",
            },
            headers=ADMIN,
        )
        assert feedback.status_code == 201
        feedback_id = feedback.json()["id"]
        generated = client.post("/api/v1/admin/knowledge/improvement-suggestions/generate", json={}, headers=ADMIN)
        assert generated.status_code == 201
        suggestion_id = generated.json()["suggestions"][0]["id"]

        applied = client.post(
            f"/api/v1/admin/knowledge/improvement-suggestions/{suggestion_id}/create-knowledge",
            json={
                "item": {
                    "title": "企业微信客服自动回复 FAQ",
                    "summary": "企业微信客服自动回复常见问题。",
                    "content_markdown": "企业微信客服自动回复适合高频咨询和标准化售后问题。",
                    "source_type": "faq",
                    "tags_json": ["企业微信", "客服"],
                    "status": "active",
                },
                "reindex": False,
            },
            headers=ADMIN,
        )
        assert applied.status_code == 201
        body = applied.json()
        assert body["item"]["title"] == "企业微信客服自动回复 FAQ"
        assert body["suggestion"]["status"] == "applied"
        assert body["vector_status"] is None
        resolved = client.patch(
            f"/api/v1/admin/knowledge/retrieval-feedback/{feedback_id}",
            json={"status": "resolved"},
            headers=ADMIN,
        )
        assert resolved.status_code == 200

    def test_unauthorized_guided_create_api_is_rejected(self, client: TestClient):
        init_db()
        resp = client.post("/api/v1/admin/knowledge/improvement-suggestions/nope/create-knowledge", json={})
        assert resp.status_code in (401, 403)
