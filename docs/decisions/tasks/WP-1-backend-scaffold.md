# WP-1: Backend Scaffold + Database Models

- **Goal**: FastAPI 应用骨架、9 个 SQLAlchemy 模型、SQLite 数据库、settings/config、健康检查端点。
- **Write set**: `backend/app/main.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/api/__init__.py`, `backend/requirements.txt`, `backend/.env.example`
- **Depends on**: 无
- **Parallel with**: WP-2, WP-4, WP-5 (但 WP-2/WP-4/WP-5 需等待 WP-1 的 models/schemas)
- **Seam owner**: WP-1 负责所有模型和 schema 定义，是其他 WP 的契约源
- **Acceptance test**:
  - `pytest` 能运行并通过健康检查测试
  - 9 个模型能成功创建表（SQLite）
  - `POST /api/v1/health` 返回 200
  - 所有枚举值（LeadStatus, TaskStatus, DecisionStatus, ArtifactType, DeliveryChannel, DeliveryStatus）正确定义
  - settings 从 `.env` 正确加载
