"""Provider-neutral citations and workspace-isolated integration foundations."""

import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base
from app.models import KnowledgeItem, Workspace
from app.services import knowledge_retriever


@pytest.fixture
def db():
    # Constraint tests must not change PRAGMA state on the shared application pool.
    engine = create_engine("sqlite://")
    try:
        with engine.connect() as connection:
            connection.execute(text("PRAGMA foreign_keys=ON"))
            connection.commit()
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            yield session
            session.rollback()
    finally:
        engine.dispose()


def workspace(db):
    row = Workspace(id=str(uuid.uuid4()), slug=uuid.uuid4().hex, name="Engine tests")
    db.add(row)
    db.flush()
    return row.id


def test_local_adapter_keeps_ranking_and_existing_fields(db):
    from app.services.knowledge_engine import retrieve_knowledge

    wid = workspace(db)
    item = KnowledgeItem(workspace_id=wid, title="Deployment", content_markdown="Private deployment",
                         source_type="manual", status="active")
    db.add(item)
    db.flush()
    old = knowledge_retriever.retrieve_knowledge_for_sales_reply(db, workspace_id=wid, query_text="deployment")
    pack = retrieve_knowledge(db, workspace_id=wid, query_text="deployment")
    assert pack["schema_version"] == 2
    assert pack["provider"] == "local"
    assert pack["config_version"] == 0
    assert pack["status"] == "ok"
    assert pack["hit_count"] == old["hit_count"]
    for old_hit, hit in zip(old["hits"], pack["hits"], strict=True):
        assert all(hit[key] == value for key, value in old_hit.items())
        assert hit["reference_id"] == f"local:{item.id}"
        assert hit["provider"] == "local"
        assert hit["external_reference_id"] is None
        assert len(hit["content_hash"]) == 64


def test_empty_local_pack_and_workspace_isolation(db):
    from app.services.knowledge_engine import retrieve_knowledge

    wid, other = workspace(db), workspace(db)
    db.add(KnowledgeItem(workspace_id=other, title="secret", content_markdown="secret",
                         source_type="manual", status="active"))
    db.flush()
    pack = retrieve_knowledge(db, workspace_id=wid, query_text="secret")
    assert pack["status"] == "empty"
    assert pack["hits"] == []
    assert pack["no_hit_reason"] == "no_active_knowledge"


def test_explicit_external_config_fails_closed_until_adapter_available(db):
    from app.models import KnowledgeEngineConnection, WorkspaceKnowledgeConfig
    from app.services.knowledge_engine import KnowledgeEngineError, retrieve_knowledge

    wid = workspace(db)
    conn = KnowledgeEngineConnection(workspace_id=wid, display_name="Private KB", endpoint_alias="private",
                                     credential_ref="kb-reader", knowledge_base_id="kb-1")
    db.add(conn)
    db.flush()
    db.add(WorkspaceKnowledgeConfig(workspace_id=wid, provider="weknora", connection_id=conn.id))
    db.flush()
    with pytest.raises(KnowledgeEngineError, match="knowledge_engine_not_ready"):
        retrieve_knowledge(db, workspace_id=wid, query_text="secret")


def test_workspace_configuration_is_unique(db):
    from app.models import WorkspaceKnowledgeConfig

    wid = workspace(db)
    db.add(WorkspaceKnowledgeConfig(workspace_id=wid))
    db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(WorkspaceKnowledgeConfig(workspace_id=wid))
        db.flush()


def test_connection_and_reference_cannot_cross_workspace(db):
    from app.models import ExternalKnowledgeReference, KnowledgeEngineConnection, WorkspaceKnowledgeConfig

    wid, other = workspace(db), workspace(db)
    conn = KnowledgeEngineConnection(workspace_id=wid, endpoint_alias="private", credential_ref="reader",
                                     display_name="KB", knowledge_base_id="kb-1")
    db.add(conn)
    db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(WorkspaceKnowledgeConfig(workspace_id=other, provider="weknora", connection_id=conn.id))
        db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(ExternalKnowledgeReference(workspace_id=other, connection_id=conn.id,
                                          knowledge_base_id="kb-1", external_knowledge_id="doc",
                                          external_chunk_id="chunk", title="Private"))
        db.flush()


def test_external_reference_identity_is_scoped_and_unique(db):
    from app.models import ExternalKnowledgeReference, KnowledgeEngineConnection

    for _ in range(2):
        wid = workspace(db)
        conn = KnowledgeEngineConnection(workspace_id=wid, endpoint_alias="private", credential_ref="reader",
                                         display_name="KB", knowledge_base_id="kb-1")
        db.add(conn)
        db.flush()
        data = dict(workspace_id=wid, connection_id=conn.id, knowledge_base_id="kb-1",
                    external_knowledge_id="same-doc", external_chunk_id="same-chunk", title="Source")
        db.add(ExternalKnowledgeReference(**data))
        db.flush()
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(ExternalKnowledgeReference(**data))
            db.flush()


def test_connection_schema_does_not_accept_raw_secrets():
    from pydantic import ValidationError
    from app.schemas import KnowledgeEngineConnectionCreate

    with pytest.raises(ValidationError):
        KnowledgeEngineConnectionCreate(endpoint_alias="private", credential_ref="reader",
                                        knowledge_base_id="kb-1", api_key="do-not-store")


def test_local_citation_contract_rejects_external_id():
    from pydantic import ValidationError
    from app.schemas import KnowledgeCitationHitV2

    with pytest.raises(ValidationError):
        KnowledgeCitationHitV2(provider="local", reference_id="local:item", knowledge_item_id="item",
                              external_reference_id="external", title="title", excerpt="text",
                              score=1, source_type="manual", rank=1, content_hash="a" * 64,
                              retrieved_at="2026-09-08T00:00:00Z")


