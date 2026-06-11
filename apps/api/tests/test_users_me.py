"""GET /api/v1/users/me 엔드포인트 테스트 (실 DB + 트랜잭션 롤백).

get_current_user(인증 경계)를 실 라우트로 검증한다(AC1/AC2/AC5):
- 성공(AC5): 유효 access → 200, UserRead(passwordHash 부재).
- 토큰 누락(AC1): 헤더 없음 → 401 not_authenticated.
- 위조/형식오류(AC1): garbage 토큰 → 401 invalid_token.
- 만료 access(AC1): 과거 exp 직접 인코딩 → 401 invalid_token.
- type 혼동(AC1): refresh 토큰 제출 → 401 invalid_token.
- 발급 후 비활성화(AC2, FR19/20): is_active=False 후 동일 토큰 → 401 invalid_token.

토큰은 login을 거치지 않고 create_access_token/create_refresh_token로 직접 생성한다
(get_current_user만 검증하므로 충분). 사용자는 savepoint 내부에서 /signup으로 시드.
"""

from datetime import datetime, timedelta, timezone

import jwt
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.repositories.users import UserRepository


async def _signup_and_fetch(
    client: AsyncClient, db: AsyncSession, email: str, role: str = "customer"
) -> User:
    """savepoint 내부에 사용자 시드 후 ORM User 객체 반환(토큰 생성용)."""
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "Secret-password1!",
            "displayName": "테스트유저",
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    user = await UserRepository(db).get_by_email(email)
    assert user is not None
    return user


# ---- AC5: 성공 ----


