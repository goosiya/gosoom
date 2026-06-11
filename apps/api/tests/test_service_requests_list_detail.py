"""GET /api/v1/service-requests, GET /api/v1/service-requests/{id} 테스트 (Story 2.2).

검증 대상:
- AC1 목록: 본인 요청만 반환, 소프트삭제 제외, 다른 고객 요청 미포함
- AC1 페이지네이션: cursor keyset(id DESC), nextCursor 반환, 두 번째 페이지 조회
- AC1 정렬: 최신순(id DESC) — 나중에 생성된 요청이 먼저
- AC2 상세: 모든 필드 반환, 타인 403, 미존재 404
- AC3 권한: 미인증 401, 비활성 401, PRO 403, ADMIN 403
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_request import ServiceRequest, ServiceRequestStatus

from tests.helpers import (
    _auth,
    _make_admin,
    _make_category,
    _make_customer,
    _make_pro,
)

pytestmark = pytest.mark.asyncio


# ---- 파일 고유 헬퍼: desired_schedule/budget 파라미터 포함 ----


async def _make_service_request(
    db: AsyncSession,
    customer: "object",
    category: "object",
    description: str = "테스트 요청",
    desired_schedule: str | None = None,
    budget: int | None = None,
) -> ServiceRequest:
    """서비스 요청 생성 헬퍼 (desired_schedule/budget 포함 — 이 파일 전용)."""
    import uuid_extensions

    req = ServiceRequest(
        id=uuid_extensions.uuid7(),
        customer_id=customer.id,  # type: ignore[attr-defined]
        category_id=category.id,  # type: ignore[attr-defined]
        region="서울 강남구",
        description=description,
        status=ServiceRequestStatus.OPEN,
        desired_schedule=desired_schedule,
        budget=budget,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    return req


# ---- 목록 엔드포인트: 성공 케이스 ----


async def test_list_mine_success_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """정상 CUSTOMER → 200, items에 본인 요청만 포함."""
    customer = await _make_customer(db_session, "list-ok@example.com")
    cat = await _make_category(db_session, "청소-list-ok")
    req = await _make_service_request(db_session, customer, cat, "목록 테스트")

    r = await client_db.get("/api/v1/service-requests/", headers=_auth(customer))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    ids = [item["id"] for item in body["items"]]
    assert str(req.id) in ids


async def test_list_mine_excludes_other_customers(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """다른 고객의 요청은 목록에 포함되지 않는다."""
    customer1 = await _make_customer(db_session, "list-c1@example.com")
    customer2 = await _make_customer(db_session, "list-c2@example.com")
    cat = await _make_category(db_session, "청소-exclude")
    req_c2 = await _make_service_request(db_session, customer2, cat, "타인 요청")

    r = await client_db.get("/api/v1/service-requests/", headers=_auth(customer1))
    assert r.status_code == 200, r.text
    ids = [item["id"] for item in r.json()["items"]]
    assert str(req_c2.id) not in ids


async def test_list_mine_empty_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """요청이 없을 때 빈 items 반환."""
    customer = await _make_customer(db_session, "list-empty@example.com")

    r = await client_db.get("/api/v1/service-requests/", headers=_auth(customer))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"] == []
    assert body["nextCursor"] is None


async def test_list_mine_cursor_pagination(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """cursor 페이지네이션: limit=1 → nextCursor 반환, 두 번째 호출로 나머지 조회."""
    customer = await _make_customer(db_session, "list-page@example.com")
    cat = await _make_category(db_session, "청소-page")
    req1 = await _make_service_request(db_session, customer, cat, "첫 번째")
    req2 = await _make_service_request(db_session, customer, cat, "두 번째")  # 더 나중 생성 = 더 높은 id

    # 첫 번째 페이지 (limit=1) → 최신인 req2가 먼저
    r = await client_db.get(
        "/api/v1/service-requests/", params={"limit": 1}, headers=_auth(customer)
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(req2.id)
    assert body["nextCursor"] is not None

    # 두 번째 페이지 → req1
    r2 = await client_db.get(
        "/api/v1/service-requests/",
        params={"limit": 1, "cursor": body["nextCursor"]},
        headers=_auth(customer),
    )
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert len(body2["items"]) == 1
    assert body2["items"][0]["id"] == str(req1.id)
    assert body2["nextCursor"] is None


async def test_list_mine_excludes_soft_deleted(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """소프트 삭제(deleted_at IS NOT NULL) 요청은 목록에서 제외된다 — AC1."""
    from datetime import datetime, timezone

    customer = await _make_customer(db_session, "list-softdel@example.com")
    cat = await _make_category(db_session, "청소-softdel")
    req_active = await _make_service_request(db_session, customer, cat, "활성 요청")
    req_deleted = await _make_service_request(db_session, customer, cat, "삭제된 요청")
    req_deleted.deleted_at = datetime.now(timezone.utc)
    await db_session.flush()

    r = await client_db.get("/api/v1/service-requests/", headers=_auth(customer))
    assert r.status_code == 200, r.text
    ids = [item["id"] for item in r.json()["items"]]
    assert str(req_active.id) in ids
    assert str(req_deleted.id) not in ids


async def test_list_mine_newest_first(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """최신순(id DESC) 정렬 검증 — 나중에 생성된 요청이 먼저."""
    customer = await _make_customer(db_session, "list-sort@example.com")
    cat = await _make_category(db_session, "청소-sort")
    req1 = await _make_service_request(db_session, customer, cat, "오래된 요청")
    req2 = await _make_service_request(db_session, customer, cat, "최신 요청")

    r = await client_db.get("/api/v1/service-requests/", headers=_auth(customer))
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) >= 2
    # 최신(req2)이 먼저, 오래된(req1)이 나중
    ids = [item["id"] for item in items]
    assert ids.index(str(req2.id)) < ids.index(str(req1.id))


# ---- 목록 엔드포인트: 거부 케이스 ----


async def test_list_mine_no_token_401(client_db: AsyncClient) -> None:
    """토큰 없음 → 401 not_authenticated."""
    r = await client_db.get("/api/v1/service-requests/")
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "not_authenticated"


async def test_list_mine_inactive_customer_401(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """비활성 고객 → 401 invalid_token."""
    customer = await _make_customer(db_session, "list-inactive@example.com")
    customer.is_active = False
    await db_session.flush()

    r = await client_db.get("/api/v1/service-requests/", headers=_auth(customer))
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "invalid_token"


async def test_list_mine_pro_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """PRO 역할 → 403 forbidden."""
    pro = await _make_pro(db_session, "list-pro@example.com")
    r = await client_db.get("/api/v1/service-requests/", headers=_auth(pro))
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "forbidden"


async def test_list_mine_admin_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """ADMIN 역할 → 403 forbidden (고객 전용 기능)."""
    admin = await _make_admin(db_session, "list-admin@example.com")
    r = await client_db.get("/api/v1/service-requests/", headers=_auth(admin))
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "forbidden"


# ---- 상세 엔드포인트: 성공 케이스 ----


async def test_get_detail_success_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """본인 요청 상세 조회 → 200, 모든 필드 반환 (AC2)."""
    customer = await _make_customer(db_session, "detail-ok@example.com")
    cat = await _make_category(db_session, "청소-detail")
    req = await _make_service_request(
        db_session,
        customer,
        cat,
        "상세 테스트",
        desired_schedule="2026-07-01",
        budget=50000,
    )

    r = await client_db.get(f"/api/v1/service-requests/{req.id}", headers=_auth(customer))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == str(req.id)
    assert body["customerId"] == str(customer.id)
    assert body["categoryId"] == str(cat.id)
    assert body["region"] == "서울 강남구"
    assert body["description"] == "상세 테스트"
    assert body["status"] == "open"
    assert body["desiredSchedule"] == "2026-07-01"
    assert body["budget"] == 50000
    assert "createdAt" in body
    assert "updatedAt" in body


# ---- 상세 엔드포인트: 거부 케이스 ----


async def test_get_detail_other_customer_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """타인 요청 접근 시 403 forbidden."""
    owner = await _make_customer(db_session, "detail-owner@example.com")
    other = await _make_customer(db_session, "detail-other@example.com")
    cat = await _make_category(db_session, "청소-403")
    req = await _make_service_request(db_session, owner, cat, "소유자 요청")

    r = await client_db.get(f"/api/v1/service-requests/{req.id}", headers=_auth(other))
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "forbidden"


async def test_get_detail_not_found_404(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """존재하지 않는 id → 404 service_request_not_found."""
    customer = await _make_customer(db_session, "detail-404@example.com")
    nonexistent_id = "00000000-0000-0000-0000-000000000099"

    r = await client_db.get(
        f"/api/v1/service-requests/{nonexistent_id}", headers=_auth(customer)
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "service_request_not_found"


async def test_get_detail_no_token_401(client_db: AsyncClient) -> None:
    """토큰 없음 → 401 not_authenticated."""
    r = await client_db.get("/api/v1/service-requests/00000000-0000-0000-0000-000000000001")
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "not_authenticated"


async def test_get_detail_pro_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """PRO 역할 → 403 forbidden."""
    pro = await _make_pro(db_session, "detail-pro@example.com")
    r = await client_db.get(
        "/api/v1/service-requests/00000000-0000-0000-0000-000000000001",
        headers=_auth(pro),
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "forbidden"


async def test_get_detail_admin_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """ADMIN 역할 → 403 forbidden (고객 전용 기능)."""
    admin = await _make_admin(db_session, "detail-admin@example.com")
    r = await client_db.get(
        "/api/v1/service-requests/00000000-0000-0000-0000-000000000001",
        headers=_auth(admin),
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "forbidden"
