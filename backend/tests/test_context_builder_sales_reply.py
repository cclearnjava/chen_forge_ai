"""Context Builder + Sales Reply integration tests (P4).

Covers Context Pack assembly, active-only knowledge, service-linked priority,
fail-soft / fail-closed, cross-workspace isolation, and Artifact context_usage.
"""

import uuid
from app.db import SessionLocal, init_db
from app.models import (
    Contact, Conversation, Customer, KnowledgeItem, Lead, Message,
    MessageSenderType, Opportunity, OpportunityStage, Service, ServiceStatus, Workspace,
)
from app.services.context_builder import build_sales_reply_context_pack
from app.services.sales_reply_workflow import run_sales_reply_workflow


def _workspace(db) -> Workspace:
    ws = Workspace(slug=f"cb-{uuid.uuid4().hex[:8]}", name="CB WS", is_default=False)
    db.add(ws); db.flush()
    return ws


def _service(db, wid, name, positioning="", status=ServiceStatus.active) -> Service:
    s = Service(workspace_id=wid, name=name, slug=f"svc-{uuid.uuid4().hex[:8]}",
                status=status, positioning=positioning, risk_notes="不承诺生产环境自动操作")
    db.add(s); db.flush()
    return s


def _knowledge(db, wid, title, summary="", content="正文内容", status="active",
               source_type="methodology", service_id=None, tags=None) -> KnowledgeItem:
    it = KnowledgeItem(workspace_id=wid, title=title, summary=summary,
                       content_markdown=content, status=status, source_type=source_type,
                       service_id=service_id, tags_json=tags or [])
    db.add(it); db.flush()
    return it


def _opportunity(db, wid, *, title="自动化报表 PoC",
                 problem="现有报表生成太慢，财务月底结账耗时两天",
                 outcome="自动化财务报表生成") -> Opportunity:
    lead = Lead(workspace_id=wid, owner_email=f"{uuid.uuid4().hex[:6]}@ex.com",
                company="报表科技", contact_name="王总", contact_method="email",
                problem=problem, desired_outcome=outcome)
    db.add(lead); db.flush()
    cust = Customer(workspace_id=wid, name=lead.company, owner_email=lead.owner_email, source_lead_id=lead.id)
    db.add(cust); db.flush()
    conv = Conversation(workspace_id=wid, customer_id=cust.id, lead_id=lead.id, title="对话", channel="web_form")
    db.add(conv); db.flush()
    db.add(Message(workspace_id=wid, conversation_id=conv.id, customer_id=cust.id,
                   sender_type=MessageSenderType.customer, sender_label="王总",
                   body_markdown=problem, source="lead_form"))
    contact = Contact(workspace_id=wid, customer_id=cust.id, name="王总", email=lead.owner_email,
                      contact_method="email", is_primary=True, source_lead_id=lead.id)
    db.add(contact); db.flush()
    opp = Opportunity(workspace_id=wid, customer_id=cust.id, lead_id=lead.id,
                      primary_contact_id=contact.id, conversation_id=conv.id,
                      title=title, stage=OpportunityStage.qualified,
                      desired_outcome=outcome, problem_summary=problem)
    db.add(opp); db.flush()
    return opp