def test_external_citation_never_requires_local_id():
    from app.schemas import KnowledgeCitationHitV2

    hit = KnowledgeCitationHitV2(provider="weknora", reference_id="external:ref", external_reference_id="ref",
                                title="title", excerpt="text", score=0.9, source_type="external_doc", rank=1,
                                content_hash="a" * 64, retrieved_at="2026-09-08T00:00:00Z")
    assert hit.knowledge_item_id is None


def test_legacy_citation_normalization_does_not_change_history():
    from app.services.knowledge_engine import normalize_local_citation_pack

    old = {"retriever_version": "v1", "hit_count": 1, "hits": [
        {"knowledge_item_id": "item", "title": "Source", "excerpt": "Original", "score": 3,
         "source_type": "manual", "match_reasons": ["title"]},
    ]}
    pack = normalize_local_citation_pack(old)
    pack["hits"][0]["match_reasons"].append("changed")
    assert "schema_version" not in old
    assert "reference_id" not in old["hits"][0]
    assert old["hits"][0]["match_reasons"] == ["title"]


def test_legacy_opportunity_without_workspace_gets_no_knowledge(db):
    from app.services.knowledge_engine import retrieve_knowledge

    db.add(KnowledgeItem(title="unscoped", content_markdown="legacy secret", status="active"))
    db.flush()
    pack = retrieve_knowledge(db, workspace_id=None, query_text="secret")
    assert pack["hits"] == []
    assert pack["no_hit_reason"] == "workspace_missing"


@pytest.mark.parametrize("provider,connection_id", [("weknora", None), ("other", None), ("local", "unexpected")])
def test_invalid_provider_configuration_is_rejected(db, provider, connection_id):
    from app.models import WorkspaceKnowledgeConfig

    wid = workspace(db)
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(WorkspaceKnowledgeConfig(workspace_id=wid, provider=provider, connection_id=connection_id))
        db.flush()


def test_connection_cannot_be_ready_without_matching_verification(db):
    from app.models import KnowledgeEngineConnection

    wid = workspace(db)
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(KnowledgeEngineConnection(workspace_id=wid, display_name="KB", endpoint_alias="private",
                                         credential_ref="reader", knowledge_base_id="kb-1", status="ready",
                                         revision=2, verified_revision=1))
        db.flush()


@pytest.mark.parametrize("max_hits", [0, -1, 6, True, 1.5])
def test_retrieval_has_bounded_hit_count(db, max_hits):
    from app.services.knowledge_engine import KnowledgeEngineError, retrieve_knowledge

    with pytest.raises(KnowledgeEngineError, match="invalid_retrieval_request"):
        retrieve_knowledge(db, workspace_id="workspace", query_text="question", max_hits=max_hits)


def test_local_config_revision_is_recorded(db):
    from app.models import WorkspaceKnowledgeConfig
    from app.services.knowledge_engine import retrieve_knowledge

    wid = workspace(db)
    db.add(WorkspaceKnowledgeConfig(workspace_id=wid, version=3))
    db.flush()
    assert retrieve_knowledge(db, workspace_id=wid, query_text="question")["config_version"] == 3


def test_workflow_preserves_v2_citations_and_waiting_approval(db):
    from app.models import Customer, Opportunity
    from app.services.sales_reply_workflow import run_sales_reply_workflow

    wid = workspace(db)
    customer = Customer(workspace_id=wid, name="Test Company", owner_email="test@example.com")
    db.add(customer)
    db.flush()
    opportunity = Opportunity(workspace_id=wid, customer_id=customer.id, title="Private deployment")
    item = KnowledgeItem(workspace_id=wid, title="Private deployment", content_markdown="Requires review",
                         source_type="manual", status="active")
    db.add_all([opportunity, item])
    db.flush()
    result = run_sales_reply_workflow(db, opportunity.id)
    draft = result["artifacts"][0]
    pack = draft.content_json["citations"]
    assert pack["schema_version"] == 2
    assert pack["hits"][0]["reference_id"] == f"local:{item.id}"
    assert draft.content_json["context_usage"]["used_reference_ids"] == [f"local:{item.id}"]
    assert draft.content_json["context_usage"]["used_knowledge_item_ids"] == [item.id]
    assert draft.requires_approval
    assert result["decision"].status.value == "waiting"


def test_existing_database_upgrade_preserves_knowledge(monkeypatch):
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import sessionmaker
    from app import db as database

    new_tables = {"knowledge_engine_connections", "workspace_knowledge_configs", "external_knowledge_references"}
    engine = create_engine("sqlite://")
    sessions = sessionmaker(engine)
    try:
        database.Base.metadata.create_all(engine, tables=[
            table for table in database.Base.metadata.sorted_tables if table.name not in new_tables
        ])
        with sessions() as session:
            wid = workspace(session)
            item = KnowledgeItem(workspace_id=wid, title="Before upgrade", content_markdown="Keep me", status="active")
            session.add(item)
            session.flush()
            item_id = item.id
            session.commit()
        monkeypatch.setattr(database, "engine", engine)
        monkeypatch.setattr(database, "SessionLocal", sessions)
        database.init_db()
        database.init_db()
        assert new_tables <= set(inspect(engine).get_table_names())
        with sessions() as session:
            assert session.get(KnowledgeItem, item_id).content_markdown == "Keep me"
    finally:
        engine.dispose()
