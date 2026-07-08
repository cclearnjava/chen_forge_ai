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
from app.models import ServiceDeliverable, ServicePackage, ServiceRiskRule, ServiceStatus

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



def _pkg_to_dict(p) -> dict:
    return {"id": p.id, "service_id": p.service_id, "workspace_id": p.workspace_id, "name": p.name, "description": p.description, "price_min": p.price_min, "price_max": p.price_max, "currency": p.currency, "duration": p.duration, "sort_order": p.sort_order, "is_active": p.is_active, "created_at": p.created_at.isoformat() if p.created_at else None, "updated_at": p.updated_at.isoformat() if p.updated_at else None}

def _del_to_dict(d) -> dict:
    return {"id": d.id, "service_id": d.service_id, "workspace_id": d.workspace_id, "package_id": d.package_id, "title": d.title, "description": d.description, "format": d.format, "sort_order": d.sort_order, "created_at": d.created_at.isoformat() if d.created_at else None, "updated_at": d.updated_at.isoformat() if d.updated_at else None}

def _rule_to_dict(r) -> dict:
    return {"id": r.id, "service_id": r.service_id, "workspace_id": r.workspace_id, "title": r.title, "description": r.description, "severity": r.severity.value if hasattr(r.severity, "value") else r.severity, "disqualifies": r.disqualifies, "suggested_response": r.suggested_response, "sort_order": r.sort_order, "created_at": r.created_at.isoformat() if r.created_at else None, "updated_at": r.updated_at.isoformat() if r.updated_at else None}


# ── Sub-resources: packages, deliverables, risk_rules ──

