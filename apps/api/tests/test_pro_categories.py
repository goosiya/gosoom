"""GET/PUT /api/v1/pros/me/categories 엔드포인트 테스트 (실 DB + 트랜잭션 롤백, Story 3.1).

검증 대상:
- AC2/AC3 성공: PUT 200 카테고리 설정, GET 200 조회.
- AC2 replace: 기존 목록 완전 교체.
- AC2 빈 배열: PUT 200 전체 삭제.
- AC4 존재하지 않는 UUID: 400 invalid_category_ids.
- AC4 비활성 카테고리: 400 invalid_category_ids.
- AC5 비인증: 401.
- AC5 비활성 고수: 401.
- AC5 CUSTOMER: 403.
- AC5 ADMIN: 403.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import (
    _auth,
    _make_admin,
    _make_category,
    _make_customer,
    _make_pro,
)

pytestmark = pytest.mark.asyncio


# ---- 성공 케이스 ----


async def test_set_categories_200(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """카테고리 2개 설정 → 200 + category_ids 반환"""
    cat1 = await _make_category(db_session, "청소_s1")
    cat2 = await _make_category(db_session, "요리_s1")
    pro = await _make_pro(db_session, "pro_set@test.com")

    r = await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": [str(cat1.id), str(cat2.id)]},
        headers=_auth(pro),
    )
    assert r.status_code == 200
    data = r.json()
    assert set(data["categoryIds"]) == {str(cat1.id), str(cat2.id)}


async def test_replace_categories_200(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """기존 설정 후 다른 목록으로 PUT → 완전 교체"""
    cat1 = await _make_category(db_session, "청소_r1")
    cat2 = await _make_category(db_session, "요리_r1")
    cat3 = await _make_category(db_session, "수리_r1")
    pro = await _make_pro(db_session, "pro_replace@test.com")

    # 첫 번째 PUT: cat1, cat2
    r1 = await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": [str(cat1.id), str(cat2.id)]},
        headers=_auth(pro),
    )
    assert r1.status_code == 200

    # 두 번째 PUT: cat3만 → 완전 교체
    r2 = await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": [str(cat3.id)]},
        headers=_auth(pro),
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["categoryIds"] == [str(cat3.id)]


async def test_set_empty_categories_200(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """빈 배열 → 200 + 빈 목록 반환"""
    cat = await _make_category(db_session, "청소_e1")
    pro = await _make_pro(db_session, "pro_empty@test.com")

    # 먼저 카테고리 설정
    await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": [str(cat.id)]},
        headers=_auth(pro),
    )

    # 빈 배열로 PUT
    r = await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": []},
        headers=_auth(pro),
    )
    assert r.status_code == 200
    assert r.json()["categoryIds"] == []


async def test_get_categories_200(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """PUT 후 GET → 동일 목록 반환"""
    cat1 = await _make_category(db_session, "청소_g1")
    cat2 = await _make_category(db_session, "요리_g1")
    pro = await _make_pro(db_session, "pro_get@test.com")

    await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": [str(cat1.id), str(cat2.id)]},
        headers=_auth(pro),
    )

    r = await client_db.get("/api/v1/pros/me/categories", headers=_auth(pro))
    assert r.status_code == 200
    data = r.json()
    assert set(data["categoryIds"]) == {str(cat1.id), str(cat2.id)}


# ---- 유효성 검증 케이스 ----


async def test_invalid_category_id_400(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """존재하지 않는 UUID → 400 + code == 'invalid_category_ids'"""
    pro = await _make_pro(db_session, "pro_invalid@test.com")
    fake_id = "00000000-0000-0000-0000-000000000001"

    r = await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": [fake_id]},
        headers=_auth(pro),
    )
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_category_ids"


async def test_inactive_category_400(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """is_active=False 카테고리 → 400 + code == 'invalid_category_ids'"""
    cat = await _make_category(db_session, "청소_inactive", is_active=False)
    pro = await _make_pro(db_session, "pro_inactive_cat@test.com")

    r = await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": [str(cat.id)]},
        headers=_auth(pro),
    )
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_category_ids"


# ---- 인증/권한 케이스 ----


async def test_no_token_401(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """토큰 없음 → 401"""
    r = await client_db.get("/api/v1/pros/me/categories")
    assert r.status_code == 401


async def test_inactive_pro_401(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """is_active=False 고수 → 401"""
    pro = await _make_pro(db_session, "pro_inactive@test.com")
    pro.is_active = False
    await db_session.flush()

    r = await client_db.get("/api/v1/pros/me/categories", headers=_auth(pro))
    assert r.status_code == 401


async def test_customer_403(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """CUSTOMER 역할 → 403"""
    customer = await _make_customer(db_session, "customer_pros@test.com")

    r = await client_db.get("/api/v1/pros/me/categories", headers=_auth(customer))
    assert r.status_code == 403


async def test_admin_403(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """ADMIN 역할 → 403"""
    admin = await _make_admin(db_session, "admin_pros@test.com")

    r = await client_db.get("/api/v1/pros/me/categories", headers=_auth(admin))
    assert r.status_code == 403


# ---- PUT 엔드포인트 인증/권한 케이스 ----


async def test_no_token_put_401(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """토큰 없음 PUT → 401"""
    r = await client_db.put("/api/v1/pros/me/categories", json={"categoryIds": []})
    assert r.status_code == 401


async def test_inactive_pro_put_401(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """비활성 고수 PUT → 401"""
    pro = await _make_pro(db_session, "pro_inactive_put@test.com")
    pro.is_active = False
    await db_session.flush()

    r = await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": []},
        headers=_auth(pro),
    )
    assert r.status_code == 401


async def test_customer_put_403(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """CUSTOMER 역할 PUT → 403"""
    customer = await _make_customer(db_session, "customer_pros_put@test.com")

    r = await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": []},
        headers=_auth(customer),
    )
    assert r.status_code == 403


async def test_admin_put_403(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """ADMIN 역할 PUT → 403"""
    admin = await _make_admin(db_session, "admin_pros_put@test.com")

    r = await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": []},
        headers=_auth(admin),
    )
    assert r.status_code == 403


# ---- AC4 deleted_at 케이스 ----


async def test_soft_deleted_category_400(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """deleted_at IS NOT NULL 소프트삭제 카테고리 → 400 + code == 'invalid_category_ids'"""
    from datetime import datetime, timezone

    cat = await _make_category(db_session, "청소_deleted")
    cat.deleted_at = datetime.now(timezone.utc)
    await db_session.flush()
    pro = await _make_pro(db_session, "pro_deleted_cat@test.com")

    r = await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": [str(cat.id)]},
        headers=_auth(pro),
    )
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_category_ids"