async def test_read_me_success_returns_safe_user(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """유효 access → 200, UserRead 안전 표현(passwordHash 키 부재, displayName 포함)(AC5)."""
    user = await _signup_and_fetch(client_db, db_session, "me-ok@example.com", role="pro")
    token = create_access_token(user.id, user.user_role)

    resp = await client_db.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "me-ok@example.com"
    assert body["displayName"] == "테스트유저"
    assert body["userRole"] == "pro"
    assert body["isActive"] is True
    # 안전 표현 — 비밀번호 해시는 절대 노출하지 않는다.
    assert "passwordHash" not in body
    assert "password_hash" not in body


async def test_read_me_returns_token_subject_not_other_user(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """두 사용자 존재 시 토큰 subject(A)를 반환 — 임의/첫 사용자가 아님(신원 바인딩, AC1/AC5).

    사용자가 1명뿐이면 read_me가 토큰을 무시하고 아무 사용자나 반환해도 통과한다.
    두 번째 사용자를 시드해 토큰의 user_id 바인딩이 실제로 작동함을 증명한다.
    """
    user_a = await _signup_and_fetch(
        client_db, db_session, "me-subject-a@example.com", role="customer"
    )
    await _signup_and_fetch(client_db, db_session, "me-subject-b@example.com", role="pro")
    token = create_access_token(user_a.id, user_a.user_role)

    resp = await client_db.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == "me-subject-a@example.com"


# ---- AC1: 인증 실패 경로 ----


async def test_read_me_empty_bearer_value_401_not_authenticated(
    client_db: AsyncClient,
) -> None:
    """값이 빈 Bearer 헤더(`Authorization: Bearer `) → 401 not_authenticated(AC1).

    oauth2_scheme는 값이 빈 Bearer에 None이 아니라 빈 문자열("")을 반환한다.
    이를 토큰 미전송으로 취급해 not_authenticated로 통일(invalid_token 아님)함을 증명.
    """
    resp = await client_db.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer "}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "not_authenticated"


async def test_read_me_missing_token_401(client_db: AsyncClient) -> None:
    """Authorization 헤더 없음 → 401 not_authenticated(토큰 누락 전용 code)(AC1)."""
    resp = await client_db.get("/api/v1/users/me")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "not_authenticated"


async def test_read_me_garbage_token_401(client_db: AsyncClient) -> None:
    """위조/형식오류 토큰 → 401 invalid_token(AC1)."""
    resp = await client_db.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer garbage.token"}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"


async def test_read_me_expired_access_401(client_db: AsyncClient) -> None:
    """만료 access → 401 invalid_token(AC1). 과거 exp로 직접 인코딩(대기 불가)."""
    expired = jwt.encode(
        {
            "user_id": "00000000-0000-0000-0000-000000000000",
            "user_role": "customer",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    resp = await client_db.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {expired}"}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"


async def test_read_me_malformed_payload_401(client_db: AsyncClient) -> None:
    """서명은 유효하나 user_id가 비-UUID인 토큰 → 401 invalid_token(payload 형식 가드, AC1).

    garbage 토큰(decode 단계 실패)과 달리, 이 케이스는 서명·만료를 통과하고
    deps.py 단계 ④(UUID 변환 try/except)에 도달해야 함을 검증한다 — 500 누수 방지의 핵심 경로.
    """
    bad_payload = jwt.encode(
        {
            "user_id": "not-a-uuid",
            "user_role": "customer",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    resp = await client_db.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {bad_payload}"}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"


async def test_read_me_nonstring_user_id_401(client_db: AsyncClient) -> None:
    """서명 유효하나 user_id가 비문자열(int) → 401 invalid_token(payload 형식 가드, AC1).

    UUID(12345)는 ValueError가 아니라 AttributeError('int' object has no attribute 'replace')를
    던진다 — deps.py 단계④ except에 AttributeError가 없으면 전역 핸들러로 새어 500이 된다.
    이 테스트가 그 회귀(500 누수)를 막는다. (test_read_me_malformed_payload_401은 문자열만 커버.)
    """
    bad_payload = jwt.encode(
        {
            "user_id": 12345,
            "user_role": "customer",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    resp = await client_db.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {bad_payload}"}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"


async def test_read_me_missing_user_id_claim_401(client_db: AsyncClient) -> None:
    """서명 유효하나 user_id 클레임 누락(KeyError) → 401 invalid_token(payload 형식 가드, AC1)."""
    bad_payload = jwt.encode(
        {
            "user_role": "customer",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    resp = await client_db.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {bad_payload}"}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"


async def test_read_me_refresh_token_rejected(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """type 혼동: refresh 토큰을 /me에 제출 → 401 invalid_token(type 가드, AC1)."""
    user = await _signup_and_fetch(client_db, db_session, "me-typeconfuse@example.com")
    refresh = create_refresh_token(user.id)

    resp = await client_db.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"


# ---- AC2: 발급 후 비활성화 즉시 차단(FR19/20) ----


async def test_read_me_after_deactivation_401(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """발급 후 비활성화 → 동일 토큰으로 /me → 401 invalid_token(AC2, FR19/20 증명).

    get_current_user가 매 요청 get_by_id로 현재 상태를 재조회하기에 비활성화가 즉시 반영된다 —
    매-요청 재조회 설계의 핵심 근거.
    """
    user = await _signup_and_fetch(client_db, db_session, "me-deact@example.com")
    token = create_access_token(user.id, user.user_role)
    # 유효 토큰 발급 후 계정 비활성화(savepoint 내)
    user.is_active = False
    await db_session.commit()

    resp = await client_db.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"


async def test_read_me_after_soft_delete_401(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """발급 후 소프트삭제(deleted_at) → 동일 토큰으로 /me → 401 invalid_token(AC2).

    get_by_id의 `deleted_at IS NULL` 공통 필터로 삭제 계정이 토큰으로 부활하지 못함을 증명
    (소프트삭제 일관성 — is_active와 별개 경로).
    """
    user = await _signup_and_fetch(client_db, db_session, "me-deleted@example.com")
    token = create_access_token(user.id, user.user_role)
    # 유효 토큰 발급 후 소프트삭제(savepoint 내)
    user.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()

    resp = await client_db.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"
