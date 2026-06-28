# WP-4: Dashboard Shell + Lead Management

- **Goal**: 私有后台外壳（导航、状态概览）、线索收件箱（列表、筛选、搜索）、线索详情页。
- **Write set**: `backend/app/api/leads.py` (list/detail/patch), `frontend/src/app/dashboard/layout.tsx`, `frontend/src/app/dashboard/page.tsx`, `frontend/src/app/dashboard/leads/[id]/page.tsx`, `frontend/src/components/dashboard/lead-inbox.tsx`, `frontend/src/components/dashboard/lead-detail.tsx`, `frontend/src/components/dashboard/dashboard-shell.tsx`, `frontend/src/lib/api-client.ts`
- **Depends on**: WP-1 (models, schemas)
- **Parallel with**: WP-2, WP-5
- **Seam owner**: WP-4 负责前端 API client 的基础封装，WP-3/WP-6 复用
- **Acceptance test**:
  - 未认证访问 `/dashboard` 被重定向
  - 已认证管理员访问 `/dashboard` 看到概览（新线索数、待决策数、草稿数）
  - 线索列表按状态筛选正常工作
  - 搜索按公司名/问题搜索正常工作
  - 线索详情页显示 Lead 信息、附件列表、关联 Artifact/Decision/DeliveryJob
  - `PATCH /api/v1/leads/{id}` 更新线索状态成功
  - 空状态（无线索时）正确展示
