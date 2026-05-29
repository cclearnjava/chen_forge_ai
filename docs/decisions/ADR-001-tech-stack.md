# ADR-001：MVP 技术栈选择

## 状态

Accepted

## 背景

ChenForge AI 的一周 MVP 需要同时完成公开门户、线索提交、私有后台、后端 API、数据库持久化和第一条 Agent 工作流。技术栈必须降低启动成本，同时保留后续演进空间。

## 决策

- 前端使用 Next.js + TypeScript。
- 样式使用 CSS Modules 或 Tailwind CSS，优先保证设计 token 和组件可维护性。
- 后端使用 FastAPI + Python。
- ORM 使用 SQLAlchemy。
- 本地数据库使用 SQLite。
- MVP 部署锁定为前端 Vercel、后端 Render。

## 方案比较

### 前端：Next.js vs 纯静态站 vs Vite React

- 纯静态站启动最快，但不适合后续 dashboard、路由、数据获取和部署扩展。
- Vite React 足够轻，但 SEO、metadata 和部署约定需要更多自建。
- Next.js 适合官网 + dashboard 的组合，支持路由、metadata、server/client component 边界和 Vercel 部署。

裁决：选择 Next.js。

### 后端：FastAPI vs Flask vs Django

- Flask 极简，但类型/schema、OpenAPI 和 async 支持需要额外组合。
- Django 成熟但偏重，本周 MVP 的模型和后台需求还不需要完整 Django 生态。
- FastAPI 自带 OpenAPI、Pydantic schema、依赖注入和测试友好性，适合快速定义 API contract。

裁决：选择 FastAPI。

### 数据库：SQLite vs Postgres

- Postgres 更接近生产，但本地启动和部署配置更重。
- SQLite 足够支撑一周 MVP，能降低本地开发和测试成本。
- 通过 SQLAlchemy repository 边界和枚举字段设计保留 Postgres 迁移空间。

裁决：MVP 使用 SQLite，模型设计保持 Postgres 兼容。

## 后果

- 前后端需要明确 API contract，避免 Next.js 与 FastAPI 字段漂移。
- 后端必须提供 mock LLM provider，保证测试不依赖网络和真实模型。
- 部署时要处理 CORS、环境变量和 SQLite 文件路径。

