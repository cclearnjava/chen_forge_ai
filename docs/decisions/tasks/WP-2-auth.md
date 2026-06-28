# WP-2: Auth — 邮箱验证码 + JWT

- **Goal**: 邮箱验证码登录/注册流程、JWT pair 签发与刷新、客户会话管理。
- **Write set**: `backend/app/auth/__init__.py`, `backend/app/auth/jwt.py`, `backend/app/auth/verification.py`, `backend/app/api/auth.py`, `frontend/src/app/(auth)/*.tsx`, `frontend/src/components/auth/*.tsx`
- **Depends on**: WP-1 (VerificationCode model, config)
- **Parallel with**: WP-4, WP-5
- **Seam owner**: WP-2 负责 auth middleware，消费方 WP-3/WP-4 通过 middleware 获取当前用户
- **Acceptance test**:
  - `POST /api/v1/auth/email/start` 发送验证码（mock email provider）
  - `POST /api/v1/auth/email/verify` 返回有效 JWT pair
  - `POST /api/v1/auth/refresh` 刷新 access token
  - 验证码过期后拒绝（10 分钟）
  - 60 秒内重复请求被拒绝
  - 同邮箱每天超过 5 次被拒绝
  - 前端登录页面可正常渲染和提交
