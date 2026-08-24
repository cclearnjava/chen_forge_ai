"""Knowledge Improvement Suggestions MVP tests (P6.12)."""

import uuid

from starlette.testclient import TestClient

from app.db import SessionLocal, init_db
from app.models import KnowledgeItem, Workspace
from app.services.knowledge_improvement_suggestions import (
    generate_improvement_suggestions,
    list_improvement_suggestions,
    update_improvement_suggestion,
)
from app.services.retrieval_feedback import create_retrieval_feedback

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _workspace(db):
    ws = Workspace(slug=f"kis-{uuid.uuid4().hex[:8]}", name="KIS WS", is_default=False)
    db.add(ws)
    db.flush()
    return ws


def _item(db, wid, **over):
    data = {
        "workspace_id": wid,
        "title": "企业知识库 PoC 验收标准",
        "summary": "RAG 验收应看召回准确率和引用来源。",
        "content_markdown": "企业知识库 PoC 验收包括高频问题覆盖、引用质量、召回准确率和人工 review。",
        "source_type": "delivery_sop",
        "status": "active",
        "tags_json": ["rag", "验收"],
    }
    data.update(over)
    it = KnowledgeItem(**data)
    db.add(it)
    db.commit()
    return it


def _feedback(db, wid, feedback_type, **over):
    item_id = over.pop("knowledge_item_id", None)
    expected_id = over.pop("expected_knowledge_item_id", None)
    data = {
        "feedback_type": feedback_type,
        "source": "retrieval_evaluation_result",
        "query": "企业知识库 PoC 怎么验收",
        "note": "样例反馈",
    }
    if feedback_type == "missing":
        if expected_id:
            data["expected_knowledge_item_id"] = expected_id
    else:
        data["knowledge_item_id"] = item_id
    data.update(over)
    return create_retrieval_feedback(db, wid, data, actor="admin@example.com")


