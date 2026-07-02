"""BE-06: Proposal draft workflow tests — TDD-first."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.auth.verification import create_verification_code
from app.models import AgentRun, Artifact, ArtifactType, AuditLog, Decision, DecisionStatus

ADMIN = {"Authorization": "Bearer admin-dev-token"}


def _setup_opportunity(client: TestClient) -> str:
    """Create lead → lifecycle → return opportunity_id."""
    email = "proposal-test@example.com"
    db = SessionLocal()
    code = create_verification_code(db, email)
    db.close()

    r = client.post("/api/v1/auth/email/verify", json={"email": email, "code": code})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/api/v1/leads", json={
        "owner_email": email, "company": "提案测试公司", "contact_name": "吴总",
        "contact_method": "email", "industry": "电商零售",
        "problem": "提案生成测试需要一段足够长的客户业务问题描述文本内容填充",
        "desired_outcome": "智能推荐引擎", "company_size": "50-200",
        "budget_range": "5-10w", "timeline": "2个月",
        "honeypot": "", "submitted_after_ms": 2000,
    }, headers=headers)
    return r.json()["lifecycle"]["opportunity"]["id"]


def _add_customer_reply(client: TestClient, opp_id: str):
    """Record a customer reply to provide richer context."""
    client.post(f"/api/v1/admin/opportunities/{opp_id}/messages",
                json={"body_markdown": "我们希望先做两周的小 PoC，验证推荐准确率。"},
                headers=ADMIN)


class TestProposalDraftWorkflow:
    def test_generate_proposal_draft_creates_artifact(self, client: TestClient):
        init_db()
        opp_id = _setup_opportunity(client)
        _add_customer_reply(client, opp_id)

        r = client.post("/api/v1/admin/agent-runs/proposal-draft",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        assert r.status_code == 200
        data = r.json()
        assert data["artifact"]["type"] == "proposal_draft"
        assert data["artifact"]["requires_approval"] is True
        assert data["artifact"]["content_markdown"] is not None
        assert len(data["artifact"]["content_markdown"]) > 100

    def test_generate_proposal_draft_creates_waiting_decision(self, client: TestClient):
        init_db()
        opp_id = _setup_opportunity(client)
        _add_customer_reply(client, opp_id)

        r = client.post("/api/v1/admin/agent-runs/proposal-draft",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        assert r.status_code == 200
        decision = r.json()["decision"]
        assert decision["status"] == "waiting"
        assert "批准" in decision["question"]

    def test_generate_proposal_draft_creates_agent_run(self, client: TestClient):
        init_db()
        opp_id = _setup_opportunity(client)
        _add_customer_reply(client, opp_id)

        r = client.post("/api/v1/admin/agent-runs/proposal-draft",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        assert r.status_code == 200
        run = r.json()["agent_run"]
        assert run["status"] == "succeeded"
        assert run["started_at"] is not None
        assert run["completed_at"] is not None

    def test_generate_proposal_draft_writes_audit_log(self, client: TestClient):
        init_db()
        opp_id = _setup_opportunity(client)
        _add_customer_reply(client, opp_id)

        r = client.post("/api/v1/admin/agent-runs/proposal-draft",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        assert r.status_code == 200

        db = SessionLocal()
        logs = db.query(AuditLog).filter(AuditLog.action == "proposal_draft_generated").all()
        assert len(logs) >= 1
        details = logs[-1].details_json or {}
        assert "artifact_id" in details
        assert "decision_id" in details

    def test_generate_proposal_draft_missing_opportunity_returns_404(self, client: TestClient):
        init_db()
        r = client.post("/api/v1/admin/agent-runs/proposal-draft",
                        json={"opportunity_id": "nonexistent-id"}, headers=ADMIN)
        assert r.status_code == 404

    def test_generate_proposal_draft_repeat_creates_new_versions(self, client: TestClient):
        init_db()
        opp_id = _setup_opportunity(client)
        _add_customer_reply(client, opp_id)

        r1 = client.post("/api/v1/admin/agent-runs/proposal-draft",
                         json={"opportunity_id": opp_id}, headers=ADMIN)
        assert r1.status_code == 200

        r2 = client.post("/api/v1/admin/agent-runs/proposal-draft",
                         json={"opportunity_id": opp_id}, headers=ADMIN)
        assert r2.status_code == 200

        assert r1.json()["artifact"]["id"] != r2.json()["artifact"]["id"]

    def test_cockpit_lists_proposal_draft_in_descending_order(self, client: TestClient):
        init_db()
        opp_id = _setup_opportunity(client)
        _add_customer_reply(client, opp_id)

        client.post("/api/v1/admin/agent-runs/proposal-draft",
                    json={"opportunity_id": opp_id}, headers=ADMIN)
        client.post("/api/v1/admin/agent-runs/proposal-draft",
                    json={"opportunity_id": opp_id}, headers=ADMIN)

        r = client.get(f"/api/v1/admin/opportunities/{opp_id}/cockpit", headers=ADMIN)
        proposals = [a for a in r.json()["artifacts"] if a["type"] == "proposal_draft"]
        assert len(proposals) >= 2
        timestamps = [p["created_at"] for p in proposals]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_proposal_draft_contains_required_sections(self, client: TestClient):
        init_db()
        opp_id = _setup_opportunity(client)
        _add_customer_reply(client, opp_id)

        r = client.post("/api/v1/admin/agent-runs/proposal-draft",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        md = r.json()["artifact"]["content_markdown"]
        required = ["客户背景", "已确认目标", "PoC 范围", "不包含", "交付物", "时间计划", "假设", "风险", "需", "确认", "下一步"]
        for section in required:
            assert section in md, f"Missing section: {section}"

    def test_proposal_draft_avoids_overpromise_terms(self, client: TestClient):
        init_db()
        opp_id = _setup_opportunity(client)
        _add_customer_reply(client, opp_id)

        r = client.post("/api/v1/admin/agent-runs/proposal-draft",
                        json={"opportunity_id": opp_id}, headers=ADMIN)
        md = r.json()["artifact"]["content_markdown"]
        for kw in ["保证", "一定上线", "固定价格"]:
            assert kw not in md, f"Contains risky keyword: {kw}"
