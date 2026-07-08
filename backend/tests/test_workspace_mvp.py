"""BE-11: Workspace MVP regression tests."""

from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.models import Workspace

ADMIN = {"Authorization": "Bearer admin-dev-token"}


class TestWorkspaceMvp:
    def test_default_workspace_is_created_once(self, client: TestClient):
        init_db()
        db = SessionLocal()
        ws1 = db.query(Workspace).filter(Workspace.slug == "chenforge-ai-consulting").first()
        assert ws1 is not None
        ws2 = db.query(Workspace).filter(Workspace.is_default == True).first()
        assert ws2 is not None
        assert ws1.id == ws2.id
        # Call again — should be idempotent
        from app.services.workspace import get_or_create_default_workspace
        ws3 = get_or_create_default_workspace(db)
        assert ws3.id == ws1.id
        db.close()

    def test_current_workspace_api_returns_default_workspace(self, client: TestClient):
        init_db()
        r = client.get("/api/v1/admin/workspace/current", headers=ADMIN)
        assert r.status_code == 200
        data = r.json()
        assert data["slug"] == "chenforge-ai-consulting"
        assert data["is_default"] is True

    def test_current_workspace_api_requires_admin(self, client: TestClient):
        init_db()
        r = client.get("/api/v1/admin/workspace/current")
        assert r.status_code in (401, 403)
