from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.jwt import get_email_from_token

security = HTTPBearer(auto_error=False)


def get_current_email(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    email = get_email_from_token(credentials.credentials)
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return email


def get_admin_email(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Require admin authentication. MVP: bearer token = ADMIN_TOKEN from env."""
    from app.config import settings

    if credentials is None:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    if credentials.credentials != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return "admin"
