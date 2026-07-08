"""Workspace service — provides default workspace for data scoping."""

from sqlalchemy.orm import Session
from app.models import Workspace

DEFAULT_WORKSPACE_SLUG = "chenforge-ai-consulting"
DEFAULT_WORKSPACE_NAME = "ChenForge AI Consulting Studio"


def get_or_create_default_workspace(db: Session) -> Workspace:
    """Return the default workspace, creating it if it doesn't exist. Idempotent."""
    ws = db.query(Workspace).filter(Workspace.is_default == True).first()
    if ws:
        return ws
    ws = db.query(Workspace).filter(Workspace.slug == DEFAULT_WORKSPACE_SLUG).first()
    if ws:
        ws.is_default = True
        db.commit()
        return ws
    ws = Workspace(
        slug=DEFAULT_WORKSPACE_SLUG,
        name=DEFAULT_WORKSPACE_NAME,
        industry="ai_consulting",
        business_type="consulting_studio",
        positioning="AI consulting and delivery studio for one-person company workflows",
        is_default=True,
    )
    db.add(ws)
    db.commit()
    return ws


def get_default_workspace_id(db: Session) -> str:
    """Return the id of the default workspace."""
    return get_or_create_default_workspace(db).id
