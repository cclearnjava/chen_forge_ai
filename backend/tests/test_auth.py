from app.db import SessionLocal
from app.models import VerificationCode
import hashlib
from datetime import datetime, timedelta, timezone


def test_email_start(client):
    response = client.post("/api/v1/auth/email/start", json={"email": "test@example.com"})
    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "验证码已发送"
    assert data["expires_in_seconds"] == 600
    assert "_dev_code" in data


def test_email_start_rate_limit_60s(client):
    client.post("/api/v1/auth/email/start", json={"email": "ratelimit@example.com"})
    response = client.post("/api/v1/auth/email/start", json={"email": "ratelimit@example.com"})
    assert response.status_code == 429
    assert "60秒" in response.json()["detail"]


def test_email_start_daily_limit(client):
    db = SessionLocal()
    email = "dailylimit@example.com"
    now = datetime.utcnow()
    for i in range(5):
        vc = VerificationCode(
            email=email,
            code_hash=f"hash_{i}",
            expires_at=now + timedelta(minutes=10),
            created_at=now - timedelta(hours=23),
        )
        db.add(vc)
    db.commit()

    response = client.post("/api/v1/auth/email/start", json={"email": email})
    assert response.status_code == 429
    assert "5次" in response.json()["detail"]


def test_email_verify_success(client):
    res = client.post("/api/v1/auth/email/start", json={"email": "verify@example.com"})
    code = res.json()["_dev_code"]

    response = client.post("/api/v1/auth/email/verify", json={
        "email": "verify@example.com",
        "code": code,
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_email_verify_wrong_code(client):
    client.post("/api/v1/auth/email/start", json={"email": "wrong@example.com"})
    response = client.post("/api/v1/auth/email/verify", json={
        "email": "wrong@example.com",
        "code": "000000",
    })
    assert response.status_code == 400


def test_email_verify_expired_code():
    from app.db import SessionLocal
    db = SessionLocal()
    email = "expired@example.com"
    code = "123456"
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    vc = VerificationCode(
        email=email,
        code_hash=code_hash,
        expires_at=datetime.utcnow() - timedelta(minutes=1),
    )
    db.add(vc)
    db.commit()

    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    response = client.post("/api/v1/auth/email/verify", json={
        "email": email,
        "code": code,
    })
    assert response.status_code == 400
    assert "过期" in response.json()["detail"]


def test_refresh_token(client):
    res = client.post("/api/v1/auth/email/start", json={"email": "refresh@example.com"})
    code = res.json()["_dev_code"]
    verify_res = client.post("/api/v1/auth/email/verify", json={
        "email": "refresh@example.com",
        "code": code,
    })
    refresh_token = verify_res.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_with_access_token(client):
    res = client.post("/api/v1/auth/email/start", json={"email": "badrefresh@example.com"})
    code = res.json()["_dev_code"]
    verify_res = client.post("/api/v1/auth/email/verify", json={
        "email": "badrefresh@example.com",
        "code": code,
    })
    access_token = verify_res.json()["access_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code in (400, 401)


def test_admin_endpoint_requires_auth(client):
    response = client.get("/api/v1/admin/leads")
    assert response.status_code == 401
