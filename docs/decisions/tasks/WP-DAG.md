# ChenForge AI MVP — WP DAG

## 依赖图

```
WP-1 (Backend Scaffold + DB)
 ├── WP-2 (Auth: email + JWT)
 │    └── WP-3 (Public Intake + Attachments)
 ├── WP-4 (Dashboard Shell + Lead Mgmt)
 │    └── WP-6 (Review Workbench: Artifact + Decision)
 ├── WP-5 (Agent Workflow: mock LLM + 5 agents)
 │    └── WP-6 (Review Workbench: Artifact + Decision)
 └── WP-7 (Delivery Center + Notification)
      └── WP-8 (Integration + Polish + Deploy)

WP-2 ∥ WP-4 ∥ WP-5  (can run in parallel after WP-1)
WP-3 ∥ WP-6              (can run in parallel after their respective deps)
```

## 并行 Track

| Track | WP | write_set 冲突？ |
|---|---|---|
| A: Auth + Intake | WP-2 → WP-3 | `backend/app/auth/`, `backend/app/api/auth.py`, `frontend/src/app/(auth)/`, `frontend/src/components/auth/` |
| B: Backend Core | WP-1 → WP-5 | `backend/app/models.py`, `backend/app/db.py`, `backend/app/services/llm.py`, `backend/app/services/agent_workflow.py` |
| C: Dashboard | WP-4 → WP-6 | `frontend/src/app/dashboard/`, `frontend/src/components/dashboard/`, `backend/app/api/leads.py`, `backend/app/api/artifacts.py`, `backend/app/api/decisions.py` |

Track A 和 Track C 共享接缝：Lead API contract（`backend/app/schemas.py`）。Track B 和 Track C 共享接缝：Artifact/Decision API contract。

## 接缝责任

| 接缝 | 生产端 | 消费端 | seam_owner |
|---|---|---|---|
| Lead API schema | WP-1 (models/schemas) | WP-3 (intake), WP-4 (dashboard) | WP-1 |
| Auth middleware | WP-2 | WP-3, WP-4 | WP-2 |
| Artifact/Decision API | WP-5 (agent produces) | WP-6 (dashboard displays) | WP-6 |
| DeliveryJob → email send | WP-6 (creates job) | WP-7 (sends) | WP-7 |
| Notification trigger | WP-1 (event model) | WP-7 (webhook) | WP-7 |
| Frontend API client | WP-3/WP-4/WP-6 | all frontend components | 联调 WP-8 |
