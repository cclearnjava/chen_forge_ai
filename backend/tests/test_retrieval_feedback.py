"""Retrieval Feedback Loop MVP tests (P6.11)."""

import uuid

import pytest
from starlette.testclient import TestClient

from app.db import SessionLocal, init_db
from app.models import (
    Artifact,
    ArtifactType,
    Customer,
    KnowledgeItem,
    Opportunity,
    RetrievalEvalResult,
    RetrievalEvalRun,
    Workspace,
)
from app.services.retrieval_feedback import (
    create_retrieval_feedback,
    list_retrieval_feedback,
    update_retrieval_feedback,
)

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _workspace(db):
    ws = Workspace(slug=f"rf-{uuid.uuid4().hex[:8]}", name="Retrieval Feedback WS", is_default=False)
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


def _artifact(db, wid, **over):
    data = {
        "workspace_id": wid,
        "type": ArtifactType.customer_reply_draft,
        "title": "客户回复草稿",
        "content_markdown": "建议先做知识库 PoC。",
        "content_json": {},
        "model": "mock",
        "prompt_version": "v1",
        "requires_approval": True,
    }
    data.update(over)
    artifact = Artifact(**data)
    db.add(artifact)
    db.commit()
    return artifact


def _opportunity(db, wid, **over):
    customer = Customer(workspace_id=wid, name="陈记连锁门店", owner_email="owner@example.com")
    db.add(customer)
    db.flush()
    data = {
        "workspace_id": wid,
        "customer_id": customer.id,
        "title": "企业知识库 PoC",
    }
    data.update(over)
    opp = Opportunity(**data)
    db.add(opp)
    db.commit()
    return opp


def _eval_result(db, wid, item_id):
    run = RetrievalEvalRun(workspace_id=wid, status="completed", case_count=1, k=5)
    db.add(run)
    db.flush()
    result = RetrievalEvalResult(
        workspace_id=wid,
        run_id=run.id,
        case_id=str(uuid.uuid4()),
        query="企业知识库 PoC 怎么验收",
        expected_knowledge_item_ids=[item_id],
        actual_knowledge_item_ids=[item_id],
        matched_expected_ids=[item_id],
        missed_expected_ids=[],
        extra_hit_ids=[],
        recall_at_k=1.0,
        precision_at_k=1.0,
        hit_count=1,
        citation_pack_json={"hits": [{"knowledge_item_id": item_id, "title": "企业知识库 PoC 验收标准"}]},
        status="passed",
    )
    db.add(result)
    db.commit()
    return result


