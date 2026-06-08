"""회원가입 엔드포인트 테스트 (실 DB + 트랜잭션 롤백).

검증: 성공(201/안전표현), 중복(409), 역할/검증 실패(422), Argon2 해싱(NFR3).
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

pytestmark = pytest.mark.asyncio


async def test_signup_success_returns_safe_user(client_db: AsyncClient) -> None:
    """customer 가입 → 201, displayName 존재·userRole==customer, password/passwordHash 부재(AC1)."""
    resp = await client_db.post(
        "/api/v1/auth/signup",
        json={
            "email": "alice@example.com",
            "password": "secret-password",
            "displayName": "앨리스",
            "role": "customer",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["displayName"] == "앨리스"
    assert body["userRole"] == "customer"
    assert body["email"] == "alice@example.com"
    assert body["isActive"] is True
    # 안전한 표현: 비밀번호 관련 키 절대 미노출
    assert "password" not in body
    assert "passwordHash" not in body
    assert "password_hash" not in body


async def test_signup_duplicate_email_returns_409(client_db: AsyncClient) -> None:
    """동일 이메일 2회 → 2번째 409 + envelope {code: email_already_exists}(AC2)."""
    payload = {
        "email": "dup@example.com",
        "password": "secret-password",
        "displayName": "중복",
        "role": "pro",
    }
    first = await client_db.post("/api/v1/auth/signup", json=payload)
    assert first.status_code == 201, first.text

    second = await client_db.post("/api/v1/auth/signup", json=payload)
    assert second.status_code == 409, second.text
    body = second.json()
    assert body["code"] == "email_already_exists"
    assert "message" in body


async def test_signup_email_is_normalized_case_insensitive(
    client_db: AsyncClient,
) -> None:
    """대소문자만 다른 이메일은 동일 사용자 — 소문자 정규화 후 저장·중복(409)."""
    first = await client_db.post(
        "/api/v1/auth/signup",
        json={
            "email": "Mixed@Example.com",
            "password": "secret-password",
            "displayName": "혼합",
            "role": "customer",
        },
    )
    assert first.status_code == 201, first.text
    # 저장·응답 이메일은 소문자로 정규화됨
    assert first.json()["email"] == "mixed@example.com"

    # 같은 주소를 소문자로 재가입 시도 → 정규화 일치로 중복 차단(409)
    second = await client_db.post(
        "/api/v1/auth/signup",
        json={
            "email": "mixed@example.com",
            "password": "secret-password",
            "displayName": "혼합2",
            "role": "customer",
        },
    )
    assert second.status_code == 409, second.text
    assert second.json()["code"] == "email_already_exists"


@pytest.mark.parametrize("bad_role", ["admin", "superuser", "", "CUSTOMER"])
async def test_signup_disallowed_role_returns_422(
    client_db: AsyncClient, bad_role: str
) -> None:
    """admin/허용 외 역할 → 422(AC3). 관리자는 자가 가입 불가."""
    resp = await client_db.post(
        "/api/v1/auth/signup",
        json={
            "email": f"role-{bad_role or 'empty'}@example.com",
            "password": "secret-password",
            "displayName": "역할",
            "role": bad_role,
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "validation_error"


@pytest.mark.parametrize(
    "payload",
    [
        # displayName 누락
        {"email": "v1@example.com", "password": "secret-password", "role": "customer"},
        # password 너무 짧음(<8)
        {
            "email": "v2@example.com",
            "password": "short",
            "displayName": "짧은비번",
            "role": "customer",
        },
        # email 형식 오류
        {
            "email": "not-an-email",
            "password": "secret-password",
            "displayName": "이메일오류",
            "role": "customer",
        },
        # displayName 빈 문자열(min_length=1)
        {
            "email": "v4@example.com",
            "password": "secret-password",
            "displayName": "",
            "role": "customer",
        },
        # displayName 공백만(strip 후 빈 문자열 — min_length=1을 통과하나 validator가 차단)
        {
            "email": "v5@example.com",
            "password": "secret-password",
            "displayName": " ",
            "role": "customer",
        },
        # password 최대 길이 초과(>128 — Argon2 DoS 방지 상한)
        {
            "email": "v6@example.com",
            "password": "x" * 129,
            "displayName": "긴비번",
            "role": "customer",
        },
    ],
)
async def test_signup_validation_errors_return_422(
    client_db: AsyncClient, payload: dict
) -> None:
    """서버 검증 실패 → 422 + envelope(서버 검증 신뢰, NFR3)."""
    resp = await client_db.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "validation_error"


async def test_password_is_argon2_hashed_in_db(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """생성 후 DB의 password_hash가 평문이 아니고 Argon2 포맷($argon2)인지(NFR3)."""
    resp = await client_db.post(
        "/api/v1/auth/signup",
        json={
            "email": "hash@example.com",
            "password": "secret-password",
            "displayName": "해시",
            "role": "customer",
        },
    )
    assert resp.status_code == 201, resp.text

    row = await db_session.execute(select(User).where(User.email == "hash@example.com"))
    user = row.scalar_one()
    assert user.password_hash != "secret-password"
    assert user.password_hash.startswith("$argon2")
    # DB enum이 소문자 값으로 저장됐는지(첫 슬라이스 규약 확정)
    assert user.user_role.value == "customer"
