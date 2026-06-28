# WP-8: Integration + Polish + Deploy

- **Goal**: 前后端联调、golden journey 端到端验证、响应式检查、README 更新、部署准备。
- **Write set**: `README.md`, `frontend/src/lib/api-client.ts` (final), `backend/app/main.py` (CORS final), `backend/.env.example` (final), `frontend/.env.local.example`
- **Depends on**: WP-3, WP-6, WP-7
- **Parallel with**: 无（集成门）
- **Seam owner**: WP-8 负责所有跨 WP 接缝的最终验证
- **Acceptance test**:
  - Golden journey 完整走通：
    1. 客户邮箱登录 → 提交需求+附件 → Agent 生成 3 个 Artifact
    2. 负责人后台查看 → 编辑 customer_reply_draft → 批准 → 创建 DeliveryJob → 发送
    3. 后台看到 sent 状态和审计日志
  - 桌面端和移动端响应式正常
  - 所有表单校验和错误状态正常
  - 无 LLM key 暴露到前端
  - 本地启动命令（`cd backend && uvicorn` + `cd frontend && npm run dev`）在 README 中可照做
  - `.env.example` 包含所有必填环境变量的说明
