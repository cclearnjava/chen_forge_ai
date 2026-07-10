from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
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
from app.services.knowledge_documents import (
    get_knowledge_document_or_none, list_knowledge_documents,
    process_uploaded_knowledge_document,
)
from app.services.knowledge_review import (
    build_quality_flags, bulk_update_review_items, get_document_review,
    list_review_items,
)
from app.services.knowledge_vectors import (
    get_vector_status, index_knowledge_item, reindex_active_knowledge,
)
from app.services.events import record_event
from app.schemas import (
    KnowledgeItemCreate, KnowledgeItemOut, KnowledgeItemUpdate,
    KnowledgeSourceCreate, KnowledgeSourceOut,
    KnowledgeDocumentOut, KnowledgeDocumentReviewOut,
    KnowledgeReviewBulkRequest, KnowledgeReviewBulkOut,
    KnowledgeReviewItemOut,
    KnowledgeVectorReindexRequest, KnowledgeVectorReindexOut,
    KnowledgeVectorStatusOut,
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


# ── Documents (declared before /{knowledge_id} to avoid path capture) ──

@router.post("/documents", status_code=201)
async def upload_document_api(file: UploadFile = File(...), db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    content = await file.read()
    result = process_uploaded_knowledge_document(
        db, wid, file.filename or "upload", file.content_type, content,
    )
    db.commit()
    if not result["ok"]:
        raise HTTPException(status_code=422, detail=result.get("error", "Document processing failed"))
    return {
        "document": KnowledgeDocumentOut.model_validate(result["document"]).model_dump(mode="json"),
        "items": [KnowledgeItemOut.model_validate(it).model_dump(mode="json") for it in result["items"]],
        "item_count": len(result["items"]),
    }


@router.get("/documents")
def list_documents_api(db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    docs = list_knowledge_documents(db, wid)
    return {"items": [KnowledgeDocumentOut.model_validate(d).model_dump(mode="json") for d in docs], "total": len(docs)}


@router.get("/documents/{document_id}")
def get_document_api(document_id: str, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    doc = get_knowledge_document_or_none(db, wid, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    return KnowledgeDocumentOut.model_validate(doc).model_dump(mode="json")


# ── Review Queue (P6.4, declared before /{knowledge_id}) ──

@router.get("/review")
def list_review_api(
    status: str = Query("draft"),
    document_id: str | None = Query(None),
    source_type: str | None = Query(None),
    service_id: str | None = Query(None),
    quality_flag: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    items = list_review_items(
        db, wid, status=status, document_id=document_id,
        source_type=source_type, service_id=service_id, quality_flag=quality_flag,
    )
    total = len(items)
    page = items[offset:offset + limit]
    doc_ids = list({
        (it.metadata_json or {}).get("document_id")
        for it in page
        if it.source_type == "external_doc" and it.metadata_json
    })
    doc_map = {}
    if doc_ids:
        from app.models import KnowledgeDocument as KD
        docs = db.query(KD).filter(
            KD.workspace_id == wid,
            KD.id.in_(doc_ids),
        ).all()
        doc_map = {d.id: d for d in docs}
    out_items = []
    dup_map = {}
    from app.services.knowledge_review import _duplicate_title_map, build_quality_flags
    dup_map = _duplicate_title_map(db, wid)
    for it in page:
        flags = build_quality_flags(db, wid, it)
        if dup_map.get(it.title):
            flags.append("duplicate_title")
        doc_ref = None
        did = (it.metadata_json or {}).get("document_id") if it.metadata_json else None
        if did and did in doc_map:
            doc_ref = {"id": did, "filename": doc_map[did].filename}
        out_items.append(KnowledgeReviewItemOut(
            item=KnowledgeItemOut.model_validate(it),
            quality_flags=flags,
            document=doc_ref,
        ).model_dump(mode="json"))
    return {"items": out_items, "total": total}


@router.post("/review/bulk")
def bulk_review_api(req: KnowledgeReviewBulkRequest, db: Session = Depends(get_db),
                    _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    try:
        items = bulk_update_review_items(
            db, wid, item_ids=req.item_ids, action=req.action, service_id=req.service_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
    return KnowledgeReviewBulkOut(
        updated_count=len(items),
        items=[KnowledgeItemOut.model_validate(it).model_dump(mode="json") for it in items],
    ).model_dump(mode="json")


@router.get("/documents/{document_id}/review")
def get_document_review_api(document_id: str, db: Session = Depends(get_db),
                            _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    try:
        result = get_document_review(db, wid, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    doc = result["document"]
    items = result["items"]
    flags = [build_quality_flags(db, wid, it) for it in items]
    return KnowledgeDocumentReviewOut(
        document=KnowledgeDocumentOut.model_validate(doc),
        items=[KnowledgeItemOut.model_validate(it).model_dump(mode="json") for it in items],
        counts=result["counts"],
        quality_summary=result["quality_summary"],
    ).model_dump(mode="json")


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


# ── Vector RAG (P6.5, declared before /{knowledge_id} to avoid path capture) ──

@router.post("/vectors/reindex-active")
def reindex_active_api(req: KnowledgeVectorReindexRequest = KnowledgeVectorReindexRequest(),
                       db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    result = reindex_active_knowledge(db, wid, limit=req.limit)
    db.commit()
    return KnowledgeVectorReindexOut(**result).model_dump(mode="json")


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


@router.get("/{knowledge_id}/vector")
def get_vector_status_api(knowledge_id: str, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    try:
        status = get_vector_status(db, wid, knowledge_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return status


@router.post("/{knowledge_id}/vector/reindex")
def reindex_item_api(knowledge_id: str, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    try:
        vec = index_knowledge_item(db, wid, knowledge_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    return {"knowledge_item_id": vec.knowledge_item_id, "status": vec.status,
            "embedding_model": vec.embedding_model}
