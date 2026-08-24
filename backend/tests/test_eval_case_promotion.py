"""Eval Case Promotion MVP tests (P6.13)."""

import uuid

import pytest
from starlette.testclient import TestClient

from app.db import SessionLocal, init_db
from app.models import KnowledgeItem, RetrievalEvalCase, Workspace
from app.services.eval_case_promotion import promote_eval_cases
from app.services.knowledge_improvement_suggestions import generate_improvement_suggestions
from app.services.retrieval_feedback import create_retrieval_feedback

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _workspace(db):
    ws = Workspace(slug=f"promote-{uuid.uuid4().hex[:8]}", name="Promotion WS", is_default=False)
    db.add(ws)
    db.flush()
    return ws


def _item(db, wid, **over):
    data = {
        "workspace_id": wid,
        "title": "企业知识库 PoC 验收标准",
        "summary": "知识库 PoC 验收应检查召回准确率。",
        "content_markdown": "企业知识库 PoC 验收标准包括高频问题覆盖、引用来源、召回准确率和人工 review。",
        "source_type": "delivery_sop",
        "status": "active",
        "tags_json": ["rag", "poc"],
    }
    data.update(over)
    item = KnowledgeItem(**data)
    db.add(item)
    db.commit()
    return item


def _feedback(db, wid, feedback_type, **over):
    data = {
        "feedback_type": feedback_type,
        "source": "manual_review",
        "query": "企业知识库 PoC 怎么验收",
        "note": "适合沉淀为回归评估用例",
    }
    data.update(over)
    return create_retrieval_feedback(db, wid, data, actor="admin@example.com")


class TestEvalCasePromotionService:
    def test_helpful_feedback_promotes_to_eval_case(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        fb = _feedback(db, ws.id, "helpful", knowledge_item_id=item.id)
        db.commit()

        result = promote_eval_cases(db, ws.id, {"feedback_ids": [fb.id]}, actor="admin@example.com")
        db.commit()
        case = db.query(RetrievalEvalCase).filter(RetrievalEvalCase.id == result["cases"][0].id).first()
        db.close()

        assert result["created_count"] == 1
        assert result["skipped_count"] == 0
        assert case.query == "企业知识库 PoC 怎么验收"
        assert case.expected_knowledge_item_ids == [item.id]
        assert "promoted" in case.tags_json
        assert "feedback" in (case.notes or "")

    def test_missing_feedback_with_expected_item_promotes_to_eval_case(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        expected = _item(db, ws.id, title="企业微信客服自动回复交付边界")
        fb = _feedback(
            db, ws.id, "missing",
            query="企业微信客服自动回复怎么做",
            expected_knowledge_item_id=expected.id,
        )
        db.commit()

        result = promote_eval_cases(db, ws.id, {"feedback_ids": [fb.id]}, actor="admin@example.com")
        db.commit()
        db.close()

        assert result["created_count"] == 1
        case = result["cases"][0]
        assert case.query == "企业微信客服自动回复怎么做"
        assert case.expected_knowledge_item_ids == [expected.id]

    def test_promote_eval_case_suggestion_creates_cases_and_marks_applied(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        _feedback(db, ws.id, "helpful", knowledge_item_id=item.id, query="知识库 PoC 验收")
        _feedback(db, ws.id, "helpful", knowledge_item_id=item.id, query="RAG 项目怎么验收")
        suggestion = generate_improvement_suggestions(db, ws.id, {})["suggestions"][0]
        db.commit()

        result = promote_eval_cases(db, ws.id, {"suggestion_id": suggestion.id}, actor="admin@example.com")
        db.commit()
        db.refresh(suggestion)
        db.close()

        assert result["created_count"] == 2
        assert {c.query for c in result["cases"]} == {"知识库 PoC 验收", "RAG 项目怎么验收"}
        assert all(c.expected_knowledge_item_ids == [item.id] for c in result["cases"])
        assert suggestion.status == "applied"
        assert suggestion.applied_at is not None
        assert len((suggestion.metadata_json or {}).get("promoted_eval_case_ids", [])) == 2

    def test_duplicate_promotion_skips_existing_active_case(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        fb = _feedback(db, ws.id, "helpful", knowledge_item_id=item.id)
        db.commit()

        first = promote_eval_cases(db, ws.id, {"feedback_ids": [fb.id]}, actor="admin@example.com")
        second = promote_eval_cases(db, ws.id, {"feedback_ids": [fb.id]}, actor="admin@example.com")
        cases = db.query(RetrievalEvalCase).filter(RetrievalEvalCase.workspace_id == ws.id).all()
        db.commit()
        db.close()

        assert first["created_count"] == 1
        assert second["created_count"] == 0
        assert second["skipped_count"] == 1
        assert len(cases) == 1

    def test_promotion_fail_closed_without_expected_item(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        fb = _feedback(db, ws.id, "missing", query="还没有知识覆盖的问题")
        db.commit()

        with pytest.raises(ValueError, match="expected knowledge item"):
            promote_eval_cases(db, ws.id, {"feedback_ids": [fb.id]}, actor="admin@example.com")
        db.close()


class TestEvalCasePromotionAPI:
    def test_promote_from_suggestion_api(self, client: TestClient):
        init_db()
        create_item = client.post(
            "/api/v1/admin/knowledge",
            json={
                "title": "RAG PoC 验收标准 API",
                "summary": "知识库 PoC 验收应检查召回准确率。",
                "content_markdown": "企业知识库 PoC 验收标准包括高频问题覆盖、引用来源、召回准确率和人工 review。",
                "source_type": "delivery_sop",
                "tags_json": ["rag", "poc"],
                "status": "active",
            },
            headers=ADMIN,
        )
        assert create_item.status_code == 201
        item_id = create_item.json()["id"]
        feedback_ids = []
        for query in ["企业知识库 PoC 怎么验收", "RAG 项目怎么验收"]:
            resp = client.post(
                "/api/v1/admin/knowledge/retrieval-feedback",
                json={
                    "feedback_type": "helpful",
                    "source": "manual_review",
                    "query": query,
                    "knowledge_item_id": item_id,
                },
                headers=ADMIN,
            )
            assert resp.status_code == 201
            feedback_ids.append(resp.json()["id"])

        generated = client.post("/api/v1/admin/knowledge/improvement-suggestions/generate", json={}, headers=ADMIN)
        assert generated.status_code == 201
        suggestion_id = generated.json()["suggestions"][0]["id"]

        promoted = client.post(
            "/api/v1/admin/knowledge/evaluations/cases/promote",
            json={"suggestion_id": suggestion_id},
            headers=ADMIN,
        )
        assert promoted.status_code == 201
        body = promoted.json()
        assert body["created_count"] == 2
        assert body["skipped_count"] == 0
        assert {c["query"] for c in body["cases"]} == {"企业知识库 PoC 怎么验收", "RAG 项目怎么验收"}
        for feedback_id in feedback_ids:
            resolved = client.patch(
                f"/api/v1/admin/knowledge/retrieval-feedback/{feedback_id}",
                json={"status": "resolved"},
                headers=ADMIN,
            )
            assert resolved.status_code == 200

    def test_unauthorized_promotion_api_is_rejected(self, client: TestClient):
        init_db()
        resp = client.post("/api/v1/admin/knowledge/evaluations/cases/promote", json={})
        assert resp.status_code in (401, 403)
