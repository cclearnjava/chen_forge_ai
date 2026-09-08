"""Provider-neutral retrieval entry point. External activation is gated until E2."""

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from time import monotonic
from typing import Protocol

from sqlalchemy.orm import Session

from app.models import WorkspaceKnowledgeConfig
from app.schemas import CitationPackV2
from app.services.knowledge_retriever import RETRIEVER_VERSION, retrieve_knowledge_for_sales_reply


class KnowledgeEngineError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class KnowledgeEngineProvider(Protocol):
    def retrieve(
        self, db: Session, *, workspace_id: str, query_text: str,
        matched_service_ids: list[str] | None = None, max_hits: int = 5,
        config_version: int = 0,
    ) -> dict: ...


def normalize_local_citation_pack(
    pack: dict, *, config_version: int = 0, latency_ms: float = 0,
) -> dict:
    """Return a v2 snapshot without mutating a retriever result or saved artifact."""
    result = deepcopy(pack)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    hits = result.get("hits", [])
    for rank, hit in enumerate(hits, start=1):
        hit.update(
            provider="local", reference_id=f"local:{hit['knowledge_item_id']}",
            external_reference_id=None, rank=rank, retrieved_at=retrieved_at,
            content_hash=sha256(hit.get("excerpt", "").encode("utf-8")).hexdigest(),
        )
    result.update(
        schema_version=2, provider="local", config_version=config_version,
        retrieved_at=retrieved_at, latency_ms=latency_ms,
        hit_count=len(hits), hits=hits, status="ok" if hits else "empty",
    )
    CitationPackV2.model_validate(result)
    return result


class LocalKnowledgeEngineProvider:
    def retrieve(
        self, db: Session, *, workspace_id: str, query_text: str,
        matched_service_ids: list[str] | None = None, max_hits: int = 5,
        config_version: int = 0,
    ) -> dict:
        started = monotonic()
        result = retrieve_knowledge_for_sales_reply(
            db, workspace_id=workspace_id, query_text=query_text,
            matched_service_ids=matched_service_ids, max_hits=max_hits,
        )
        return normalize_local_citation_pack(
            result, config_version=config_version, latency_ms=(monotonic() - started) * 1000,
        )


def retrieve_knowledge(
    db: Session, *, workspace_id: str | None, query_text: str,
    matched_service_ids: list[str] | None = None, max_hits: int = 5,
) -> dict:
    if not isinstance(max_hits, int) or isinstance(max_hits, bool) or not 1 <= max_hits <= 5:
        raise KnowledgeEngineError("invalid_retrieval_request")
    # Pre-workspace opportunities may still generate drafts, but cannot retrieve unscoped knowledge.
    if workspace_id is None:
        return normalize_local_citation_pack({
            "retriever_version": RETRIEVER_VERSION, "hits": [],
            "query_summary": query_text[:120] if query_text else None,
            "no_hit_reason": "workspace_missing",
        })
    if not workspace_id.strip():
        raise KnowledgeEngineError("invalid_retrieval_request")
    config = db.query(WorkspaceKnowledgeConfig).filter_by(workspace_id=workspace_id).first()
    # A persisted but unsupported external selection must never silently read local data.
    if config is not None and config.provider != "local":
        raise KnowledgeEngineError("knowledge_engine_not_ready")
    return LocalKnowledgeEngineProvider().retrieve(
        db, workspace_id=workspace_id, query_text=query_text,
        matched_service_ids=matched_service_ids, max_hits=max_hits,
        config_version=config.version if config else 0,
    )
