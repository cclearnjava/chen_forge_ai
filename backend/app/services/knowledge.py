"""Workspace Knowledge Engine — workspace-scoped knowledge management (P3)."""

from datetime import datetime, timezone
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models import KnowledgeItem, KnowledgeSource


def list_knowledge_items(
    db: Session, workspace_id: str, *,
    status: str | None = None, source_type: str | None = None,
    tag: str | None = None, service_id: str | None = None, q: str | None = None,
) -> list[KnowledgeItem]:
    query = db.query(KnowledgeItem).filter(KnowledgeItem.workspace_id == workspace_id)
    # Default: only active (archived + draft hidden unless explicitly requested)
    query = query.filter(KnowledgeItem.status == (status or "active"))
    if source_type:
        query = query.filter(KnowledgeItem.source_type == source_type)
    if service_id:
        query = query.filter(KnowledgeItem.service_id == service_id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            KnowledgeItem.title.ilike(like),
            KnowledgeItem.summary.ilike(like),
            KnowledgeItem.content_markdown.ilike(like),
        ))
    items = query.order_by(KnowledgeItem.updated_at.desc()).all()
    if tag:
        items = [it for it in items if it.tags_json and tag in it.tags_json]
    return items


def search_knowledge_items(db: Session, workspace_id: str, q: str, **filters) -> list[KnowledgeItem]:
    return list_knowledge_items(db, workspace_id, q=q, **filters)


def get_knowledge_item_or_none(db: Session, workspace_id: str, item_id: str) -> KnowledgeItem | None:
    return db.query(KnowledgeItem).filter(
        KnowledgeItem.id == item_id, KnowledgeItem.workspace_id == workspace_id,
    ).first()


def create_knowledge_item(db: Session, workspace_id: str, data: dict) -> KnowledgeItem:
    data = dict(data)
    data.setdefault("tags_json", [])
    item = KnowledgeItem(workspace_id=workspace_id, **data)
    db.add(item)
    db.flush()
    return item


def update_knowledge_item(db: Session, workspace_id: str, item_id: str, data: dict) -> KnowledgeItem | None:
    item = get_knowledge_item_or_none(db, workspace_id, item_id)
    if not item:
        return None
    for k, v in data.items():
        if hasattr(item, k):
            setattr(item, k, v)
    if data.get("status") == "archived" and item.archived_at is None:
        item.archived_at = datetime.now(timezone.utc)
    db.flush()
    return item


def archive_knowledge_item(db: Session, workspace_id: str, item_id: str) -> KnowledgeItem | None:
    item = get_knowledge_item_or_none(db, workspace_id, item_id)
    if not item:
        return None
    item.status = "archived"
    item.archived_at = datetime.now(timezone.utc)
    db.flush()
    return item


def list_knowledge_sources(db: Session, workspace_id: str) -> list[KnowledgeSource]:
    return db.query(KnowledgeSource).filter(
        KnowledgeSource.workspace_id == workspace_id,
    ).order_by(KnowledgeSource.name).all()


def create_knowledge_source(db: Session, workspace_id: str, data: dict) -> KnowledgeSource:
    src = KnowledgeSource(workspace_id=workspace_id, **data)
    db.add(src)
    db.flush()
    return src


DEFAULT_KNOWLEDGE_SOURCES = [
    {"name": "手工录入", "description": "运营人员直接录入的知识条目"},
    {"name": "客户案例", "description": "已交付项目沉淀的案例与总结"},
    {"name": "FAQ", "description": "售前售后常见问题与标准回答"},
    {"name": "报价规则", "description": "定价、折扣与承接边界规则"},
    {"name": "交付 SOP", "description": "标准交付流程与验收标准"},
]


def ensure_default_knowledge_sources(db: Session, workspace_id: str) -> list[KnowledgeSource]:
    """Idempotent per-name: seed any missing default source for the workspace.

    Robust even if other sources (e.g. the '外部文档' source created by document
    upload) already exist — each default is seeded only if its name is absent.
    """
    existing_names = {
        s.name for s in db.query(KnowledgeSource).filter(
            KnowledgeSource.workspace_id == workspace_id,
        ).all()
    }
    for d in DEFAULT_KNOWLEDGE_SOURCES:
        if d["name"] not in existing_names:
            db.add(KnowledgeSource(workspace_id=workspace_id, **d))
    db.flush()
    return list_knowledge_sources(db, workspace_id)
