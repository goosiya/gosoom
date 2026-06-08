"""로그인/세션갱신 엔드포인트 테스트 (실 DB + 트랜잭션 롤백).

검증:
- 로그인 성공(AC1): 200 + access/refresh, access payload 구조·role 일치.
- 로그인 실패 3종(AC2): 비번불일치·미존재·비활성 → 동일 일반 401(anti-enumeration, NFR3).
- refresh(AC3): 성공(새 access만)·type혼동·만료·위조·발급후비활성화 → 401.

사용자 시드는 savepoint 내부에서 `client_db`로 `/signup` 후 진행(둘 다 롤백 격리).
"""

from datetime import datetime, timedelta, timezone

import jwt
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_password
from app.repositories.users import UserRepository

# asyncio_mode=auto(pyproject)라 async 테스트는 마커 없이 자동 인식.
# 동기 단위 테스트(verify_password)도 같은 파일에 있으므로 모듈 레벨 asyncio 마크를 두지 않는다.


async def _signup(client: AsyncClient, email: str, password: str, role: str = "customer") -> dict:
    """가입 헬퍼 — 201 확인 후 응답 body 반환."""
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": password,
            "displayName": "테스트유저",
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---- AC1: 로그인 성공 ----


async def test_login_success_returns_tokens(client_db: AsyncClient) -> None:
    """올바른 자격증명 → 200, accessToken/refreshToken/tokenType=="bearer"(AC1)."""
    await _signup(client_db, "login-ok@example.com", "secret-password", role="pro")

    resp = await client_db.post(
        "/api/v1/auth/login",
        json={"email": "login-ok@example.com", "password": "secret-password"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tokenType"] == "bearer"
    assert isinstance(body["accessToken"], str) and body["accessToken"]
    assert isinstance(body["refreshToken"], str) and body["refreshToken"]


async def test_login_access_token_payload(client_db: AsyncClient) -> None:
    """access JWT payload는 {user_id, user_role, type:"access", exp}, role은 가입 역할과 일치(AC1)."""
    await _signup(client_db, "payload@example.com", "secret-password", role="pro")

    resp = await client_db.post(
        "/api/v1/auth/login",
        json={"email": "payload@example.com", "password": "secret-password"},
    )
    assert resp.status_code == 200, resp.text
    access = resp.json()["accessToken"]

    payload = jwt.decode(access, settings.jwt_secret, algorithms=["HS256"])
    assert payload["type"] == "access"
    assert payload["user_role"] == "pro"
    assert "user_id" in payload
    assert "exp" in payload


async def test_login_email_case_insensitive(client_db: AsyncClient) -> None:
    """대소문자만 다른 이메일로도 로그인 성공 — 정규화 일관(AC1)."""
    await _signup(client_db, "Case@Example.com", "secret-password")

    resp = await client_db.post(
        "/api/v1/auth/login",
        json={"email": "case@example.com", "password": "secret-password"},
    )
    assert resp.status_code == 200, resp.text


# ---- AC2: 로그인 실패 3종 (anti-enumeration) ----


async def test_login_wrong_password_401(client_db: AsyncClient) -> None:
    """비밀번호 불일치 → 401 invalid_credentials, 토큰 미발급(AC2)."""
    await _signup(client_db, "wrongpw@example.com", "secret-password")

    resp = await client_db.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "WRONG-password"},
    )
    assert resp.status_code == 401, resp.text
    body = resp.json()
    assert body["code"] == "invalid_credentials"
    assert "accessToken" not in body
    assert "refreshToken" not in body


async def test_login_unknown_email_401(client_db: AsyncClient) -> None:
    """미존재 이메일 → 401 invalid_credentials(AC2)."""
    resp = await client_db.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "secret-password"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_credentials"


async def test_login_inactive_account_401(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """비활성 계정(is_active=False) → 401, 토큰 미발급(AC2, FR19/20)."""
    await _signup(client_db, "inactive@example.com", "secret-password")
    # 가입 직후 비활성화
    user = await UserRepository(db_session).get_by_email("inactive@example.com")
    assert user is not None
    user.is_active = False
    await db_session.commit()

    resp = await client_db.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "secret-password"},
    )
    assert resp.status_code == 401, resp.text
    body = resp.json()
    assert body["code"] == "invalid_credentials"
    assert "accessToken" not in body