class TestKnowledgeImprovementSuggestionService:
    def test_irrelevant_feedback_generates_improve_metadata(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id, title="企业知识库报价规则")
        _feedback(db, ws.id, "irrelevant", knowledge_item_id=item.id, note="这是报价规则，不适合验收问题")
        db.commit()

        result = generate_improvement_suggestions(db, ws.id, {})
        db.commit()
        db.close()

        assert result["created_count"] == 1
        suggestion = result["suggestions"][0]
        assert suggestion.suggestion_type == "improve_metadata"
        assert suggestion.knowledge_item_id == item.id
        assert suggestion.evidence_json["feedback_count"] == 1

    def test_outdated_feedback_generates_update_content(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id, title="RAG PoC 交付周期")
        _feedback(db, ws.id, "outdated", knowledge_item_id=item.id, note="交付周期已经从 2 周改成 3 周")
        db.commit()

        result = generate_improvement_suggestions(db, ws.id, {})
        db.commit()
        db.close()

        assert result["suggestions"][0].suggestion_type == "update_content"
        assert "更新" in result["suggestions"][0].recommended_action

    def test_missing_with_expected_item_generates_improve_retrievability(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        expected = _item(db, ws.id, title="企业微信客服自动回复交付边界")
        _feedback(
            db, ws.id, "missing",
            expected_knowledge_item_id=expected.id,
            query="企业微信客服自动回复怎么做",
        )
        db.commit()

        result = generate_improvement_suggestions(db, ws.id, {})
        db.commit()
        db.close()

        suggestion = result["suggestions"][0]
        assert suggestion.suggestion_type == "improve_retrievability"
        assert suggestion.knowledge_item_id == expected.id

    def test_missing_without_expected_item_generates_create_knowledge(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        fb = _feedback(db, ws.id, "missing", query="企业微信客服自动回复怎么做")
        fb.expected_knowledge_item_id = None
        db.commit()

        result = generate_improvement_suggestions(db, ws.id, {})
        db.commit()
        db.close()

        suggestion = result["suggestions"][0]
        assert suggestion.suggestion_type == "create_knowledge"
        assert suggestion.knowledge_item_id is None
        assert "企业微信客服自动回复" in suggestion.title

    def test_helpful_feedback_threshold_generates_promote_eval_case(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        _feedback(db, ws.id, "helpful", knowledge_item_id=item.id, query="知识库 PoC 验收")
        _feedback(db, ws.id, "helpful", knowledge_item_id=item.id, query="RAG 项目怎么验收")
        db.commit()

        result = generate_improvement_suggestions(db, ws.id, {})
        db.commit()
        db.close()

        assert result["created_count"] == 1
        assert result["suggestions"][0].suggestion_type == "promote_eval_case"

    def test_open_suggestion_is_deduplicated_and_evidence_updated(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        _feedback(db, ws.id, "irrelevant", knowledge_item_id=item.id, query="问题 A")
        db.commit()
        first = generate_improvement_suggestions(db, ws.id, {})
        _feedback(db, ws.id, "irrelevant", knowledge_item_id=item.id, query="问题 B")
        second = generate_improvement_suggestions(db, ws.id, {})
        suggestions = list_improvement_suggestions(db, ws.id, {})
        db.commit()
        db.close()

        assert first["created_count"] == 1
        assert second["created_count"] == 0
        assert second["updated_count"] == 1
        assert len(suggestions) == 1
        assert suggestions[0].evidence_json["feedback_count"] == 2

    def test_dismissed_suggestion_allows_new_suggestion(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        _feedback(db, ws.id, "irrelevant", knowledge_item_id=item.id, query="问题 A")
        first = generate_improvement_suggestions(db, ws.id, {})
        update_improvement_suggestion(db, ws.id, first["suggestions"][0].id, {"status": "dismissed"})
        _feedback(db, ws.id, "irrelevant", knowledge_item_id=item.id, query="问题 B")
        second = generate_improvement_suggestions(db, ws.id, {})
        suggestions = list_improvement_suggestions(db, ws.id, {})
        db.commit()
        db.close()

        assert second["created_count"] == 1
        assert len(suggestions) == 2

    def test_cross_workspace_feedback_not_included(self):
        init_db()
        db = SessionLocal()
        ws1 = _workspace(db)
        ws2 = _workspace(db)
        item2 = _item(db, ws2.id)
        _feedback(db, ws2.id, "irrelevant", knowledge_item_id=item2.id)
        db.commit()

        result = generate_improvement_suggestions(db, ws1.id, {})
        db.close()

        assert result["created_count"] == 0
        assert result["suggestions"] == []

    def test_update_status_sets_timestamps(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        _feedback(db, ws.id, "outdated", knowledge_item_id=item.id)
        result = generate_improvement_suggestions(db, ws.id, {})
        suggestion = result["suggestions"][0]

        accepted = update_improvement_suggestion(db, ws.id, suggestion.id, {"status": "accepted"})
        dismissed = update_improvement_suggestion(db, ws.id, suggestion.id, {"status": "dismissed"})
        applied = update_improvement_suggestion(db, ws.id, suggestion.id, {"status": "applied"})
        archived = update_improvement_suggestion(db, ws.id, suggestion.id, {"status": "archived"})
        db.commit()
        db.close()

        assert accepted.accepted_at is not None
        assert dismissed.dismissed_at is not None
        assert applied.applied_at is not None
        assert archived.archived_at is not None


class TestKnowledgeImprovementSuggestionAPI:
    def test_generate_list_and_update_suggestion_api(self, client: TestClient):
        init_db()
        create_item = client.post(
            "/api/v1/admin/knowledge",
            json={
                "title": "企业知识库报价规则",
                "summary": "报价规则摘要",
                "content_markdown": "报价规则内容",
                "source_type": "pricing_rule",
                "tags_json": ["报价"],
                "status": "active",
            },
            headers=ADMIN,
        )
        assert create_item.status_code == 201
        item_id = create_item.json()["id"]
        feedback = client.post(
            "/api/v1/admin/knowledge/retrieval-feedback",
            json={
                "feedback_type": "irrelevant",
                "source": "retrieval_evaluation_result",
                "query": "企业知识库 PoC 怎么验收",
                "knowledge_item_id": item_id,
            },
            headers=ADMIN,
        )
        assert feedback.status_code == 201
        feedback_id = feedback.json()["id"]

        generated = client.post("/api/v1/admin/knowledge/improvement-suggestions/generate", json={}, headers=ADMIN)
        assert generated.status_code == 201
        body = generated.json()
        assert body["created_count"] == 1
        sid = body["suggestions"][0]["id"]

        listing = client.get("/api/v1/admin/knowledge/improvement-suggestions?status=open&suggestion_type=improve_metadata", headers=ADMIN)
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

        patched = client.patch(
            f"/api/v1/admin/knowledge/improvement-suggestions/{sid}",
            json={"status": "applied"},
            headers=ADMIN,
        )
        assert patched.status_code == 200
        assert patched.json()["status"] == "applied"
        assert patched.json()["applied_at"] is not None

        resolved_feedback = client.patch(
            f"/api/v1/admin/knowledge/retrieval-feedback/{feedback_id}",
            json={"status": "resolved"},
            headers=ADMIN,
        )
        assert resolved_feedback.status_code == 200

    def test_unauthorized_suggestion_api_is_rejected(self, client: TestClient):
        init_db()
        resp = client.get("/api/v1/admin/knowledge/improvement-suggestions")
        assert resp.status_code in (401, 403)
