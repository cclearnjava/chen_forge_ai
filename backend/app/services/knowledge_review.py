"""Knowledge Review / Activation — draft review queue, quality flags, bulk actions,
document-level review summary (P6.4).

All operations are workspace-scoped. Quality flags are deterministic (no AI).
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import KnowledgeDocument, KnowledgeItem
from app.services.events import record_event

SHORT_CONTENT_THRESHOLD = 80
MAX_BULK_ITEM_IDS = 100

ALLOWED_BULK_ACTIONS = frozenset({"activate", "archive", "set_service", "clear_service"})


# ── quality flags ──

def build_quality_flags(db: Session, workspace_id: str, item: KnowledgeItem) -> list[str]:
    """Return deterministic quality flag labels for a single KnowledgeItem."""
    flags: list[str] = []
    content = (item.content_markdown or "").strip()
    if len(content) < SHORT_CONTENT_THRESHOLD:
        flags.append("short_content")
    if not (item.summary or "").strip():
        flags.append("missing_summary")
    if not item.service_id:
        flags.append("missing_service")
    if not item.tags_json or len(item.tags_json) == 0:
        flags.append("missing_tags")
    if item.source_type == "external_doc":
        md = item.metadata_json or {}
        if not md.get("document_id"):
            flags.append("external_doc_without_document_id")
        # Quality pipeline flags embedded in chunk metadata (P6.5)
        chunk_flags = md.get("chunk_quality_flags")
        if isinstance(chunk_flags, list):
            for f in chunk_flags:
                if f not in flags and f in (
                    "high_noise_removed", "very_short_after_cleaning",
                    "duplicate_content", "weak_title", "cleaning_removed_all_content",
                ):
                    flags.append(f)
    return flags


def _duplicate_title_map(db: Session, workspace_id: str) -> dict[str, bool]:
    """Build a map of title → is_duplicate for a given workspace.  One query only."""
    from sqlalchemy import func
    rows = (
        db.query(KnowledgeItem.title, func.count(KnowledgeItem.id))
        .filter(
            KnowledgeItem.workspace_id == workspace_id,
            KnowledgeItem.status != "archived",
        )
        .group_by(KnowledgeItem.title)
        .having(func.count(KnowledgeItem.id) > 1)
        .all()
    )
    return {title: True for title, _ in rows}


# ── review list ──

def list_review_items(
    db: Session,
    workspace_id: str,
    *,
    status: str = "draft",
    document_id: str | None = None,
    source_type: str | None = None,
    service_id: str | None = None,
    quality_flag: str | None = None,
) -> list[KnowledgeItem]:
    """Return items matching the review filters, workspace-scoped."""
    q = db.query(KnowledgeItem).filter(
        KnowledgeItem.workspace_id == workspace_id,
        KnowledgeItem.status == status,
    )
    if document_id:
        # JSON field access for metadata_json.document_id
        q = q.filter(KnowledgeItem.metadata_json["document_id"].as_string() == document_id)
    if source_type:
        q = q.filter(KnowledgeItem.source_type == source_type)
    if service_id:
        q = q.filter(KnowledgeItem.service_id == service_id)
    items = q.order_by(KnowledgeItem.updated_at.desc()).all()

    # Post-filter by quality_flag if requested — compute flags + filter in Python
    if quality_flag:
        dup_map = _duplicate_title_map(db, workspace_id) if quality_flag == "duplicate_title" else {}
        filtered = []
        for it in items:
            flags = set(build_quality_flags(db, workspace_id, it))
            if quality_flag == "duplicate_title" and dup_map.get(it.title):
                filtered.append(it)
            elif quality_flag in flags:
                filtered.append(it)
        return filtered
    return items


# ── document review ──

def get_document_review(db: Session, workspace_id: str, document_id: str) -> dict:
    """Aggregate review view for a single KnowledgeDocument and its generated items."""
    doc = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.id == document_id,
        KnowledgeDocument.workspace_id == workspace_id,
    ).first()
    if not doc:
        raise ValueError("Knowledge document not found")

    items = db.query(KnowledgeItem).filter(
        KnowledgeItem.workspace_id == workspace_id,
        KnowledgeItem.metadata_json["document_id"].as_string() == document_id,
    ).all()

    counts = {"total": len(items), "draft": 0, "active": 0, "archived": 0}
    quality_count: dict[str, int] = {}
    for it in items:
        s = it.status if hasattr(it, "status") else str(it.status)
        if s in counts:
            counts[s] += 1
        for flag in build_quality_flags(db, workspace_id, it):
            quality_count[flag] = quality_count.get(flag, 0) + 1

    return {
        "document": doc,
        "items": items,
        "counts": counts,
        "quality_summary": quality_count,
    }


# ── bulk actions ──

def bulk_update_review_items(
    db: Session,
    workspace_id: str,
    *,
    item_ids: list[str],
    action: str,
    service_id: str | None = None,
) -> list[KnowledgeItem]:
    """Apply a bulk action to the given item_ids.  All-or-nothing, workspace-scoped.

    Raises ValueError for empty ids / unsupported action / out-of-bounds items.
    The caller (API) owns the transaction — any ValueError should trigger rollback.
    """
    if not item_ids:
        raise ValueError("item_ids must not be empty")
    if len(item_ids) > MAX_BULK_ITEM_IDS:
        raise ValueError(f"item_ids exceeds maximum of {MAX_BULK_ITEM_IDS}")
    if action not in ALLOWED_BULK_ACTIONS:
        raise ValueError(f"Unsupported action: {action}")

    items = db.query(KnowledgeItem).filter(
        KnowledgeItem.id.in_(item_ids),
    ).all()

    # Fail-closed: every requested id must exist and belong to this workspace
    found_ids = {it.id: it for it in items}
    for iid in item_ids:
        it = found_ids.get(iid)
        if not it:
            raise ValueError(f"Knowledge item {iid} not found or not in this workspace")
        wid = it.workspace_id or None
        if wid != workspace_id:
            raise ValueError(f"Knowledge item {iid} does not belong to this workspace")

    from app.services.service_catalog import get_service_or_none
    if action in ("set_service", "clear_service"):
        if action == "set_service" and not service_id:
            raise ValueError("service_id is required for set_service")
        if action == "set_service" and service_id:
            svc = get_service_or_none(db, workspace_id, service_id)
            if not svc:
                raise ValueError("service_id does not belong to this workspace")

    for it in items:
        if action == "activate":
            it.status = "active"
        elif action == "archive":
            it.status = "archived"
            it.archived_at = datetime.now(timezone.utc)
        elif action == "set_service":
            it.service_id = service_id
        elif action == "clear_service":
            it.service_id = None
    db.flush()

    event_type_map = {
        "activate": "knowledge_review.bulk_activated",
        "archive": "knowledge_review.bulk_archived",
        "set_service": "knowledge_review.bulk_service_set",
        "clear_service": "knowledge_review.bulk_service_cleared",
    }
    record_event(
        db, workspace_id=workspace_id,
        type=event_type_map.get(action, "knowledge_review.unknown"),
        source="knowledge_api",
        subject_type="knowledge_item",
        title=f"Bulk {action}: {len(items)} items",
        payload_json={
            "item_ids": [it.id for it in items],
            "updated_count": len(items),
            "service_id": service_id,
            "action": action,
        },
    )

    return items
