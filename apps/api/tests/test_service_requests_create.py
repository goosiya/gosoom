"""POST /api/v1/service-requests 엔드포인트 테스트 (실 DB + 트랜잭션 롤백, Story 2.1).

검증 대상:
- AC1 성공: 201, status="open", customerId=토큰 사용자 ID.
- AC1 선택 필드 생략: desiredSchedule/budget nullable.
- AC2 필수 필드 누락: categoryId/region/description 각각 422.
- AC2 존재하지 않는 카테고리: 404 category_not_found.
- AC2 비활성 카테고리: 404 category_not_found.
- AC3 미인증: 401 not_authenticated.
- AC3 비활성 고객: 401 invalid_token.
- AC3 PRO 역할: 403 forbidden.
- AC3 ADMIN 역할: 403 forbidden.
"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category

from tests.helpers import (
    _auth,
    _make_admin,
    _make_customer,
    _make_pro,
)

pytestmark = pytest.mark.asyncio


# ---- 파일 고유 헬퍼: deleted 파라미터 포함 ----


async def _make_category(
    db: AsyncSession,
    name: str,
    *,
    is_active: bool = True,
    deleted: bool = False,
) -> Category:
    category = Category(name=name, is_active=is_active)
    if deleted:
        category.deleted_at = datetime.now(timezone.utc)
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


# ---- AC1: 성공 케이스 ----


async def test_create_service_request_success_201(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """정상 CUSTOMER + 활성 카테고리 → 201, status=open, customerId=토큰 사용자 ID."""
    user = await _make_customer(db_session, "sr-ok@example.com")
    category = await _make_category(db_session, "청소-성공")

    body = {
        "categoryId": str(category.id),
        "region": "서울",
        "description": "집 청소 부탁드립니다",
        "desiredSchedule": "이번 주 중",
        "budget": 50000,
    }
    resp = await client_db.post(
        "/api/v1/service-requests/", headers=_auth(user), json=body
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "open"
    assert data["customerId"] == str(user.id)
    assert data["categoryId"] == str(category.id)
    assert data["region"] == "서울"
    assert data["description"] == "집 청소 부탁드립니다"
    assert data["desiredSchedule"] == "이번 주 중"
    assert data["budget"] == 50000
    assert "id" in data


async def test_create_service_request_optional_fields_omitted(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """선택 필드(desiredSchedule/budget) 생략 시 201 성공."""
    user = await _make_customer(db_session, "sr-optional@example.com")
    category = await _make_category(db_session, "이사-선택필드")

    body = {
        "categoryId": str(category.id),
        "region": "부산",
        "description": "이사 도움",
    }
    resp = await client_db.post(
        "/api/v1/service-requests/", headers=_auth(user), json=body
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["desiredSchedule"] is None
    assert data["budget"] is None


# ---- AC3: 인증/역할 거부 ----


async def test_create_service_request_no_token_401(client_db: AsyncClient) -> None:
    """토큰 없음 → 401 not_authenticated."""
    resp = await client_db.post(
        "/api/v1/service-requests/",
        json={"categoryId": "00000000-0000-0000-0000-000000000001", "region": "서울", "description": "설명"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "not_authenticated"


async def test_create_service_request_inactive_user_401(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """비활성 고객 → 401 invalid_token (get_current_user is_active 검사)."""
    user = await _make_customer(db_session, "sr-inactive@example.com")
    user.is_active = False
    await db_session.flush()

    resp = await client_db.post(
        "/api/v1/service-requests/",
        headers=_auth(user),
        json={"categoryId": "00000000-0000-0000-0000-000000000001", "region": "서울", "description": "설명"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "invalid_token"


async def test_create_service_request_pro_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """PRO 역할 → 403 forbidden."""
    user = await _make_pro(db_session, "sr-pro@example.com")
    resp = await client_db.post(
        "/api/v1/service-requests/",
        headers=_auth(user),
        json={"categoryId": "00000000-0000-0000-0000-000000000001", "region": "서울", "description": "설명"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


async def test_create_service_request_admin_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """ADMIN 역할 → 403 forbidden (고객 전용 기능)."""
    user = await _make_admin(db_session, "sr-admin@example.com")
    resp = await client_db.post(
        "/api/v1/service-requests/",
        headers=_auth(user),
        json={"categoryId": "00000000-0000-0000-0000-000000000001", "region": "서울", "description": "설명"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


# ---- AC2: 유효성 검사 ----


async def test_create_service_request_missing_category_id_422(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """categoryId 누락 → 422."""
    user = await _make_customer(db_session, "sr-no-cat@example.com")
    resp = await client_db.post(
        "/api/v1/service-requests/",
        headers=_auth(user),
        json={"region": "서울", "description": "설명"},
    )
    assert resp.status_code == 422, resp.text


async def test_create_service_request_missing_region_422(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """region 누락 → 422."""
    user = await _make_customer(db_session, "sr-no-region@example.com")
    resp = await client_db.post(
        "/api/v1/service-requests/",
        headers=_auth(user),
        json={"categoryId": "00000000-0000-0000-0000-000000000001", "description": "설명"},
    )
    assert resp.status_code == 422, resp.text


async def test_create_service_request_missing_description_422(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """description 누락 → 422."""
    user = await _make_customer(db_session, "sr-no-desc@example.com")
    resp = await client_db.post(
        "/api/v1/service-requests/",
        headers=_auth(user),
        json={"categoryId": "00000000-0000-0000-0000-000000000001", "region": "서울"},
    )
    assert resp.status_code == 422, resp.text


async def test_create_service_request_nonexistent_category_404(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """존재하지 않는 categoryId → 404 category_not_found."""
    user = await _make_customer(db_session, "sr-no-cat-id@example.com")
    resp = await client_db.post(
        "/api/v1/service-requests/",
        headers=_auth(user),
        json={
            "categoryId": "00000000-0000-0000-0000-000000000099",
            "region": "서울",
            "description": "설명",
        },
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "category_not_found"


async def test_create_service_request_inactive_category_404(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """비활성 카테고리 ID → 404 category_not_found (비활성도 not found 처리)."""
    user = await _make_customer(db_session, "sr-inactive-cat@example.com")
    category = await _make_category(db_session, "비활성카테고리-SR", is_active=False)

    resp = await client_db.post(
        "/api/v1/service-requests/",
        headers=_auth(user),
        json={
            "categoryId": str(category.id),
            "region": "서울",
            "description": "설명",
        },
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "category_not_found"
