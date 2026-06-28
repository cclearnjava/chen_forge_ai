from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.models import Artifact, Decision
from app.schemas import ArtifactUpdate, ArtifactApprove

router = APIRouter(tags=["artifacts"])


def _artifact_to_dict(a: Artifact) -> dict:
    return {
        "id": a.id, "lead_id": a.lead_id, "type": a.type.value,
        "title": a.title, "content_markdown": a.content_markdown,
        "content_json": a.content_json, "model": a.model,
        "prompt_version": a.prompt_version, "requires_approval": a.requires_approval,
        "approved_at": a.approved_at.isoformat() if a.approved_at else None,
        "version_history": a.version_history,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/leads/{lead_id}/artifacts")
def list_artifacts(
    lead_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    items = db.query(Artifact).filter(Artifact.lead_id == lead_id).order_by(Artifact.created_at.desc()).all()
    return {"items": [_artifact_to_dict(a) for a in items]}


@router.get("/artifacts/{artifact_id}")
def get_artifact(
    artifact_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    a = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"artifact": _artifact_to_dict(a)}


@router.patch("/artifacts/{artifact_id}")
def update_artifact(
    artifact_id: str,
    req: ArtifactUpdate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    a = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Artifact not found")

    history = a.version_history or []
    history.append({
        "content_markdown": a.content_markdown,
        "edited_at": __import__("datetime").datetime.utcnow().isoformat(),
        "operator_note": req.operator_note,
    })

    a.content_markdown = req.content_markdown
    a.version_history = history
    db.commit()
    return {"artifact": _artifact_to_dict(a)}


@router.post("/artifacts/{artifact_id}/approve")
def approve_artifact(
    artifact_id: str,
    req: ArtifactApprove = ArtifactApprove(),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    a = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Artifact not found")

    from datetime import datetime as dt
    a.requires_approval = False
    a.approved_at = dt.utcnow()
    db.commit()
    return {"artifact": _artifact_to_dict(a)}