@router.get("/{service_id}/packages")
def list_packages(service_id: str, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    items = db.query(ServicePackage).filter(ServicePackage.service_id == service_id, ServicePackage.workspace_id == wid).order_by(ServicePackage.sort_order).all()
    return {"items": [_pkg_to_dict(p) for p in items]}

@router.get("/{service_id}/deliverables")
def list_deliverables(service_id: str, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    items = db.query(ServiceDeliverable).filter(ServiceDeliverable.service_id == service_id, ServiceDeliverable.workspace_id == wid).order_by(ServiceDeliverable.sort_order).all()
    return {"items": [_del_to_dict(d) for d in items]}

@router.get("/{service_id}/risk-rules")
def list_risk_rules(service_id: str, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    items = db.query(ServiceRiskRule).filter(ServiceRiskRule.service_id == service_id, ServiceRiskRule.workspace_id == wid).order_by(ServiceRiskRule.sort_order).all()
    return {"items": [_rule_to_dict(r) for r in items]}


# ── Sub-resource mutations ──

@router.post("/{service_id}/packages", status_code=201)
def create_package(service_id: str, req: dict, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    if not get_service_or_none(db, wid, service_id): raise HTTPException(status_code=404, detail="Service not found")
    if not req.get("name"): raise HTTPException(status_code=422, detail="Package name is required")
    pkg = ServicePackage(workspace_id=wid, service_id=service_id, name=req["name"], description=req.get("description"), price_min=req.get("price_min"), price_max=req.get("price_max"), currency=req.get("currency", "CNY"), duration=req.get("duration"), sort_order=req.get("sort_order", 0))
    db.add(pkg); db.commit()
    return _pkg_to_dict(pkg)

@router.post("/{service_id}/deliverables", status_code=201)
def create_deliverable(service_id: str, req: dict, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    if not get_service_or_none(db, wid, service_id): raise HTTPException(status_code=404, detail="Service not found")
    if not req.get("title"): raise HTTPException(status_code=422, detail="Deliverable title is required")
    d = ServiceDeliverable(workspace_id=wid, service_id=service_id, package_id=req.get("package_id"), title=req["title"], description=req.get("description"), format=req.get("format"), sort_order=req.get("sort_order", 0))
    db.add(d); db.commit()
    return _del_to_dict(d)

@router.post("/{service_id}/risk-rules", status_code=201)
def create_risk_rule(service_id: str, req: dict, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    if not get_service_or_none(db, wid, service_id): raise HTTPException(status_code=404, detail="Service not found")
    if not req.get("title"): raise HTTPException(status_code=422, detail="Risk rule title is required")
    sev = req.get("severity", "medium")
    if sev not in ("low", "medium", "high", "critical"): raise HTTPException(status_code=422, detail=f"Invalid severity: {sev}")
    r = ServiceRiskRule(workspace_id=wid, service_id=service_id, title=req["title"], description=req.get("description"), severity=sev, disqualifies=req.get("disqualifies", False), suggested_response=req.get("suggested_response"), sort_order=req.get("sort_order", 0))
    db.add(r); db.commit()
    return _rule_to_dict(r)

@router.patch("/{service_id}/packages/{package_id}")
def update_package(service_id: str, package_id: str, req: dict, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    pkg = db.query(ServicePackage).filter(ServicePackage.id == package_id, ServicePackage.service_id == service_id, ServicePackage.workspace_id == wid).first()
    if not pkg: raise HTTPException(status_code=404, detail="Package not found")
    for k in ["name", "description", "price_min", "price_max", "currency", "duration", "sort_order"]:
        if k in req: setattr(pkg, k, req[k])
    db.commit(); return _pkg_to_dict(pkg)

@router.patch("/{service_id}/deliverables/{deliverable_id}")
def update_deliverable(service_id: str, deliverable_id: str, req: dict, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    d = db.query(ServiceDeliverable).filter(ServiceDeliverable.id == deliverable_id, ServiceDeliverable.service_id == service_id, ServiceDeliverable.workspace_id == wid).first()
    if not d: raise HTTPException(status_code=404, detail="Deliverable not found")
    for k in ["title", "description", "format", "sort_order"]:
        if k in req: setattr(d, k, req[k])
    db.commit(); return _del_to_dict(d)

@router.patch("/{service_id}/risk-rules/{rule_id}")
def update_risk_rule(service_id: str, rule_id: str, req: dict, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    r = db.query(ServiceRiskRule).filter(ServiceRiskRule.id == rule_id, ServiceRiskRule.service_id == service_id, ServiceRiskRule.workspace_id == wid).first()
    if not r: raise HTTPException(status_code=404, detail="Risk rule not found")
    for k in ["title", "description", "severity", "disqualifies", "suggested_response", "sort_order"]:
        if k in req: setattr(r, k, req[k])
    db.commit(); return _rule_to_dict(r)

@router.delete("/{service_id}/packages/{package_id}")
def delete_package(service_id: str, package_id: str, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    pkg = db.query(ServicePackage).filter(ServicePackage.id == package_id, ServicePackage.service_id == service_id, ServicePackage.workspace_id == wid).first()
    if not pkg: raise HTTPException(status_code=404, detail="Package not found")
    db.delete(pkg); db.commit()
    return {"deleted": True}

@router.delete("/{service_id}/deliverables/{deliverable_id}")
def delete_deliverable(service_id: str, deliverable_id: str, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    d = db.query(ServiceDeliverable).filter(ServiceDeliverable.id == deliverable_id, ServiceDeliverable.service_id == service_id, ServiceDeliverable.workspace_id == wid).first()
    if not d: raise HTTPException(status_code=404, detail="Deliverable not found")
    db.delete(d); db.commit()
    return {"deleted": True}

@router.delete("/{service_id}/risk-rules/{rule_id}")
def delete_risk_rule(service_id: str, rule_id: str, db: Session = Depends(get_db)):
    wid = get_current_workspace_id(db)
    r = db.query(ServiceRiskRule).filter(ServiceRiskRule.id == rule_id, ServiceRiskRule.service_id == service_id, ServiceRiskRule.workspace_id == wid).first()
    if not r: raise HTTPException(status_code=404, detail="Risk rule not found")
    db.delete(r); db.commit()
    return {"deleted": True}


# Import at bottom to avoid circular
from app.models import Service
