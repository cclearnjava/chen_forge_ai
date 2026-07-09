"""External Connector management — workspace-scoped connector CRUD (P5)."""

import secrets
from sqlalchemy.orm import Session
from app.models import ExternalConnector


def generate_webhook_token() -> str:
    return secrets.token_urlsafe(24)


def list_connectors(db: Session, workspace_id: str) -> list[ExternalConnector]:
    return db.query(ExternalConnector).filter(
        ExternalConnector.workspace_id == workspace_id,
    ).order_by(ExternalConnector.created_at.desc()).all()


def create_connector(db: Session, workspace_id: str, data: dict) -> ExternalConnector:
    conn = ExternalConnector(
        workspace_id=workspace_id,
        provider=data["provider"],
        name=data["name"],
        config_json=data.get("config_json") or {},
        secret_ref=data.get("secret_ref"),
        webhook_token=generate_webhook_token(),
    )
    db.add(conn)
    db.flush()
    return conn


def update_connector(db: Session, workspace_id: str, connector_id: str, data: dict) -> ExternalConnector | None:
    conn = db.query(ExternalConnector).filter(
        ExternalConnector.id == connector_id,
        ExternalConnector.workspace_id == workspace_id,
    ).first()
    if not conn:
        return None
    for k in ("name", "status", "config_json", "secret_ref"):
        if k in data and data[k] is not None:
            setattr(conn, k, data[k])
    db.flush()
    return conn


def get_connector_by_token(db: Session, token: str) -> ExternalConnector | None:
    """Find a connector by webhook token, regardless of status (caller checks active)."""
    return db.query(ExternalConnector).filter(
        ExternalConnector.webhook_token == token,
    ).first()