class TestRetrievalFeedbackService:
    def test_create_helpful_feedback_records_open_status(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        fb = create_retrieval_feedback(db, ws.id, {
            "feedback_type": "helpful",
            "source": "sales_reply_citation",
            "query": "企业知识库 PoC 怎么验收",
            "knowledge_item_id": item.id,
            "citation_hit_json": {"knowledge_item_id": item.id, "title": item.title},
        }, actor="admin@example.com")
        db.commit()
        db.close()

        assert fb.status == "open"
        assert fb.feedback_type == "helpful"
        assert fb.knowledge_item_id == item.id
        assert fb.created_by == "admin@example.com"

    def test_create_missing_feedback_allows_expected_item(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        expected = _item(db, ws.id)
        fb = create_retrieval_feedback(db, ws.id, {
            "feedback_type": "missing",
            "source": "retrieval_evaluation_result",
            "query": "企业微信自动回复怎么做",
            "expected_knowledge_item_id": expected.id,
            "note": "应该命中这条验收资料",
        }, actor="admin@example.com")
        db.commit()
        db.close()

        assert fb.feedback_type == "missing"
        assert fb.expected_knowledge_item_id == expected.id
        assert fb.knowledge_item_id is None

    def test_non_missing_feedback_requires_knowledge_item(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        with pytest.raises(ValueError, match="knowledge_item_id is required"):
            create_retrieval_feedback(db, ws.id, {
                "feedback_type": "irrelevant",
                "source": "sales_reply_citation",
                "query": "企业知识库 PoC",
            }, actor="admin@example.com")
        db.close()

    def test_cross_workspace_knowledge_item_is_rejected(self):
        init_db()
        db = SessionLocal()
        ws1 = _workspace(db)
        ws2 = _workspace(db)
        foreign = _item(db, ws2.id)
        with pytest.raises(ValueError, match="knowledge_item_id does not belong"):
            create_retrieval_feedback(db, ws1.id, {
                "feedback_type": "helpful",
                "source": "sales_reply_citation",
                "knowledge_item_id": foreign.id,
            }, actor="admin@example.com")
        db.close()

    def test_related_objects_must_belong_to_workspace(self):
        init_db()
        db = SessionLocal()
        ws1 = _workspace(db)
        ws2 = _workspace(db)
        item = _item(db, ws1.id)
        foreign_artifact = _artifact(db, ws2.id)
        foreign_opp = _opportunity(db, ws2.id)
        foreign_result = _eval_result(db, ws2.id, _item(db, ws2.id).id)

        for field, value in [
            ("artifact_id", foreign_artifact.id),
            ("opportunity_id", foreign_opp.id),
            ("retrieval_eval_result_id", foreign_result.id),
        ]:
            with pytest.raises(ValueError, match=f"{field} does not belong"):
                create_retrieval_feedback(db, ws1.id, {
                    "feedback_type": "helpful",
                    "source": "sales_reply_citation",
                    "knowledge_item_id": item.id,
                    field: value,
                }, actor="admin@example.com")
        db.close()

    def test_list_filters_by_status_and_type(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        create_retrieval_feedback(db, ws.id, {
            "feedback_type": "helpful",
            "source": "sales_reply_citation",
            "knowledge_item_id": item.id,
        }, actor="admin@example.com")
        create_retrieval_feedback(db, ws.id, {
            "feedback_type": "outdated",
            "source": "sales_reply_citation",
            "knowledge_item_id": item.id,
        }, actor="admin@example.com")
        db.commit()

        helpful = list_retrieval_feedback(db, ws.id, {"feedback_type": "helpful"})
        open_items = list_retrieval_feedback(db, ws.id, {"status": "open"})
        db.close()

        assert len(helpful) == 1
        assert helpful[0].feedback_type == "helpful"
        assert len(open_items) == 2

    def test_update_status_sets_review_timestamps(self):
        init_db()
        db = SessionLocal()
        ws = _workspace(db)
        item = _item(db, ws.id)
        fb = create_retrieval_feedback(db, ws.id, {
            "feedback_type": "needs_review",
            "source": "sales_reply_citation",
            "knowledge_item_id": item.id,
        }, actor="admin@example.com")
        db.commit()

        reviewed = update_retrieval_feedback(db, ws.id, fb.id, {"status": "reviewed"})
        resolved = update_retrieval_feedback(db, ws.id, fb.id, {"status": "resolved"})
        db.commit()
        db.close()

        assert reviewed.reviewed_at is not None
        assert resolved.resolved_at is not None


class TestRetrievalFeedbackAPI:
    def test_create_list_and_update_feedback_api(self, client: TestClient):
        init_db()
        create_item = client.post(
            "/api/v1/admin/knowledge",
            json={
                "title": "企业知识库 PoC 验收标准",
                "summary": "知识库 PoC 验收应检查召回准确率。",
                "content_markdown": "企业知识库 PoC 验收标准包括高频问题覆盖、引用来源和人工 review。",
                "source_type": "delivery_sop",
                "tags_json": ["rag", "poc"],
                "status": "active",
            },
            headers=ADMIN,
        )
        assert create_item.status_code == 201
        item_id = create_item.json()["id"]

        create_fb = client.post(
            "/api/v1/admin/knowledge/retrieval-feedback",
            json={
                "feedback_type": "irrelevant",
                "source": "sales_reply_citation",
                "query": "企业知识库 PoC 怎么验收",
                "note": "这条不适合当前问题",
                "knowledge_item_id": item_id,
                "citation_hit_json": {"knowledge_item_id": item_id, "title": "企业知识库 PoC 验收标准"},
            },
            headers=ADMIN,
        )
        assert create_fb.status_code == 201
        fb = create_fb.json()
        assert fb["status"] == "open"
        assert fb["feedback_type"] == "irrelevant"

        listing = client.get("/api/v1/admin/knowledge/retrieval-feedback?status=open&feedback_type=irrelevant", headers=ADMIN)
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

        patch = client.patch(
            f"/api/v1/admin/knowledge/retrieval-feedback/{fb['id']}",
            json={"status": "resolved", "note": "已处理"},
            headers=ADMIN,
        )
        assert patch.status_code == 200
        assert patch.json()["status"] == "resolved"
        assert patch.json()["resolved_at"] is not None

    def test_unauthorized_feedback_api_is_rejected(self, client: TestClient):
        init_db()
        resp = client.get("/api/v1/admin/knowledge/retrieval-feedback")
        assert resp.status_code in (401, 403)
