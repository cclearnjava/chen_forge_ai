"""Context Builder — assemble a Sales Reply Context Pack from Opportunity + Service Catalog + Knowledge Engine.

Deterministic, workspace-scoped, no embeddings. Extends the base opportunity context
(build_opportunity_agent_context) with matched services and relevant knowledge items.
"""

from sqlalchemy.orm import Session
from app.models import KnowledgeItem, ServiceRiskRule
from app.services.agent_context import build_opportunity_agent_context
from app.services.service_catalog import list_services
from app.services.knowledge_engine import retrieve_knowledge
from app.services.text_utils import as_text_list, overlap_score

CONTEXT_BUILDER_VERSION = "context_builder.sales_reply.v1"
MAX_SERVICES = 3
MAX_KNOWLEDGE = 5


def _opportunity_haystack(opp, messages) -> str:
    parts = [opp.title, opp.problem_summary, opp.desired_outcome]
    for m in messages[-5:]:
        parts.append(getattr(m, "body_markdown", None))
    return " ".join(p for p in parts if p)


def _match_services(db: Session, wid: str, text: str) -> tuple[list, int]:
    services = list_services(db, wid, status="active")
    scored = [(s, overlap_score(text, " ".join(filter(None, [
        s.name, s.positioning, s.target_customer,
        as_text_list(s.pain_points_json), as_text_list(s.outcomes_json),
    ])))) for s in services]
    genuine = sorted([p for p in scored if p[1] > 0], key=lambda p: p[1], reverse=True)
    if genuine:
        matched = [s for s, _ in genuine[:MAX_SERVICES]]
        return matched, len(matched)
    # Fail-soft fallback: show top active services as candidates, hit_count = 0
    return services[:MAX_SERVICES], 0


def _service_dict(s) -> dict:
    return {
        "id": s.id, "name": s.name, "positioning": s.positioning,
        "target_customer": s.target_customer, "typical_duration": s.typical_duration,
        "price_min": s.price_min, "price_max": s.price_max, "risk_notes": s.risk_notes,
    }


def _knowledge_dict_from_hit(hit: dict) -> dict:
    return {
        "id": hit["knowledge_item_id"],
        "title": hit["title"],
        "summary": hit.get("summary"),
        "source_type": hit.get("source_type"),
        "tags_json": hit.get("tags") or [],
        "content_excerpt": hit.get("excerpt") or "",
    }


def _collect_risk_notes(db: Session, wid: str, services: list, knowledge: list) -> list[str]:
    notes: list[str] = []
    service_ids = [s.id for s in services]
    for s in services:
        if s.risk_notes:
            notes.append(s.risk_notes)
    if service_ids:
        rules = db.query(ServiceRiskRule).filter(
            ServiceRiskRule.service_id.in_(service_ids),
            ServiceRiskRule.workspace_id == wid,
        ).all()
        for r in rules:
            label = r.title
            if r.suggested_response:
                label = f"{r.title}：{r.suggested_response}"
            notes.append(label)
    for it in knowledge:
        if it.source_type in ("pricing_rule", "contract_boundary") and it.summary:
            notes.append(it.summary)
    # de-dup, preserve order
    seen, out = set(), []
    for n in notes:
        if n and n not in seen:
            seen.add(n); out.append(n)
    return out


def build_sales_reply_context_pack(db: Session, opportunity_id: str) -> dict:
    """Build a Sales Reply Context Pack. Fail-closed if Opportunity missing (raises ValueError)."""
    ctx = build_opportunity_agent_context(db, opportunity_id)
    opp = ctx["opportunity"]
    wid = opp.workspace_id
    messages = ctx.get("messages") or []

    text = _opportunity_haystack(opp, messages)
    services, service_hits = _match_services(db, wid, text)
    service_ids = [s.id for s in services]

    # --- Knowledge: use the Retriever (P6.3 citation-aware contract) ---
    citation_pack = retrieve_knowledge(
        db, workspace_id=wid, query_text=text,
        matched_service_ids=service_ids, max_hits=MAX_KNOWLEDGE,
    )
    knowledge_hits = citation_pack["hit_count"]
    hits = citation_pack.get("hits", [])
    # Maintain backwards-compatible relevant_knowledge_items shape for mock generate_sales_reply,
    # but derive it from the Retriever result so retrieval has a single source of truth.
    compat_knowledge = [_knowledge_dict_from_hit(h) for h in hits]
    hit_ids = [h["knowledge_item_id"] for h in hits]
    hit_item_map = {}
    if hit_ids:
        hit_items = db.query(KnowledgeItem).filter(
            KnowledgeItem.workspace_id == wid,
            KnowledgeItem.status == "active",
            KnowledgeItem.id.in_(hit_ids),
        ).all()
        hit_item_map = {it.id: it for it in hit_items}
    risk_notes = _collect_risk_notes(db, wid, services, [hit_item_map[i] for i in hit_ids if i in hit_item_map])

    matched_services = [_service_dict(s) for s in services]

    summary_bits = [f"匹配服务 {service_hits} 个", f"命中知识 {knowledge_hits} 条"]
    if risk_notes:
        summary_bits.append(f"风险提示 {len(risk_notes)} 条")
    context_summary = "；".join(summary_bits)

    usage = {
        "used_service_ids": service_ids,
        "used_knowledge_item_ids": hit_ids,
        "used_reference_ids": [h["reference_id"] for h in hits],
        "used_external_reference_ids": [],
        "knowledge_provider": citation_pack["provider"],
        "knowledge_config_version": citation_pack["config_version"],
        "service_hit_count": service_hits,
        "knowledge_hit_count": knowledge_hits,
        "citation_count": knowledge_hits,
        "context_builder_version": CONTEXT_BUILDER_VERSION,
        "retriever_version": citation_pack.get("retriever_version"),
        "context_pack_summary": context_summary,
        "service_names": [s["name"] for s in matched_services],
        "knowledge_titles": [h["title"] for h in hits],
    }

    ctx.update({
        "matched_services": matched_services,
        "relevant_knowledge_items": compat_knowledge,
        "citation_pack": citation_pack,
        "risk_notes": risk_notes,
        "context_summary": context_summary,
        "usage": usage,
    })
    return ctx
