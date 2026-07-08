from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.services.workspace import get_or_create_default_workspace, get_default_workspace_id

router = APIRouter(tags=["workspace"])


def _workspace_to_dict(ws) -> dict:
    return {
        "id": ws.id, "name": ws.name, "slug": ws.slug,
        "industry": ws.industry, "business_type": ws.business_type,
        "positioning": ws.positioning, "is_default": ws.is_default,
        "created_at": ws.created_at.isoformat() if ws.created_at else None,
        "updated_at": ws.updated_at.isoformat() if ws.updated_at else None,
    }


@router.get("/admin/workspace/current")
def get_current_workspace(
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    ws = get_or_create_default_workspace(db)
    return _workspace_to_dict(ws)
