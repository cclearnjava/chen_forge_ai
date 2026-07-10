"""Knowledge Retriever — stable retrieval contract for matching active KnowledgeItems
against a structured query, returning a Citation Pack with scores, match reasons,
excerpts, and source traces (P6.3).

Deterministic, workspace-scoped, no embeddings.  This is the freeze-layer for the
retrieval interface: when pgvector arrives later it replaces the matching internals
but keeps this contract (KnowledgeHit / CitationPack) unchanged.
"""

from sqlalchemy.orm import Session
from app.models import KnowledgeDocument, KnowledgeItem
from app.services.text_utils import as_text_list, bigrams, overlap_score

RETRIEVER_VERSION = "knowledge_retriever.hybrid_v1"
DEFAULT_MAX_HITS = 5
EXCERPT_LEN = 220

# Scoring weights
W_TITLE = 8
W_SUMMARY = 5
W_TAGS = 5
W_CONTENT_UNIT = 2
W_SERVICE_LINK = 6
W_SOURCE_TYPE_PRIORITY = {
    "contract_boundary": 3,
    "pricing_rule": 3,
    "delivery_sop": 2,
    "methodology": 2,
    "service_note": 1,
}

# ── excerpt (CJK-safe: prefer sentence boundary) ──

def _build_excerpt(content: str, max_len: int = EXCERPT_LEN) -> str:
    if not content:
        return ""
    content = content.strip()
    if len(content) <= max_len:
        return content
    # Try to stop at a period / newline / blank near the target
    cut = content.rfind("\n\n", 0, max_len)
    if cut > max_len // 2:
        return content[:cut].strip()
    for sep in ["\n", "。", ".", "；", "，", " "]:
        cut = content.rfind(sep, 0, max_len)
        if cut > max_len // 2:
            return content[:cut + len(sep)].strip()
    return content[:max_len]


# ── scoring ──

def score_knowledge_item(
    item: KnowledgeItem,
    query_text: str,
    matched_service_ids: set[str],
) -> tuple[int, list[str]]:
    """Return (score, match_reasons) for one KnowledgeItem.  score=0 → not a hit."""
    score = 0
    reasons: list[str] = []
    qt = query_text.lower()

    t_overlap = overlap_score(qt, item.title or "")
    if t_overlap > 0:
        score += W_TITLE
        reasons.append("title")

    s_overlap = overlap_score(qt, item.summary or "")
    if s_overlap > 0:
        score += W_SUMMARY
        reasons.append("summary")

    c_overlap = overlap_score(qt, item.content_markdown or "")
    if c_overlap > 0:
        score += c_overlap * W_CONTENT_UNIT
        reasons.append("content")

    tags = as_text_list(item.tags_json)
    if tags and overlap_score(qt, tags) > 0:
        score += W_TAGS
        reasons.append("tags")

    if item.service_id and item.service_id in matched_service_ids:
        score += W_SERVICE_LINK
        reasons.append("service_link")

    # Source-type priority: record both in score AND match_reasons
    st = item.source_type or ""
    st_bonus = W_SOURCE_TYPE_PRIORITY.get(st, 0)
    if st_bonus:
        score += st_bonus
        reasons.append("source_type_priority")

    return score, reasons


# ── citation source ──

def _citation_source(item: KnowledgeItem, doc_map: dict[str, KnowledgeDocument]) -> dict:
    st = item.source_type or "unknown"
    doc_id = (item.metadata_json or {}).get("document_id") if item.metadata_json else None
    chunk = (item.metadata_json or {}).get("chunk_index") if item.metadata_json else None
    result: dict = {
        "source_type": st,
        "source_name": "外部文档" if st == "external_doc" else "手工录入",
        "document_id": doc_id,
        "document_filename": None,
        "chunk_index": chunk,
    }
    if doc_id and doc_id in doc_map:
        result["document_filename"] = doc_map[doc_id].filename or None
    return result


# ── main entry ──

