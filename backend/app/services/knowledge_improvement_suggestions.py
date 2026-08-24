"""Knowledge Improvement Suggestions service (P6.12).

Rule-based, local-only generator that turns Retrieval Feedback into actionable
Knowledge maintenance suggestions. It does not modify KnowledgeItem rows.
"""

from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    KNOWLEDGE_IMPROVEMENT_SUGGESTION_STATUSES,
    KNOWLEDGE_IMPROVEMENT_SUGGESTION_TYPES,
    KNOWLEDGE_RETRIEVAL_FEEDBACK_TYPES,
    KnowledgeImprovementSuggestion,
    KnowledgeItem,
    KnowledgeRetrievalFeedback,
)

GENERATOR = "rule_based"
GENERATOR_VERSION = "knowledge_improvement.rule_v1"
ACTIVE_DEDUPE_STATUSES = ("open", "accepted")


def _validate_enum(name: str, value: str, allowed: tuple[str, ...]) -> str:
    if value not in allowed:
        raise ValueError(f"Invalid {name}: {value}")
    return value


def _knowledge_title(db: Session, workspace_id: str, item_id: str | None) -> str:
    if not item_id:
        return "未关联知识"
    item = db.query(KnowledgeItem).filter(
        KnowledgeItem.id == item_id,
        KnowledgeItem.workspace_id == workspace_id,
    ).first()
    return item.title if item else item_id


def _short(value: str | None, limit: int = 160) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value[:limit]


def _evidence(feedbacks: list[KnowledgeRetrievalFeedback]) -> dict:
    type_counts = Counter(f.feedback_type for f in feedbacks)
    queries = []
    notes = []
    for fb in feedbacks:
        if fb.query and fb.query not in queries:
            queries.append(fb.query)
        note = _short(fb.note)
        if note and note not in notes:
            notes.append(note)
    return {
        "feedback_ids": [f.id for f in feedbacks],
        "feedback_count": len(feedbacks),
        "feedback_types": dict(type_counts),
        "sample_queries": queries[:5],
        "sample_notes": notes[:5],
    }


def _dedupe_target(suggestion_type: str, knowledge_item_id: str | None, query: str | None) -> str:
    if knowledge_item_id:
        return knowledge_item_id
    normalized = " ".join((query or "").lower().split())
    return normalized[:160] or suggestion_type


def _find_active_duplicate(
    db: Session,
    workspace_id: str,
    suggestion_type: str,
    target_key: str,
) -> KnowledgeImprovementSuggestion | None:
    return db.query(KnowledgeImprovementSuggestion).filter(
        KnowledgeImprovementSuggestion.workspace_id == workspace_id,
        KnowledgeImprovementSuggestion.suggestion_type == suggestion_type,
        KnowledgeImprovementSuggestion.status.in_(ACTIVE_DEDUPE_STATUSES),
        KnowledgeImprovementSuggestion.metadata_json["dedupe_key"].as_string() == target_key,
    ).first()


def _upsert_suggestion(
    db: Session,
    workspace_id: str,
    *,
    suggestion_type: str,
    title: str,
    reason: str,
    recommended_action: str,
    feedbacks: list[KnowledgeRetrievalFeedback],
    knowledge_item_id: str | None = None,
    expected_knowledge_item_id: str | None = None,
    confidence: float = 0.6,
) -> tuple[KnowledgeImprovementSuggestion, bool]:
    evidence = _evidence(feedbacks)
    target_key = _dedupe_target(suggestion_type, knowledge_item_id, feedbacks[0].query if feedbacks else None)
    existing = _find_active_duplicate(db, workspace_id, suggestion_type, target_key)
    if existing:
        existing.source_feedback_ids = evidence["feedback_ids"]
        existing.evidence_json = evidence
        existing.reason = reason
        existing.recommended_action = recommended_action
        existing.confidence = confidence
        metadata = dict(existing.metadata_json or {})
        metadata["dedupe_key"] = target_key
        existing.metadata_json = metadata
        db.flush()
        return existing, False

    suggestion = KnowledgeImprovementSuggestion(
        workspace_id=workspace_id,
        suggestion_type=suggestion_type,
        status="open",
        title=title,
        reason=reason,
        recommended_action=recommended_action,
        knowledge_item_id=knowledge_item_id,
        expected_knowledge_item_id=expected_knowledge_item_id,
        source_feedback_ids=evidence["feedback_ids"],
        evidence_json=evidence,
        metadata_json={"dedupe_key": target_key},
        generator=GENERATOR,
        generator_version=GENERATOR_VERSION,
        confidence=confidence,
    )
    db.add(suggestion)
    db.flush()
    return suggestion, True


