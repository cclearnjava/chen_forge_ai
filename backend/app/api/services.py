from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.services.workspace_guard import get_current_workspace_id
from app.services.service_catalog import (
    create_service, ensure_default_services, get_service_or_none,
    list_services, set_service_status, update_service,
)
from app.services.events import record_event
from app.models import ServiceStatus

router = APIRouter(prefix="/admin/services", tags=["services"])


def _svc_to_dict(s) -> dict:
    return {
        "id": s.id, "workspace_id": s.workspace_id, "name": s.name, "slug": s.slug,
        "status": s.status.value if hasattr(s.status, "value") else s.status,
        "positioning": s.positioning, "target_customer": s.target_customer,
        "pain_points_json": s.pain_points_json, "outcomes_json": s.outcomes_json,
        "required_inputs_json": s.required_inputs_json,
        "success_criteria_json": s.success_criteria_json,
        "typical_duration": s.typical_duration,
        "price_min": s.price_min, "price_max": s.price_max, "currency": s.currency,
        "sort_order": s.sort_order, "is_featured": s.is_featured,
        "risk_notes": s.risk_notes,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.get("")
def list_services_api(
    status: str | None = Query(None), q: str | None = Query(None),
    offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), _admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    items = list_services(db, wid, status, q)
    total = len(items)
    page = items[offset:offset + limit]
    return {"items": [_svc_to_dict(s) for s in page], "total": total}


@router.post("", status_code=201)
def create_service_api(
    req: dict, db: Session = Depends(get_db), admin: str = Depends(get_admin_email),
):
    wid = get_current_workspace_id(db)
    # FastAPI will parse the body; use a simple approach for MVP
    from app.schemas import ServiceCreate
    data = ServiceCreate(**req)
    existing = db.query(Service).filter(Service.slug == data.slug, Service.workspace_id == wid).first()
    if existing:
        raise HTTPException(status_code=409, detail="Service slug already exists in this workspace")
    svc = create_service(db, wid, data.model_dump(exclude_unset=True))
    record_event(db, workspace_id=wid, type="service.created", source="service_api",
                  subject_type="service", subject_id=svc.id, title=f"Service created: {svc.name}")
    db.commit()
    return _svc_to_dict(svc)


@router.get("/{service_id}")
def get_service(service_id: str, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    svc = get_service_or_none(db, wid, service_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    return _svc_to_dict(svc)


@router.patch("/{service_id}")
def update_service_api(service_id: str, req: dict, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    from app.schemas import ServiceUpdate
    data = ServiceUpdate(**req)
    svc = update_service(db, wid, service_id, data.model_dump(exclude_unset=True))
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    record_event(db, workspace_id=wid, type="service.updated", source="service_api",
                  subject_type="service", subject_id=svc.id, title=f"Service updated: {svc.name}")
    db.commit()
    return _svc_to_dict(svc)


@router.post("/{service_id}/activate")
def activate(service_id: str, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    svc = set_service_status(db, wid, service_id, ServiceStatus.active)
    if not svc: raise HTTPException(status_code=404, detail="Service not found")
    record_event(db, workspace_id=wid, type="service.activated", source="service_api",
                  subject_type="service", subject_id=svc.id, title=f"Service activated: {svc.name}")
    db.commit()
    return _svc_to_dict(svc)


@router.post("/{service_id}/deactivate")
def deactivate(service_id: str, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    svc = set_service_status(db, wid, service_id, ServiceStatus.inactive)
    if not svc: raise HTTPException(status_code=404, detail="Service not found")
    record_event(db, workspace_id=wid, type="service.deactivated", source="service_api",
                  subject_type="service", subject_id=svc.id, title=f"Service deactivated: {svc.name}")
    db.commit()
    return _svc_to_dict(svc)


@router.post("/{service_id}/archive")
def archive(service_id: str, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    svc = set_service_status(db, wid, service_id, ServiceStatus.archived)
    if not svc: raise HTTPException(status_code=404, detail="Service not found")
    record_event(db, workspace_id=wid, type="service.archived", source="service_api",
                  subject_type="service", subject_id=svc.id, title=f"Service archived: {svc.name}")
    db.commit()
    return _svc_to_dict(svc)


@router.post("/seed-defaults")
def seed_defaults(db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    services = ensure_default_services(db, wid)
    record_event(db, workspace_id=wid, type="service.seeded", source="service_api",
                  subject_type="service", title="Default services seeded")
    db.commit()
    return {"services": [_svc_to_dict(s) for s in services], "count": len(services)}


# Import at bottom to avoid circular
from app.models import Service
