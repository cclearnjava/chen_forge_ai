"""Knowledge Change Validation MVP tests (P6.16)."""

import uuid

import pytest
from starlette.testclient import TestClient

from app.db import SessionLocal, init_db
from app.models import KnowledgeItem, RetrievalEvalCase, Workspace
from app.services.knowledge_change_validation import list_knowledge_validation_history, validate_knowledge_change
from app.services.retrieval_evaluation import run_retrieval_evaluation

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _workspace(db):
    ws = Workspace(slug=f"kcv-{uuid.uuid4().hex[:8]}", name="KCV WS", is_default=False)
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
        "tags_json": ["rag", "poc"],
        "status": "active",
    }
    data.update(over)
    item = KnowledgeItem(**data)
    db.add(item)
    db.commit()
    return item


def _case(db, wid, item_id, **over):
    data = {
        "workspace_id": wid,
        "query": "企业知识库 PoC 怎么验收",
        "expected_knowledge_item_ids": [item_id],
        "tags_json": ["validation"],
        "notes": "知识变更验证用例",
        "status": "active",
    }
    data.update(over)
    case = RetrievalEvalCase(**data)
    db.add(case)
    db.commit()
    return case


class TestKnowledgeChangeValidationService:
    def test_validate_runs_related_eval_cases(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        case = _case(db, ws.id, item.id)

        result = validate_knowledge_change(db, ws.id, item.id, {"k": 5})
        db.commit()
        db.close()

        assert result["case_count"] == 1
        assert result["case_ids"] == [case.id]
        assert result["run"].status == "completed"
        assert result["run"].case_count == 1
        assert len(result["results"]) == 1
        assert result["summary"]["passed_count"] == 1

    def test_validate_fail_closed_without_related_cases(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)

        with pytest.raises(ValueError, match="No active retrieval eval cases"):
            validate_knowledge_change(db, ws.id, item.id, {"k": 5})
        db.close()

    def test_cross_workspace_cases_are_not_used(self):
        init_db()
        db = SessionLocal()
        ws1 = _workspace(db)
        ws2 = _workspace(db)
        item = _item(db, ws1.id)
        _case(db, ws2.id, item.id)

        with pytest.raises(ValueError, match="No active retrieval eval cases"):
            validate_knowledge_change(db, ws1.id, item.id, {"k": 5})
        db.close()

    def test_history_lists_validation_runs_newest_first(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        _case(db, ws.id, item.id)

        first = validate_knowledge_change(db, ws.id, item.id, {"k": 5})
        second = validate_knowledge_change(db, ws.id, item.id, {"k": 5})
        db.commit()

        history = list_knowledge_validation_history(db, ws.id, item.id)
        db.close()

        assert [entry["run"].id for entry in history] == [second["run"].id, first["run"].id]
        assert history[0]["summary"]["passed_count"] == 1
        assert len(history[0]["results"]) == 1

    def test_history_excludes_regular_eval_runs(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        case = _case(db, ws.id, item.id)

        run_retrieval_evaluation(db, ws.id, case_ids=[case.id], k=5)
        db.commit()

        history = list_knowledge_validation_history(db, ws.id, item.id)
        db.close()

        assert history == []


class TestKnowledgeChangeValidationAPI:
    def test_validate_api(self, client: TestClient):
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
        create_case = client.post(
            "/api/v1/admin/knowledge/evaluations/cases",
            json={
                "query": "企业知识库 PoC 怎么验收",
                "expected_knowledge_item_ids": [item_id],
                "tags_json": ["validation"],
                "notes": "API validation",
            },
            headers=ADMIN,
        )
        assert create_case.status_code == 201

        resp = client.post(f"/api/v1/admin/knowledge/{item_id}/validate-retrieval", json={"k": 5}, headers=ADMIN)
        assert resp.status_code == 201
        body = resp.json()
        assert body["case_count"] == 1
        assert body["run"]["status"] == "completed"
        assert body["run"]["trigger_source"] == "knowledge_change_validation"
        assert body["run"]["knowledge_item_id"] == item_id
        assert body["summary"]["passed_count"] == 1

    def test_validation_history_api(self, client: TestClient):
        init_db()
        create_item = client.post(
            "/api/v1/admin/knowledge",
            json={
                "title": "RAG PoC 验证历史 API",
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
        create_case = client.post(
            "/api/v1/admin/knowledge/evaluations/cases",
            json={
                "query": "企业知识库 PoC 怎么验收",
                "expected_knowledge_item_ids": [item_id],
                "tags_json": ["validation"],
                "notes": "API validation history",
            },
            headers=ADMIN,
        )
        assert create_case.status_code == 201

        first = client.post(f"/api/v1/admin/knowledge/{item_id}/validate-retrieval", json={"k": 5}, headers=ADMIN)
        second = client.post(f"/api/v1/admin/knowledge/{item_id}/validate-retrieval", json={"k": 5}, headers=ADMIN)
        assert first.status_code == 201
        assert second.status_code == 201

        resp = client.get(f"/api/v1/admin/knowledge/{item_id}/validation-history", headers=ADMIN)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert [entry["run"]["id"] for entry in body["items"]] == [
            second.json()["run"]["id"],
            first.json()["run"]["id"],
        ]
        assert body["items"][0]["summary"]["passed_count"] == 1

    def test_unauthorized_validate_api_is_rejected(self, client: TestClient):
        init_db()
        resp = client.post("/api/v1/admin/knowledge/nope/validate-retrieval", json={})
        assert resp.status_code in (401, 403)