def _load_feedbacks(db: Session, workspace_id: str, filters: dict | None) -> list[KnowledgeRetrievalFeedback]:
    filters = filters or {}
    q = db.query(KnowledgeRetrievalFeedback).filter(
        KnowledgeRetrievalFeedback.workspace_id == workspace_id,
        KnowledgeRetrievalFeedback.status.in_(("open", "reviewed")),
    )
    if filters.get("feedback_type"):
        feedback_type = _validate_enum("feedback_type", filters["feedback_type"], KNOWLEDGE_RETRIEVAL_FEEDBACK_TYPES)
        q = q.filter(KnowledgeRetrievalFeedback.feedback_type == feedback_type)
    if filters.get("knowledge_item_id"):
        q = q.filter(KnowledgeRetrievalFeedback.knowledge_item_id == filters["knowledge_item_id"])
    limit = filters.get("limit") or 200
    return q.order_by(KnowledgeRetrievalFeedback.created_at.desc()).limit(limit).all()


def generate_improvement_suggestions(db: Session, workspace_id: str, filters: dict | None = None) -> dict:
    feedbacks = _load_feedbacks(db, workspace_id, filters)
    groups: dict[tuple[str, str], list[KnowledgeRetrievalFeedback]] = defaultdict(list)
    for fb in feedbacks:
        if fb.feedback_type == "missing":
            target = fb.expected_knowledge_item_id or _dedupe_target("create_knowledge", None, fb.query)
        else:
            target = fb.knowledge_item_id or ""
        groups[(fb.feedback_type, target)].append(fb)

    suggestions: list[KnowledgeImprovementSuggestion] = []
    created_count = 0
    updated_count = 0

    for (feedback_type, target), rows in groups.items():
        if not rows:
            continue

        suggestion = None
        created = False
        if feedback_type == "irrelevant" and target:
            title = _knowledge_title(db, workspace_id, target)
            suggestion, created = _upsert_suggestion(
                db, workspace_id,
                suggestion_type="improve_metadata",
                title=f"建议优化「{title}」的标题、摘要或标签",
                reason=f"该知识条目在 {len(rows)} 条反馈中被标记为不相关，可能存在关键词过宽或摘要误导。",
                recommended_action="检查标题、summary、tags_json 和 source_type，减少泛化关键词。",
                feedbacks=rows,
                knowledge_item_id=target,
                confidence=min(0.9, 0.5 + len(rows) * 0.1),
            )
        elif feedback_type == "outdated" and target:
            title = _knowledge_title(db, workspace_id, target)
            suggestion, created = _upsert_suggestion(
                db, workspace_id,
                suggestion_type="update_content",
                title=f"建议更新「{title}」正文",
                reason=f"该知识条目在 {len(rows)} 条反馈中被标记为过时。",
                recommended_action="人工核对最新交付周期、报价、合同边界或流程信息后更新正文。",
                feedbacks=rows,
                knowledge_item_id=target,
                confidence=min(0.9, 0.6 + len(rows) * 0.1),
            )
        elif feedback_type == "missing":
            expected_id = rows[0].expected_knowledge_item_id
            if expected_id:
                title = _knowledge_title(db, workspace_id, expected_id)
                suggestion, created = _upsert_suggestion(
                    db, workspace_id,
                    suggestion_type="improve_retrievability",
                    title=f"建议增强「{title}」的可检索性",
                    reason=f"该知识条目在 {len(rows)} 条反馈中被认为应该命中但未命中。",
                    recommended_action="将真实 query 中的关键表达补充到标题、摘要或标签中。",
                    feedbacks=rows,
                    knowledge_item_id=expected_id,
                    expected_knowledge_item_id=expected_id,
                    confidence=min(0.9, 0.6 + len(rows) * 0.1),
                )
            else:
                query = rows[0].query or "未命名问题"
                suggestion, created = _upsert_suggestion(
                    db, workspace_id,
                    suggestion_type="create_knowledge",
                    title=f"建议新增知识：{query[:80]}",
                    reason=f"有 {len(rows)} 条反馈显示该问题没有合适知识命中。",
                    recommended_action="新建 FAQ / service_note / delivery_sop 类型 KnowledgeItem 覆盖该问题。",
                    feedbacks=rows,
                    confidence=min(0.85, 0.5 + len(rows) * 0.1),
                )
        elif feedback_type == "helpful" and target and len(rows) >= 2:
            title = _knowledge_title(db, workspace_id, target)
            suggestion, created = _upsert_suggestion(
                db, workspace_id,
                suggestion_type="promote_eval_case",
                title=f"建议将「{title}」沉淀为检索评估用例",
                reason=f"该知识条目在 {len(rows)} 条真实反馈中被标记有用。",
                recommended_action="将这些真实 query 和 expected KnowledgeItem 沉淀为 RetrievalEvalCase。",
                feedbacks=rows,
                knowledge_item_id=target,
                confidence=min(0.9, 0.5 + len(rows) * 0.1),
            )

        if suggestion:
            suggestions.append(suggestion)
            if created:
                created_count += 1
            else:
                updated_count += 1

    db.flush()
    return {"created_count": created_count, "updated_count": updated_count, "suggestions": suggestions}


