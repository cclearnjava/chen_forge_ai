"""Workspace isolation guard — all admin endpoints must scope queries by workspace."""

from fastapi import HTTPException
from sqlalchemy.orm import Session, Query
from app.services.workspace import get_default_workspace_id


def get_current_workspace_id(db: Session) -> str:
    """Return the current workspace id (MVP: always default workspace)."""
    return get_default_workspace_id(db)


def filter_current_workspace(query: Query, model, db: Session) -> Query:
    """Add NULL-safe workspace_id filter to an existing query."""
    wid = get_current_workspace_id(db)
    col = getattr(model, "workspace_id", None)
    if col is None:
        return query
    return query.filter((col == wid) | (col.is_(None)))


def get_scoped_or_404(db: Session, model, object_id: str, *, label: str = "Object"):
    """Fetch an object by id, scoped to current workspace. Returns 404 if not found or wrong workspace."""
    wid = get_current_workspace_id(db)
    col = getattr(model, "workspace_id", None)
    if col is None:
        obj = db.query(model).filter(model.id == object_id).first()
    else:
        obj = db.query(model).filter(model.id == object_id, (col == wid) | (col.is_(None))).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def inherit_workspace_id(parent_obj, db: Session) -> str:
    """Return parent's workspace_id if available, otherwise current workspace id."""
    wid = getattr(parent_obj, "workspace_id", None)
    return wid if wid else get_current_workspace_id(db)


def require_workspace_id(obj, label: str = "Object") -> None:
    """Raise ValueError if object has no workspace_id."""
    wid = getattr(obj, "workspace_id", None)
    if not wid:
        raise ValueError(f"{label} has no workspace_id")


def assert_same_workspace(parent, child, parent_label: str = "Parent", child_label: str = "Child") -> None:
    """Raise ValueError if parent and child don't share the same workspace."""
    p_wid = getattr(parent, "workspace_id", None)
    c_wid = getattr(child, "workspace_id", None)
    if p_wid and c_wid and p_wid != c_wid:
        raise ValueError(f"{child_label} workspace ({c_wid}) does not match {parent_label} workspace ({p_wid})")


def scoped_artifacts_for_opportunity(db: Session, opp, *artifact_types) -> list:
    """Return artifacts for an opportunity, scoped to its workspace."""
    from app.models import Artifact
    wid = inherit_workspace_id(opp, db)
    query = db.query(Artifact).filter(
        Artifact.opportunity_id == opp.id,
        (Artifact.workspace_id == wid) | (Artifact.workspace_id.is_(None)),
    )
    if artifact_types:
        query = query.filter(Artifact.type.in_(artifact_types))
    return query.order_by(Artifact.created_at.desc()).all()
