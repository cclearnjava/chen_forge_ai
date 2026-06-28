import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import VerificationCode


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def can_send_code(db: Session, email: str) -> tuple[bool, str | None]:
    """Check if a code can be sent to this email. Returns (allowed, error_message)."""
    now = datetime.utcnow()

    recent = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.email == email,
            VerificationCode.created_at > now - timedelta(seconds=60),
        )
        .first()
    )
    if recent:
        return False, "60秒内已发送过验证码，请稍后再试"

    today_count = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.email == email,
            VerificationCode.created_at > now - timedelta(days=1),
        )
        .count()
    )
    if today_count >= 5:
        return False, "今日发送次数已达上限（5次），请明天再试"

    return True, None


def create_verification_code(db: Session, email: str) -> str:
    """Create and store a verification code. Returns the plaintext code (for sending)."""
    code = generate_code()
    code_hash = _hash_code(code)
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    vc = VerificationCode(
        email=email,
        code_hash=code_hash,
        expires_at=expires_at,
    )
    db.add(vc)
    db.commit()
    return code


def verify_code(db: Session, email: str, code: str) -> tuple[bool, str | None]:
    """Verify a submitted code. Returns (valid, error_message)."""
    code_hash = _hash_code(code)
    now = datetime.utcnow()

    vc = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.email == email,
            VerificationCode.code_hash == code_hash,
            VerificationCode.used == False,
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )

    if not vc:
        return False, "验证码错误或已使用"

    if vc.expires_at < now:
        return False, "验证码已过期（10分钟有效）"

    if vc.attempts >= 3:
        vc.used = True
        db.commit()
        return False, "验证码尝试次数过多，请重新获取"

    vc.attempts += 1
    db.commit()
    return True, None


def mark_code_used(db: Session, email: str, code: str):
    code_hash = _hash_code(code)
    vc = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.email == email,
            VerificationCode.code_hash == code_hash,
        )
        .first()
    )
    if vc:
        vc.used = True
        db.commit()