class TestContextBuilder:
    def test_matches_active_service(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _service(db, ws.id, "自动化报表系统", "帮助企业自动化生成财务报表")
        opp = _opportunity(db, ws.id); db.commit()
        pack = build_sales_reply_context_pack(db, opp.id)
        assert len(pack["matched_services"]) >= 1
        assert pack["usage"]["service_hit_count"] >= 1
        # Citation pack is present
        assert "citation_pack" in pack
        assert pack["citation_pack"]["retriever_version"] == "knowledge_retriever.keyword_v1"

    def test_matches_active_knowledge(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _knowledge(db, ws.id, "财务报表自动化验收标准", "报表自动化项目的验收要点")
        opp = _opportunity(db, ws.id); db.commit()
        pack = build_sales_reply_context_pack(db, opp.id)
        assert len(pack["relevant_knowledge_items"]) >= 1
        assert pack["usage"]["knowledge_hit_count"] >= 1

    def test_archived_knowledge_excluded(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _knowledge(db, ws.id, "财务报表自动化验收标准", "报表自动化验收", status="archived")
        opp = _opportunity(db, ws.id); db.commit()
        pack = build_sales_reply_context_pack(db, opp.id)
        titles = [k["title"] for k in pack["relevant_knowledge_items"]]
        assert "财务报表自动化验收标准" not in titles

    def test_draft_knowledge_excluded(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _knowledge(db, ws.id, "财务报表自动化验收标准", "报表自动化验收", status="draft")
        opp = _opportunity(db, ws.id); db.commit()
        pack = build_sales_reply_context_pack(db, opp.id)
        titles = [k["title"] for k in pack["relevant_knowledge_items"]]
        assert "财务报表自动化验收标准" not in titles

    def test_service_linked_knowledge_prioritized(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        svc = _service(db, ws.id, "自动化报表系统", "帮助企业自动化生成财务报表")
        # low text overlap but linked to the matched service → boosted in
        linked = _knowledge(db, ws.id, "完全无关的标题ABCDEF", "无关摘要",
                            content="无关内容", service_id=svc.id)
        opp = _opportunity(db, ws.id); db.commit()
        pack = build_sales_reply_context_pack(db, opp.id)
        assert linked.id in pack["usage"]["used_knowledge_item_ids"]

    def test_fail_soft_no_knowledge(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _service(db, ws.id, "自动化报表系统", "自动化报表")
        opp = _opportunity(db, ws.id); db.commit()
        pack = build_sales_reply_context_pack(db, opp.id)
        assert pack["relevant_knowledge_items"] == []
        assert pack["usage"]["knowledge_hit_count"] == 0

    def test_fail_closed_no_opportunity(self):
        init_db(); db = SessionLocal()
        try:
            build_sales_reply_context_pack(db, "does-not-exist")
            assert False, "should raise"
        except ValueError:
            pass

    def test_cross_workspace_service_excluded(self):
        init_db(); db = SessionLocal()
        ws1 = _workspace(db); ws2 = _workspace(db)
        _service(db, ws2.id, "自动化报表系统", "帮助企业自动化生成财务报表")
        opp = _opportunity(db, ws1.id); db.commit()
        pack = build_sales_reply_context_pack(db, opp.id)
        names = [s["name"] for s in pack["matched_services"]]
        assert "自动化报表系统" not in names

    def test_cross_workspace_knowledge_excluded(self):
        init_db(); db = SessionLocal()
        ws1 = _workspace(db); ws2 = _workspace(db)
        _knowledge(db, ws2.id, "财务报表自动化验收标准", "报表自动化验收")
        opp = _opportunity(db, ws1.id); db.commit()
        pack = build_sales_reply_context_pack(db, opp.id)
        titles = [k["title"] for k in pack["relevant_knowledge_items"]]
        assert "财务报表自动化验收标准" not in titles


class TestSalesReplyContextIntegration:
    def test_artifact_records_context_usage(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _service(db, ws.id, "自动化报表系统", "帮助企业自动化生成财务报表")
        _knowledge(db, ws.id, "财务报表自动化验收标准", "报表自动化项目的验收要点")
        opp = _opportunity(db, ws.id); db.commit()
        result = run_sales_reply_workflow(db, opp.id); db.commit()
        draft = result["artifacts"][0]
        usage = draft.content_json["context_usage"]
        assert "used_service_ids" in usage
        assert "used_knowledge_item_ids" in usage
        assert usage["context_builder_version"] == "context_builder.sales_reply.v1"
        assert usage["retriever_version"] == "knowledge_retriever.keyword_v1"
        # Citation pack is stored alongside context_usage
        citations = draft.content_json.get("citations")
        assert citations is not None and "hits" in citations
        assert citations["retriever_version"] == "knowledge_retriever.keyword_v1"

    def test_reply_reflects_context(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        _service(db, ws.id, "自动化报表系统", "帮助企业自动化生成财务报表")
        _knowledge(db, ws.id, "财务报表自动化验收标准", "务必先确认数据口径再做验收")
        opp = _opportunity(db, ws.id); db.commit()
        result = run_sales_reply_workflow(db, opp.id); db.commit()
        text = result["artifacts"][0].content_markdown
        assert "自动化报表系统" in text or "务必先确认数据口径再做验收" in text

    def test_fail_soft_still_produces_draft(self):
        init_db(); db = SessionLocal()
        ws = _workspace(db)
        opp = _opportunity(db, ws.id); db.commit()  # no service, no knowledge
        result = run_sales_reply_workflow(db, opp.id); db.commit()
        draft = result["artifacts"][0]
        assert draft.content_markdown
        assert "报表科技" in draft.content_markdown  # base reply still present
        # Citation pack present but empty (fail-soft)
        citations = draft.content_json.get("citations")
        assert citations is not None and citations["hit_count"] == 0
