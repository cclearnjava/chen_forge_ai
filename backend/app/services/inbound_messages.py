"""Inbound message processing — normalize external channel messages into
Customer / Contact / Conversation / Message, then record Event + Notification (P5).

Workspace isolation: everything is scoped to connector.workspace_id.
Contact matching: fixed priority external_user_id(+provider) → email → phone,
all workspace-scoped. Empty identity fields are backfilled on any match.
Fail-closed: caller (API) owns the transaction; any exception rolls back.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import (
    Contact, Conversation, ConversationStatus, Customer,
    ExternalConnector, Message, MessageSenderType, Notification,
)
from app.services.events import record_event


def _provider_str(provider) -> str:
    return provider.value if hasattr(provider, "value") else provider


def _source_for(connector: ExternalConnector) -> str:
    return f"external_{_provider_str(connector.provider)}"


def _status_str(connector: ExternalConnector) -> str:
    return connector.status.value if hasattr(connector.status, "value") else connector.status


def normalize_phone(value: str | None) -> str | None:
    """Lightweight phone normalization: keep a leading '+' and digits only."""
    if not value:
        return None
    s = value.strip()
    plus = s.startswith("+")
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return None
    return ("+" + digits) if plus else digits


def find_contact_for_inbound_sender(db: Session, workspace_id: str, provider: str, sender: dict) -> Contact | None:
    """Match an existing Contact by identity, in fixed priority, workspace-scoped.

    1. external_provider + external_user_id
    2. email
    3. normalized phone
    """
    euid = sender.get("external_user_id")
    if euid:
        c = db.query(Contact).filter(
            Contact.workspace_id == workspace_id,
            Contact.external_provider == provider,
            Contact.external_user_id == euid,
        ).first()
        if c:
            return c
    email = sender.get("email")
    if email:
        c = db.query(Contact).filter(
            Contact.workspace_id == workspace_id, Contact.email == email,
        ).first()
        if c:
            return c
    phone = normalize_phone(sender.get("phone"))
    if phone:
        c = db.query(Contact).filter(
            Contact.workspace_id == workspace_id, Contact.phone == phone,
        ).first()
        if c:
            return c
    return None


def _backfill_identity(contact: Contact, provider: str, sender: dict, norm_phone: str | None) -> None:
    """Fill empty identity fields on a matched Contact. Never overwrite existing values."""
    if norm_phone and not contact.phone:
        contact.phone = norm_phone
    euid = sender.get("external_user_id")
    if euid and not contact.external_user_id:
        contact.external_user_id = euid
        if not contact.external_provider:
            contact.external_provider = provider
    email = sender.get("email")
    if email and not contact.email:
        contact.email = email


def _create_conversation(db: Session, wid: str, customer: Customer, contact: Contact, connector: ExternalConnector) -> Conversation:
    conv = Conversation(
        workspace_id=wid,
        customer_id=customer.id,
        primary_contact_id=contact.id,
        title=f"外部消息 · {customer.name}",
        channel=_source_for(connector),
        status=ConversationStatus.open,
    )
    db.add(conv)
    db.flush()
    return conv


def process_inbound_message(db: Session, connector: ExternalConnector, payload: dict) -> dict:
    """Process one normalized inbound message. Returns a result dict with ORM objects.

    Raises ValueError('connector is not active') if the connector is paused/disabled.
    """
    wid = connector.workspace_id
    if _status_str(connector) != "active":
        raise ValueError("connector is not active")

    ext_msg_id = payload["external_message_id"]
    sender = payload.get("sender") or {}

    # Idempotency: workspace + connector + external_message_id
    existing = db.query(Message).filter(
        Message.workspace_id == wid,
        Message.external_connector_id == connector.id,
        Message.external_message_id == ext_msg_id,
    ).first()
    if existing:
        customer = db.query(Customer).filter(Customer.id == existing.customer_id).first()
        contact = db.query(Contact).filter(Contact.id == existing.contact_id).first() if existing.contact_id else None
        conversation = db.query(Conversation).filter(Conversation.id == existing.conversation_id).first()
        return {
            "deduplicated": True, "connector": connector, "customer": customer,
            "contact": contact, "conversation": conversation, "message": existing,
            "event": None, "notification": None,
        }

    # Contact matching: external_user_id (+provider) → email → phone, workspace-scoped
    provider = _provider_str(connector.provider)
    norm_phone = normalize_phone(sender.get("phone"))
    contact = find_contact_for_inbound_sender(db, wid, provider, sender)

    if contact:
        _backfill_identity(contact, provider, sender, norm_phone)
        customer = db.query(Customer).filter(
            Customer.id == contact.customer_id, Customer.workspace_id == wid,
        ).first()
        conversation = db.query(Conversation).filter(
            Conversation.workspace_id == wid,
            Conversation.customer_id == customer.id,
            Conversation.status != ConversationStatus.closed,
        ).order_by(Conversation.updated_at.desc()).first()
        if not conversation:
            conversation = _create_conversation(db, wid, customer, contact, connector)
    else:
        email = sender.get("email")
        display = sender.get("name") or email or norm_phone or sender.get("external_user_id") or "外部客户"
        customer = Customer(workspace_id=wid, name=display, owner_email=email or "")
        db.add(customer)
        db.flush()
        contact = Contact(
            workspace_id=wid, customer_id=customer.id, name=sender.get("name"),
            email=email, phone=norm_phone,
            external_provider=provider, external_user_id=sender.get("external_user_id"),
            contact_method=email or norm_phone or sender.get("external_user_id"),
            is_primary=True,
        )
        db.add(contact)
        db.flush()
        conversation = _create_conversation(db, wid, customer, contact, connector)

    message = Message(
        workspace_id=wid,
        conversation_id=conversation.id,
        customer_id=customer.id,
        contact_id=contact.id,
        sender_type=MessageSenderType.customer,
        sender_label=sender.get("name"),
        body_markdown=payload["body_markdown"],
        source=_source_for(connector),
        external_message_id=ext_msg_id,
        external_connector_id=connector.id,
        external_thread_id=payload.get("external_thread_id"),
        raw_payload_json=payload.get("raw_payload") or {},
    )
    db.add(message)
    db.flush()

    connector.last_received_at = datetime.now(timezone.utc)

    body_preview = (payload["body_markdown"] or "")[:80]
    event = record_event(
        db, workspace_id=wid, type="external_message.received", source="external_connector",
        subject_type="message", subject_id=message.id,
        title="新客户消息",
        summary=f"{sender.get('name') or '客户'}：{body_preview}",
        target_type="conversation", target_id=conversation.id,
        payload_json={
            "connector_id": connector.id,
            "provider": _provider_str(connector.provider),
            "message_id": message.id,
            "conversation_id": conversation.id,
            "customer_id": customer.id,
            "contact_id": contact.id,
            "external_message_id": ext_msg_id,
        },
    )
    notification = None
    if event is not None:
        notification = db.query(Notification).filter(Notification.event_id == event.id).first()

    return {
        "deduplicated": False, "connector": connector, "customer": customer,
        "contact": contact, "conversation": conversation, "message": message,
        "event": event, "notification": notification,
    }
