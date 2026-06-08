"""GET /api/v1/categories 엔드포인트 테스트 (실 DB + 트랜잭션 롤백, Story 1.6).

검증 대상:
- 인증 필요(AC3): 토큰 없음 → 401 not_authenticated.
- 성공 + envelope 형식(AC1): {items, nextCursor}, item camelCase, deletedAt 부재.
- 비활성·소프트삭제 제외(AC1): is_active=False·deleted_at 둘 다 제외.
- 모든 역할 허용(AC3): customer·pro·admin 전부 200(require_role 아님 — CurrentUser 증명).
- 페이지네이션 실동작(AC4): limit+cursor로 다중 페이지, 중복·누락 없음.
- 손상 cursor(AC4): 비-base64·base64-but-not-UUID → 400 invalid_cursor(500 아님).
- limit 경계: 0·101 → 422.

카테고리는 db_session으로 직접 insert. 토큰은 create_access_token(user.id, user.user_role) 직접 생성
(get_current_user가 id로 재조회하므로 사용자는 db_session에 직접 시드).
"""

from datetime import datetime, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import encode_cursor
from app.core.security import create_access_token, hash_password
from app.models.category import Category
from app.models.user import User, UserRole

pytestmark = pytest.mark.asyncio


# ---- 헬퍼 ----


async def _make_user(
    db: AsyncSession, email: str, role: UserRole = UserRole.CUSTOMER
) -> User:
    """db_session에 사용자 1명 시드 후 ORM 객체 반환(토큰 생성용)."""
    user = User(
        email=email,
        password_hash=hash_password("secret-password"),
        display_name="테스트유저",
        user_role=role,
        is_active=True,
        is_seed=(role is UserRole.ADMIN),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _make_category(
    db: AsyncSession,
    name: str,
    *,
    is_active: bool = True,
    deleted: bool = False,
) -> Category:
    """db_session에 카테고리 1개 시드. is_active/소프트삭제 제어 가능."""
    category = Category(name=name, is_active=is_active)
    if deleted:
        category.deleted_at = datetime.now(timezone.utc)
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.user_role)
    return {"Authorization": f"Bearer {token}"}


# ---- AC3: 인증 필요 ----


async def test_list_categories_missing_token_401(client_db: AsyncClient) -> None:
    """토큰 없음 → 401 not_authenticated(AC3)."""
    resp = await client_db.get("/api/v1/categories")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "not_authenticated"


# ---- AC1: 성공 + envelope 형식 ----


