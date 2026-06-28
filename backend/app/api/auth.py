from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas import (
    EmailStartRequest, EmailVerifyRequest,
    TokenOut, RefreshRequest,
)
from app.auth.jwt import (
    create_access_token, create_refresh_token,
    decode_token, get_email_from_token,
)
from app.auth.verification import (
    can_send_code, create_verification_code,
    verify_code, mark_code_used,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/email/start", status_code=202)
def email_start(req: EmailStartRequest, db: Session = Depends(get_db)):
    allowed, error = can_send_code(db, req.email)
    if not allowed:
        raise HTTPException(status_code=429, detail=error)

    code = create_verification_code(db, req.email)
    # In production: send email via Resend here
    # For MVP with mock: log the code for testing
    return {
        "message": "验证码已发送",
        "expires_in_seconds": 600,
        # Only include code in dev/mock mode
        "_dev_code": code,
    }


@router.post("/email/verify", response_model=TokenOut)
def email_verify(req: EmailVerifyRequest, db: Session = Depends(get_db)):
    valid, error = verify_code(db, req.email, req.code)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    mark_code_used(db, req.email, req.code)
    access_token = create_access_token(req.email)
    refresh_token = create_refresh_token(req.email)
    return TokenOut(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenOut)
def refresh(req: RefreshRequest):
    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    return TokenOut(
        access_token=create_access_token(email),
        refresh_token=create_refresh_token(email),
    )
