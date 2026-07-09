from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.services.workspace_guard import get_current_workspace_id
from app.services.external_connectors import (
    create_connector, get_connector_by_token, list_connectors, update_connector,
)
from app.services.inbound_messages import process_inbound_message
from app.schemas import (
    ExternalConnectorCreate, ExternalConnectorUpdate, InboundMessageCreateIn,
)

router = APIRouter(tags=["connectors"])

INBOUND_PATH = "/api/v1/connectors/{webhook_token}/inbound"


def _connector_to_dict(c) -> dict:
    return {
        "id": c.id, "workspace_id": c.workspace_id,
        "provider": c.provider.value if hasattr(c.provider, "value") else c.provider,
        "name": c.name,
        "status": c.status.value if hasattr(c.status, "value") else c.status,
        "config_json": c.config_json, "secret_ref": c.secret_ref,
        "webhook_token": c.webhook_token,
        "webhook_path": INBOUND_PATH.replace("{webhook_token}", c.webhook_token) if c.webhook_token else None,
        "last_received_at": c.last_received_at.isoformat() if c.last_received_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _customer_dict(c):
    return None if not c else {"id": c.id, "name": c.name, "owner_email": c.owner_email,
                               "industry": c.industry, "company_size": c.company_size}


def _contact_dict(c):
    return None if not c else {"id": c.id, "name": c.name, "email": c.email,
                               "contact_method": c.contact_method, "is_primary": c.is_primary}


def _conversation_dict(c):
    return None if not c else {"id": c.id, "title": c.title, "channel": c.channel,
                               "status": c.status.value if hasattr(c.status, "value") else c.status}


def _message_dict(m):
    return None if not m else {
        "id": m.id, "sender_type": m.sender_type.value if hasattr(m.sender_type, "value") else m.sender_type,
        "sender_label": m.sender_label, "body_markdown": m.body_markdown, "source": m.source,
        "external_message_id": m.external_message_id, "external_thread_id": m.external_thread_id,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


# ── Admin connector management (admin auth) ──

@router.get("/admin/connectors")
def list_connectors_api(db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    items = list_connectors(db, wid)
    return {"items": [_connector_to_dict(c) for c in items], "total": len(items)}


@router.post("/admin/connectors", status_code=201)
def create_connector_api(req: ExternalConnectorCreate, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    conn = create_connector(db, wid, req.model_dump())
    db.commit()
    return _connector_to_dict(conn)


@router.patch("/admin/connectors/{connector_id}")
def update_connector_api(connector_id: str, req: ExternalConnectorUpdate, db: Session = Depends(get_db), _admin: str = Depends(get_admin_email)):
    wid = get_current_workspace_id(db)
    conn = update_connector(db, wid, connector_id, req.model_dump(exclude_unset=True))
    if not conn:
        raise HTTPException(status_code=404, detail="Connector not found")
    db.commit()
    return _connector_to_dict(conn)


# ── Inbound webhook (token auth only, NO admin dependency) ──

@router.post("/connectors/{webhook_token}/inbound")
def inbound_webhook(webhook_token: str, req: InboundMessageCreateIn, db: Session = Depends(get_db)):
    connector = get_connector_by_token(db, webhook_token)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    try:
        result = process_inbound_message(db, connector, req.model_dump())
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Inbound processing failed")

    return {
        "deduplicated": result["deduplicated"],
        "connector_id": connector.id,
        "customer": _customer_dict(result["customer"]),
        "contact": _contact_dict(result["contact"]),
        "conversation": _conversation_dict(result["conversation"]),
        "message": _message_dict(result["message"]),
        "event_id": result["event"].id if result["event"] else None,
        "notification_id": result["notification"].id if result["notification"] else None,
    }
