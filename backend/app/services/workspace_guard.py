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
