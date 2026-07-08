from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.workspace import get_default_workspace_id
from app.services.workspace_guard import get_scoped_or_404
from app.auth.middleware import get_admin_email
from app.models import AuditLog, Conversation, Message, MessageSenderType
from app.schemas import MessageCreate

router = APIRouter(tags=["conversations"])


@router.get("/admin/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    conv = get_scoped_or_404(db, Conversation, conversation_id, label="Conversation")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    return {
        "conversation_id": conversation_id,
        "messages": [_message_to_dict(m) for m in messages],
    }


@router.post("/admin/conversations/{conversation_id}/messages", status_code=201)
def create_message(
    conversation_id: str,
    req: MessageCreate,
    db: Session = Depends(get_db),
    admin: str = Depends(get_admin_email),
):
    conv = get_scoped_or_404(db, Conversation, conversation_id, label="Conversation")

    try:
        sender_type = MessageSenderType(req.sender_type)
    except ValueError:
        allowed = [e.value for e in MessageSenderType]
        raise HTTPException(status_code=422, detail=f"Invalid sender_type. Allowed: {allowed}")

    wid = conv.workspace_id or get_default_workspace_id(db)
    message = Message(
        workspace_id=wid,
        conversation_id=conversation_id,
        customer_id=conv.customer_id,
        contact_id=conv.primary_contact_id,
        sender_type=sender_type,
        sender_label=admin,
        body_markdown=req.body_markdown,
        source=req.source,
    )
    db.add(message)
    db.flush()

    db.add(AuditLog(
        workspace_id=wid,
        lead_id=conv.lead_id,
        actor=admin,
        action="message_created",
        details_json={
            "conversation_id": conversation_id,
            "message_id": message.id,
            "sender_type": req.sender_type,
            "source": req.source,
        },
    ))

    db.commit()
    db.refresh(message)
    return {"message": _message_to_dict(message)}


def _message_to_dict(m: Message) -> dict:
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "customer_id": m.customer_id,
        "contact_id": m.contact_id,
        "sender_type": m.sender_type.value if hasattr(m.sender_type, "value") else m.sender_type,
        "sender_label": m.sender_label,
        "body_markdown": m.body_markdown,
        "source": m.source,
        "external_message_id": m.external_message_id,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
