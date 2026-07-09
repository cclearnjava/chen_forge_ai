from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.services.workspace_guard import get_current_workspace_id
from app.services.service_catalog import get_service_or_none
from app.services.knowledge import (
    archive_knowledge_item, create_knowledge_item, create_knowledge_source,
    ensure_default_knowledge_sources, get_knowledge_item_or_none,
    list_knowledge_items, list_knowledge_sources, update_knowledge_item,
)
from app.services.events import record_event
from app.schemas import (
    KnowledgeItemCreate, KnowledgeItemOut, KnowledgeItemUpdate,
    KnowledgeSourceCreate, KnowledgeSourceOut,
)
from app.models import KnowledgeItem, KnowledgeSource

router = APIRouter(prefix="/admin/knowledge", tags=["knowledge"])


def _validate_links(db: Session, wid: str, data: dict) -> None:
    """service_id / source_id, if provided, must belong to the current workspace."""
    sid = data.get("service_id")
    if sid and not get_service_or_none(db, wid, sid):
        raise HTTPException(status_code=422, detail="service_id does not belong to this workspace")
    src_id = data.get("source_id")
    if src_id:
        src = db.query(KnowledgeSource).filter(
            KnowledgeSource.id == src_id, KnowledgeSource.workspace_id == wid,
        ).first()
        if not src:
            raise HTTPException(status_code=422, detail="source_id does not belong to this workspace")


# ── Sources (declared before /{knowledge_id} to avoid path capture) ──

@router.get("/sources")
def list_sources_api(db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    sources = ensure_default_knowledge_sources(db, wid)
    db.commit()
    return {"items": [KnowledgeSourceOut.model_validate(s).model_dump(mode="json") for s in sources]}


@router.post("/sources", status_code=201)
def create_source_api(req: KnowledgeSourceCreate, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    src = create_knowledge_source(db, wid, req.model_dump())
    record_event(db, workspace_id=wid, type="knowledge_source.created", source="knowledge_api",
                 subject_type="knowledge_source", subject_id=src.id, title=f"知识来源已创建: {src.name}")
    db.commit()
    return KnowledgeSourceOut.model_validate(src).model_dump(mode="json")


# ── Knowledge items ──

@router.get("")
def list_items_api(
    q: str | None = Query(None), status: str | None = Query(None),
    source_type: str | None = Query(None), tag: str | None = Query(None),
    service_id: str | None = Query(None),
    offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    items = list_knowledge_items(
        db, wid, q=q, status=status, source_type=source_type, tag=tag, service_id=service_id,
    )
    total = len(items)
    page = items[offset:offset + limit]
    return {"items": [KnowledgeItemOut.model_validate(it).model_dump(mode="json") for it in page], "total": total}


@router.post("", status_code=201)
def create_item_api(req: KnowledgeItemCreate, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    data = req.model_dump()
    _validate_links(db, wid, data)
    item = create_knowledge_item(db, wid, data)
    record_event(db, workspace_id=wid, type="knowledge_item.created", source="knowledge_api",
                 subject_type="knowledge_item", subject_id=item.id, title=f"知识已创建: {item.title}")
    db.commit()
    return KnowledgeItemOut.model_validate(item).model_dump(mode="json")


@router.get("/{knowledge_id}")
def get_item_api(knowledge_id: str, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    item = get_knowledge_item_or_none(db, wid, knowledge_id)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return KnowledgeItemOut.model_validate(item).model_dump(mode="json")


@router.patch("/{knowledge_id}")
def update_item_api(knowledge_id: str, req: KnowledgeItemUpdate, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    data = req.model_dump(exclude_unset=True)
    _validate_links(db, wid, data)
    item = update_knowledge_item(db, wid, knowledge_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    record_event(db, workspace_id=wid, type="knowledge_item.updated", source="knowledge_api",
                 subject_type="knowledge_item", subject_id=item.id, title=f"知识已更新: {item.title}")
    db.commit()
    return KnowledgeItemOut.model_validate(item).model_dump(mode="json")


@router.post("/{knowledge_id}/archive")
def archive_item_api(knowledge_id: str, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    item = archive_knowledge_item(db, wid, knowledge_id)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    record_event(db, workspace_id=wid, type="knowledge_item.archived", source="knowledge_api",
                 subject_type="knowledge_item", subject_id=item.id, title=f"知识已归档: {item.title}")
    db.commit()
    return KnowledgeItemOut.model_validate(item).model_dump(mode="json")
