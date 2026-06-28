# WP-1 LOG: Backend Scaffold + Database Models

## Done

- FastAPI app scaffold: `backend/app/main.py` with CORS, health router
- Config: `backend/app/config.py` with pydantic-settings, `.env` loading
- Database: sync SQLAlchemy with SQLite (`backend/app/db.py`)
- Models: 9 models + 10 enums in `backend/app/models.py`
- Schemas: Pydantic request/response schemas in `backend/app/schemas.py`
- Health endpoint: `GET /api/v1/health` returns `{"status": "ok", "version": "0.1.0"}`
- Tests: 10 tests (1 health + 8 model creation + 1 enum count)
- venv created with all deps via Tsinghua mirror

## Deviations

- Switched from async SQLAlchemy to sync: `greenlet` package unavailable on mirrors. Sync is sufficient for MVP; upgrade path to async documented in ADR-001.
- Database URL transformed from `sqlite+aiosqlite:///` to `sqlite:///` in db.py.

## Commands

```bash
cd backend && .venv/bin/python -m pytest tests/ -v   # 10 passed
```