async def test_list_categories_success_envelope_format(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """활성 카테고리 → 200, {items, nextCursor} envelope, item camelCase, deletedAt 부재(AC1)."""
    user = await _make_user(db_session, "cat-ok@example.com")
    await _make_category(db_session, "청소")
    await _make_category(db_session, "이사")

    resp = await client_db.get("/api/v1/categories", headers=_auth(user))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # envelope 형식
    assert "items" in body and isinstance(body["items"], list)
    assert "nextCursor" in body
    # 단일 페이지 → nextCursor is None
    assert body["nextCursor"] is None
    assert len(body["items"]) == 2
    # item 안전 표현 + camelCase 경계
    item = body["items"][0]
    assert "name" in item
    assert "isActive" in item  # camelCase
    assert "createdAt" in item
    assert item["isActive"] is True
    # 내부 마커는 노출 금지
    assert "deletedAt" not in item
    assert "deleted_at" not in item
    assert "is_active" not in item


async def test_list_categories_excludes_inactive_and_soft_deleted(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """활성 1 + 비활성 1 + 소프트삭제 1 → 활성 1개만 반환(두 제외 조건 모두 증명, AC1)."""
    user = await _make_user(db_session, "cat-filter@example.com")
    await _make_category(db_session, "활성카테고리", is_active=True)
    await _make_category(db_session, "비활성카테고리", is_active=False)
    await _make_category(db_session, "삭제카테고리", is_active=True, deleted=True)

    resp = await client_db.get("/api/v1/categories", headers=_auth(user))
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    names = {i["name"] for i in items}
    assert names == {"활성카테고리"}


# ---- AC3: 모든 역할 허용(admin 배제 안 됨) ----


@pytest.mark.parametrize(
    "role", [UserRole.CUSTOMER, UserRole.PRO, UserRole.ADMIN]
)
async def test_list_categories_all_roles_allowed(
    client_db: AsyncClient, db_session: AsyncSession, role: UserRole
) -> None:
    """customer·pro·admin 전부 200 — require_role이 아니라 CurrentUser임을 증명(AC3 핵심 회귀)."""
    user = await _make_user(db_session, f"cat-{role.value}@example.com", role=role)
    await _make_category(db_session, f"카테고리-{role.value}")

    resp = await client_db.get("/api/v1/categories", headers=_auth(user))
    assert resp.status_code == 200, resp.text


# ---- AC4: 페이지네이션 실동작 ----


async def test_list_categories_pagination_works(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """활성 5개 + limit=2 → 3페이지(2/2/1), 합집합=전체, 중복 없음, 마지막 nextCursor=null(AC4)."""
    user = await _make_user(db_session, "cat-page@example.com")
    # uuid7은 시간정렬이라 생성 순서대로 id 증가 → keyset(id ASC) 검증에 적합.
    for i in range(5):
        await _make_category(db_session, f"페이지카테고리-{i}")
    headers = _auth(user)

    seen_ids: list[str] = []

    # 1페이지
    r1 = await client_db.get("/api/v1/categories?limit=2", headers=headers)
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert len(b1["items"]) == 2
    assert b1["nextCursor"] is not None
    seen_ids += [i["id"] for i in b1["items"]]

    # 2페이지
    r2 = await client_db.get(
        f"/api/v1/categories?limit=2&cursor={b1['nextCursor']}", headers=headers
    )
    assert r2.status_code == 200, r2.text
    b2 = r2.json()
    assert len(b2["items"]) == 2
    assert b2["nextCursor"] is not None
    seen_ids += [i["id"] for i in b2["items"]]

    # 3페이지(마지막)
    r3 = await client_db.get(
        f"/api/v1/categories?limit=2&cursor={b2['nextCursor']}", headers=headers
    )
    assert r3.status_code == 200, r3.text
    b3 = r3.json()
    assert len(b3["items"]) == 1
    assert b3["nextCursor"] is None  # 마지막 페이지
    seen_ids += [i["id"] for i in b3["items"]]

    # 합집합 = 전체 5, 중복 없음
    assert len(seen_ids) == 5
    assert len(set(seen_ids)) == 5


# ---- AC4: 손상 cursor → 400(500 아님) ----


async def test_list_categories_corrupted_cursor_not_base64_400(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """비-base64 cursor → 400 invalid_cursor(전역 500 누수 방지, AC4)."""
    user = await _make_user(db_session, "cat-badcursor1@example.com")
    resp = await client_db.get(
        "/api/v1/categories?cursor=not-base64!!!", headers=_auth(user)
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "invalid_cursor"


async def test_list_categories_corrupted_cursor_base64_not_uuid_400(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """base64는 유효하나 비-UUID인 cursor → 400 invalid_cursor(service UUID 가드, AC4)."""
    user = await _make_user(db_session, "cat-badcursor2@example.com")
    bad = encode_cursor("not-a-uuid")  # 유효 base64, 디코드하면 "not-a-uuid"
    resp = await client_db.get(
        f"/api/v1/categories?cursor={bad}", headers=_auth(user)
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "invalid_cursor"


async def test_list_categories_valid_cursor_unknown_id_empty(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """유효 base64+UUID지만 존재하지 않는 경계 id → 빈 페이지(에러 아님, keyset 정상 동작)."""
    user = await _make_user(db_session, "cat-emptycursor@example.com")
    await _make_category(db_session, "단일카테고리")
    # 매우 큰 UUID를 경계로 → id > after_id 충족 행 없음
    far = encode_cursor(str(UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")))
    resp = await client_db.get(
        f"/api/v1/categories?cursor={far}", headers=_auth(user)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["items"] == []
    assert body["nextCursor"] is None


# ---- limit 경계 ----


async def test_list_categories_limit_zero_422(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """limit=0 → 422(Query ge=1)."""
    user = await _make_user(db_session, "cat-limit0@example.com")
    resp = await client_db.get("/api/v1/categories?limit=0", headers=_auth(user))
    assert resp.status_code == 422, resp.text


async def test_list_categories_limit_too_large_422(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """limit=101 → 422(Query le=100, 과대 요청 차단)."""
    user = await _make_user(db_session, "cat-limit101@example.com")
    resp = await client_db.get("/api/v1/categories?limit=101", headers=_auth(user))
    assert resp.status_code == 422, resp.text
