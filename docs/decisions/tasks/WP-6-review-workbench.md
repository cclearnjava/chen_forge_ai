# WP-6: Review Workbench — Artifact + Decision UI

- **Goal**: 后台评审台：展示 Agent 生成物、支持编辑后批准、Decision 决策动作（approve/defer/rewrite）、版本历史。
- **Write set**: `backend/app/api/artifacts.py` (list/detail/approve/patch), `backend/app/api/decisions.py` (list/approve/defer/rewrite), `frontend/src/components/dashboard/artifact-viewer.tsx`, `frontend/src/components/dashboard/decision-queue.tsx`, `frontend/src/components/dashboard/review-workbench.tsx`
- **Depends on**: WP-4 (dashboard shell, api-client), WP-5 (Agent 生产 Artifact/Decision)
- **Parallel with**: WP-3
- **Seam owner**: WP-6 负责审批流程的完整闭环验证
- **Acceptance test**:
  - 线索详情页展示所有 Artifact（Markdown 渲染）
  - `PATCH /api/v1/artifacts/{id}` 保存编辑后的内容，version_history 追加旧版本
  - `POST /api/v1/artifacts/{id}/approve` 设置 approved_at，requires_approval = false
  - `POST /api/v1/decisions/{id}/approve` 批准决策
  - `POST /api/v1/decisions/{id}/defer` 暂缓决策
  - `POST /api/v1/decisions/{id}/request-rewrite` 要求重写
  - Decision 状态变更后 UI 实时更新
  - 编辑后批准的前端交互完整（编辑 → 预览 → 确认批准）