def list_improvement_suggestions(db: Session, workspace_id: str, filters: dict | None = None) -> list[KnowledgeImprovementSuggestion]:
    filters = filters or {}
    q = db.query(KnowledgeImprovementSuggestion).filter(
        KnowledgeImprovementSuggestion.workspace_id == workspace_id,
    )
    if filters.get("status"):
        status = _validate_enum("status", filters["status"], KNOWLEDGE_IMPROVEMENT_SUGGESTION_STATUSES)
        q = q.filter(KnowledgeImprovementSuggestion.status == status)
    if filters.get("suggestion_type"):
        suggestion_type = _validate_enum("suggestion_type", filters["suggestion_type"], KNOWLEDGE_IMPROVEMENT_SUGGESTION_TYPES)
        q = q.filter(KnowledgeImprovementSuggestion.suggestion_type == suggestion_type)
    if filters.get("knowledge_item_id"):
        q = q.filter(KnowledgeImprovementSuggestion.knowledge_item_id == filters["knowledge_item_id"])
    return q.order_by(KnowledgeImprovementSuggestion.created_at.desc()).all()


def update_improvement_suggestion(
    db: Session,
    workspace_id: str,
    suggestion_id: str,
    data: dict,
) -> KnowledgeImprovementSuggestion:
    suggestion = db.query(KnowledgeImprovementSuggestion).filter(
        KnowledgeImprovementSuggestion.id == suggestion_id,
        KnowledgeImprovementSuggestion.workspace_id == workspace_id,
    ).first()
    if not suggestion:
        raise ValueError("Knowledge improvement suggestion not found")

    if "status" in data and data["status"] is not None:
        status = _validate_enum("status", data["status"], KNOWLEDGE_IMPROVEMENT_SUGGESTION_STATUSES)
        suggestion.status = status
        now = datetime.utcnow()
        if status == "accepted" and not suggestion.accepted_at:
            suggestion.accepted_at = now
        if status == "dismissed" and not suggestion.dismissed_at:
            suggestion.dismissed_at = now
        if status == "applied" and not suggestion.applied_at:
            suggestion.applied_at = now
        if status == "archived" and not suggestion.archived_at:
            suggestion.archived_at = now
    db.flush()
    return suggestion
