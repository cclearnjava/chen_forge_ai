from app.db import SessionLocal
from app.models import Lead, AgentTask, Artifact, Decision, AuditLog
from app.services.agent_workflow import run_diagnosis, run_proposal, run_intake_response
from app.services.llm import MockLLMProvider


def _create_test_lead(db):
    lead = Lead(
        owner_email="agent-test@example.com",
        company="测试Agent公司",
        contact_method="email",
        problem="这是一个测试Agent工作流的业务问题，需要足够长的描述来满足最小长度要求",
        desired_outcome="企业知识库 / RAG 问答",
    )
    db.add(lead)
    db.commit()
    return lead


def test_run_diagnosis():
    db = SessionLocal()
    lead = _create_test_lead(db)

    result = run_diagnosis(db, lead.id)
    assert "task" in result
    assert result["task"]["status"] == "succeeded"
    assert "artifact" in result
    assert result["artifact"]["type"] == "requirement_summary"

    # Verify DB records
    task = db.query(AgentTask).filter(AgentTask.id == result["task"]["id"]).first()
    assert task is not None
    assert task.status.value == "succeeded"
    assert task.output_json is not None

    artifact = db.query(Artifact).filter(Artifact.id == result["artifact"]["id"]).first()
    assert artifact is not None
    assert artifact.type.value == "requirement_summary"
    assert artifact.requires_approval is False

    decision = db.query(Decision).filter(Decision.lead_id == lead.id).first()
    assert decision is not None

    # Audit log
    logs = db.query(AuditLog).filter(AuditLog.lead_id == lead.id).all()
    assert len(logs) >= 1


def test_run_proposal():
    db = SessionLocal()
    lead = _create_test_lead(db)

    result = run_proposal(db, lead.id)
    assert result["task"]["status"] == "succeeded"
    assert result["artifact"]["type"] == "proposal_draft"

    artifact = db.query(Artifact).filter(Artifact.id == result["artifact"]["id"]).first()
    assert artifact.requires_approval is True


def test_run_intake_response():
    db = SessionLocal()
    lead = _create_test_lead(db)

    result = run_intake_response(db, lead.id)
    assert result["task"]["status"] == "succeeded"
    assert len(result["artifacts"]) == 3
    assert len(result["decisions"]) == 2

    # Check artifact types
    types = [a["type"] for a in result["artifacts"]]
    assert "requirement_summary" in types
    assert "customer_reply_draft" in types
    assert "proposal_draft" in types

    # Check that lead status updated
    updated_lead = db.query(Lead).filter(Lead.id == lead.id).first()
    assert updated_lead.status.value == "diagnosed"


def test_run_diagnosis_nonexistent_lead():
    db = SessionLocal()
    try:
        run_diagnosis(db, "nonexistent-id")
        assert False, "Should have raised"
    except ValueError as e:
        assert "not found" in str(e)


def test_mock_llp_provider_modes():
    provider = MockLLMProvider(mode="success")
    result = provider.generate_json("lead_diagnosis", {"problem": "test"}, {})
    assert "pain_summary" in result

    error_provider = MockLLMProvider(mode="exception")
    try:
        error_provider.generate_json("lead_diagnosis", {}, {})
        assert False
    except RuntimeError:
        pass


def test_agent_workflow_creates_audit_log():
    db = SessionLocal()
    lead = _create_test_lead(db)
    run_diagnosis(db, lead.id)

    logs = db.query(AuditLog).filter(
        AuditLog.lead_id == lead.id,
        AuditLog.action == "agent_completed",
    ).all()
    assert len(logs) == 1


def test_agent_workflow_api(client):
    """Test the API endpoint triggers agent workflow."""
    from app.db import SessionLocal
    db = SessionLocal()
    lead = Lead(
        owner_email="api-agent@example.com",
        company="API测试Agent公司",
        contact_method="email",
        problem="API触发的Agent工作流测试问题描述足够了",
        desired_outcome="内部自动化 MVP",
    )
    db.add(lead)
    db.commit()

    response = client.post(
        f"/api/v1/leads/{lead.id}/run-diagnosis",
        headers={"Authorization": "Bearer admin-dev-token"},
    )
    assert response.status_code == 202
    data = response.json()
    assert "artifact" in data
    assert data["task"]["status"] == "succeeded"
