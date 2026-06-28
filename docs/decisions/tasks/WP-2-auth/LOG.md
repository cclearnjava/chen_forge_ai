# WP-2 LOG: Auth — 邮箱验证码 + JWT

## Done

- JWT utility: `backend/app/auth/jwt.py` (access + refresh tokens, HS256)
- Verification code service: `backend/app/auth/verification.py` (generate, hash, verify, rate limit)
- Auth API: `backend/app/api/auth.py` (email/start, email/verify, refresh)
- Auth middleware: `backend/app/auth/middleware.py` (customer JWT, admin bearer token)
- Tests: 9 tests covering start, rate limit (60s + daily), verify success/wrong/expired, refresh, access-token-as-refresh rejected

## Deviations

- Using naive UTC datetimes for SQLite compatibility (will fix in post-MVP cleanup)
- Dev mode: `_dev_code` returned in email/start response for testing without real email

## Commands

```bash
cd backend && .venv/bin/python -m pytest tests/ -v   # 19 passed
```
