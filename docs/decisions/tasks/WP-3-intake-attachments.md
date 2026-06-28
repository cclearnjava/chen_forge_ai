# WP-3: Public Intake + Attachments

- **Goal**: 客户认证后提交业务需求、上传文档/截图、填写视频链接。替代原有公开表单。
- **Write set**: `backend/app/api/leads.py` (POST create), `backend/app/api/attachments.py`, `backend/app/services/storage.py`, `frontend/src/app/intake/*.tsx`, `frontend/src/components/intake/*.tsx`
- **Depends on**: WP-2 (auth middleware, JWT session)
- **Parallel with**: WP-6
- **Seam owner**: WP-3 负责 Lead 创建契约，WP-4 消费 Lead 列表/详情
- **Acceptance test**:
  - 认证用户 `POST /api/v1/leads` 创建 Lead 成功（201）
  - `owner_email` 不等于 JWT email 时拒绝（403）
  - honeypot 非空时静默拒绝
  - `POST /api/v1/leads/{id}/attachments` 上传 PNG/PDF/DOCX 成功
  - 不允许的文件类型被拒绝（422）
  - 超过 20MB 文件被拒绝
  - 前端 intake 页面能完整提交（含附件和视频链接）
  - 提交后显示"接下来会发生什么"