def retrieve_knowledge_for_sales_reply(
    db: Session,
    *,
    workspace_id: str,
    query_text: str,
    matched_service_ids: list[str] | None = None,
    max_hits: int = DEFAULT_MAX_HITS,
) -> dict[str, object]:
    """Return a stable Citation Pack dict.  All filtering happens at the query level
    (workspace_id + status=active), never in Python-side post-filter."""

    svc_ids = set(matched_service_ids or [])
    items = db.query(KnowledgeItem).filter(
        KnowledgeItem.workspace_id == workspace_id,
        KnowledgeItem.status == "active",
    ).all()

    if not items:
        return {
            "retriever_version": RETRIEVER_VERSION,
            "query_summary": query_text[:120] if query_text else None,
            "hit_count": 0,
            "no_hit_reason": "no_active_knowledge",
            "hits": [],
        }

    # ── keyword scoring ──
    kw_scored: list[tuple[KnowledgeItem, int, list[str]]] = []
    item_map = {it.id: it for it in items}
    for it in items:
        s, reasons = score_knowledge_item(it, query_text, svc_ids)
        if s > 0:
            kw_scored.append((it, s, reasons))
    kw_map: dict[str, int] = {it.id: s for it, s, _ in kw_scored}

    # ── vector scoring ──
    from app.services.knowledge_vectors import search_vectors
    vec_hits = search_vectors(db, workspace_id, query_text, max_hits=max_hits)
    vec_map: dict[str, float] = {h["knowledge_item_id"]: h["score"] * 20 for h in vec_hits}

    # ── merge ──
    VEC_WEIGHT = 20.0
    merged_ids: set[str] = set(kw_map.keys()) | set(vec_map.keys())
    merged: list[tuple[str, float, float, list[str], str]] = []  # (id, final, kw, reasons, mode)
    for iid in merged_ids:
        kw_s = kw_map.get(iid, 0)
        vec_s = vec_map.get(iid, 0.0)
        it = item_map.get(iid)
        reasons: list[str] = []
        mode = "keyword"

        if kw_s > 0:
            scored_reasons = [r for it2, _, r in kw_scored if it2.id == iid]
            reasons = scored_reasons[0] if scored_reasons else []
            mode = "keyword"

        if vec_s > 0:
            if "vector" not in reasons:
                reasons.append("vector")
            mode = "hybrid" if kw_s > 0 else "vector"

        # Apply service-link boost for merged items
        final = kw_s + vec_s
        if it and it.service_id and it.service_id in svc_ids:
            final += W_SERVICE_LINK
        st = (it.source_type or "") if it else ""
        st_bonus = W_SOURCE_TYPE_PRIORITY.get(st, 0)
        if st_bonus:
            final += st_bonus

        merged.append((iid, final, kw_s, vec_s, reasons, mode))

    merged.sort(key=lambda t: (-t[1], -(item_map[t[0]].updated_at.timestamp() if item_map.get(t[0]) and item_map[t[0]].updated_at else 0), t[0]))

    # Bulk-lookup KnowledgeDocument filenames for external_doc items
    doc_ids = [
        (it.metadata_json or {}).get("document_id")
        for iid, _, _, _, _, _ in merged
        if (it := item_map.get(iid)) and it.source_type == "external_doc" and it.metadata_json
    ]
    doc_map: dict[str, KnowledgeDocument] = {}
    if doc_ids:
        docs = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.workspace_id == workspace_id,
            KnowledgeDocument.id.in_(doc_ids),
        ).all()
        doc_map = {d.id: d for d in docs}

    hits: list[dict] = []
    for iid, final, kw_s, vec_s, reasons, mode in merged[:max_hits]:
        it = item_map.get(iid)
        if not it:
            continue
        excerpt = _build_excerpt(it.content_markdown or "")
        source = _citation_source(it, doc_map)
        hits.append({
            "knowledge_item_id": it.id,
            "title": it.title,
            "summary": it.summary,
            "source_type": it.source_type or "unknown",
            "service_id": it.service_id,
            "score": int(final),
            "keyword_score": kw_s if kw_s > 0 else None,
            "vector_score": round(vec_s, 4) if vec_s > 0 else None,
            "match_reasons": reasons,
            "retrieval_mode": mode,
            "excerpt": excerpt,
            "tags": it.tags_json or [],
            "source": source,
        })

    no_hit_reason = None if hits else "no_active_knowledge_matched"
    return {
        "retriever_version": RETRIEVER_VERSION,
        "query_summary": query_text[:120] if query_text else None,
        "hit_count": len(hits),
        "no_hit_reason": no_hit_reason,
        "hits": hits,
    }