async def test_login_failures_are_indistinguishable(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """anti-enumeration(NFR3): 비번불일치·미존재·비활성 세 응답이 code·message 모두 동일."""
    # 비활성 계정 준비
    await _signup(client_db, "enum-inactive@example.com", "secret-password")
    user = await UserRepository(db_session).get_by_email("enum-inactive@example.com")
    assert user is not None
    user.is_active = False
    await db_session.commit()
    # 비번불일치용 정상 계정
    await _signup(client_db, "enum-active@example.com", "secret-password")

    wrong_pw = await client_db.post(
        "/api/v1/auth/login",
        json={"email": "enum-active@example.com", "password": "WRONG"},
    )
    unknown = await client_db.post(
        "/api/v1/auth/login",
        json={"email": "enum-nobody@example.com", "password": "secret-password"},
    )
    inactive = await client_db.post(
        "/api/v1/auth/login",
        json={"email": "enum-inactive@example.com", "password": "secret-password"},
    )

    assert wrong_pw.status_code == unknown.status_code == inactive.status_code == 401
    # 세 응답의 envelope(code+message)가 완전히 동일해야 상태 추론이 불가능하다.
    assert wrong_pw.json() == unknown.json() == inactive.json()


# ---- AC3: refresh ----


async def _login_tokens(client: AsyncClient, email: str, password: str, role: str = "customer") -> dict:
    """가입+로그인 헬퍼 — 토큰 dict({accessToken, refreshToken, ...}) 반환."""
    await _signup(client, email, password, role=role)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_refresh_success_returns_new_access_only(client_db: AsyncClient) -> None:
    """유효 refresh → 200, 새 accessToken(+tokenType), refreshToken 키 부재(회전 없음, AC3)."""
    tokens = await _login_tokens(client_db, "refresh-ok@example.com", "secret-password", role="pro")

    resp = await client_db.post(
        "/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tokenType"] == "bearer"
    assert isinstance(body["accessToken"], str) and body["accessToken"]
    # 회전 없음 — refresh 토큰은 재발급하지 않는다
    assert "refreshToken" not in body
    # 새 access도 현재 role(pro)을 반영
    payload = jwt.decode(body["accessToken"], settings.jwt_secret, algorithms=["HS256"])
    assert payload["type"] == "access"
    assert payload["user_role"] == "pro"


async def test_refresh_with_access_token_rejected(client_db: AsyncClient) -> None:
    """type 혼동: accessToken을 /refresh에 제출 → 401 invalid_token(AC3)."""
    tokens = await _login_tokens(client_db, "type-confuse@example.com", "secret-password")

    resp = await client_db.post(
        "/api/v1/auth/refresh", json={"refreshToken": tokens["accessToken"]}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"


async def test_refresh_expired_token_rejected(client_db: AsyncClient) -> None:
    """만료 refresh → 401 invalid_token(AC3). 과거 exp로 직접 인코딩."""
    expired = jwt.encode(
        {
            "user_id": "00000000-0000-0000-0000-000000000000",
            "type": "refresh",
            "exp": datetime.now(timezone.utc) - timedelta(days=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    resp = await client_db.post("/api/v1/auth/refresh", json={"refreshToken": expired})
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"


async def test_refresh_garbage_token_rejected(client_db: AsyncClient) -> None:
    """위조/형식오류 토큰 → 401 invalid_token(AC3)."""
    resp = await client_db.post(
        "/api/v1/auth/refresh", json={"refreshToken": "garbage.token"}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"


async def test_refresh_after_deactivation_rejected(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """발급 후 비활성화(FR19/20 증명): 동일 refresh로 /refresh → 401(AC3).

    refresh가 단순 재서명이 아니라 사용자를 재조회하기에 비활성화가 반영된다 — refresh 설계의 핵심.
    """
    tokens = await _login_tokens(client_db, "deact@example.com", "secret-password")
    # 발급 후 계정 비활성화
    user = await UserRepository(db_session).get_by_email("deact@example.com")
    assert user is not None
    user.is_active = False
    await db_session.commit()

    resp = await client_db.post(
        "/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"


# ---- verify_password 단위 ----


def test_verify_password_unit() -> None:
    """verify_password: 올바른 평문→True, 틀린 평문→False, 손상된 해시→False(예외 정규화)."""
    from app.core.security import hash_password

    h = hash_password("secret-password")
    assert verify_password("secret-password", h) is True
    assert verify_password("wrong", h) is False
    # 손상된/비-Argon2 해시는 예외가 아니라 False로 정규화
    assert verify_password("x", "not-a-valid-hash") is False
