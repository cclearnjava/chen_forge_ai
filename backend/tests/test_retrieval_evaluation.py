"""Knowledge Retrieval Evaluation MVP tests (P6.9)."""

import uuid

import pytest
from starlette.testclient import TestClient

from app.db import SessionLocal, init_db
from app.models import KnowledgeItem, Workspace
from app.services.retrieval_evaluation import (
    compute_retrieval_metrics,
    create_eval_case,
    run_retrieval_evaluation,
)

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _workspace(db):
    ws = Workspace(slug=f"eval-{uuid.uuid4().hex[:8]}", name="Eval WS", is_default=False)
    db.add(ws)
    db.flush()
    return ws


def _item(db, wid, **over):
    defaults = {
        "title": f"RAG PoC 验收标准 {uuid.uuid4().hex[:4]}",
        "summary": "RAG PoC 应覆盖高频问题、引用质量和命中率验收。",
        "content_markdown": "企业知识库 PoC 验收时，需要检查高频问题覆盖率、引用来源、召回准确率和错误召回样本。",
        "source_type": "delivery_sop",
        "status": "active",
        "tags_json": ["rag", "poc", "验收"],
        "workspace_id": wid,
    }
    defaults.update(over)
    it = KnowledgeItem(**defaults)
    db.add(it)
    db.commit()
    return it


class TestRetrievalEvalMetrics:
    def test_metrics_calculate_recall_and_precision(self):
        metrics = compute_retrieval_metrics(
            expected_ids=["ki_1", "ki_2"],
            actual_ids=["ki_1", "ki_3", "ki_4"],
        )
        assert metrics["matched_expected_ids"] == ["ki_1"]
        assert metrics["missed_expected_ids"] == ["ki_2"]
        assert metrics["extra_hit_ids"] == ["ki_3", "ki_4"]
        assert metrics["recall_at_k"] == 0.5
        assert metrics["precision_at_k"] == pytest.approx(1 / 3)


class TestRetrievalEvaluationService:
    def test_run_eval_case_records_passed_result(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        expected = _item(db, ws.id, title="企业知识库 PoC 验收标准")
        case = create_eval_case(db, ws.id, {
            "query": "企业知识库 PoC 怎么验收",
            "expected_knowledge_item_ids": [expected.id],
            "tags_json": ["rag"],
            "notes": "应命中验收标准",
        })
        run = run_retrieval_evaluation(db, ws.id, case_ids=[case.id], k=5)
        db.close()

        assert run.status == "completed"
        assert run.case_count == 1
        assert run.average_recall_at_k == 1.0
        assert run.miss_count == 0
        assert len(run.results) == 1
        result = run.results[0]
        assert result.status == "passed"
        assert expected.id in result.matched_expected_ids
        assert result.citation_pack_json["hit_count"] >= 1

    def test_cross_workspace_expected_item_rejected(self):
        init_db()
        db = SessionLocal()
        ws1 = _workspace(db)
        ws2 = _workspace(db)
        foreign = _item(db, ws2.id)
        with pytest.raises(ValueError, match="does not belong to this workspace"):
            create_eval_case(db, ws1.id, {
                "query": "跨 workspace 资料",
                "expected_knowledge_item_ids": [foreign.id],
            })
        db.close()


class TestRetrievalEvaluationAPI:
    def test_case_run_and_detail_api(self, client: TestClient):
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
                "tags_json": ["rag"],
                "notes": "API smoke",
            },
            headers=ADMIN,
        )
        assert create_case.status_code == 201
        case_id = create_case.json()["id"]

        run_resp = client.post(
            "/api/v1/admin/knowledge/evaluations/runs",
            json={"case_ids": [case_id], "k": 5},
            headers=ADMIN,
        )
        assert run_resp.status_code == 201
        run = run_resp.json()
        assert run["status"] == "completed"
        assert run["case_count"] == 1
        assert run["average_recall_at_k"] == 1.0

        detail = client.get(f"/api/v1/admin/knowledge/evaluations/runs/{run['id']}", headers=ADMIN)
        assert detail.status_code == 200
        body = detail.json()
        assert body["run"]["id"] == run["id"]
        assert body["results"][0]["case_id"] == case_id
        assert item_id in body["results"][0]["matched_expected_ids"]
