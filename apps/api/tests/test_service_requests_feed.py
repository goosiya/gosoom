"""GET /api/v1/service-requests/feed, GET /api/v1/service-requests/feed/{id} 테스트 (Story 3.2).

검증 대상:
- AC1 피드 목록: 카테고리 일치 요청만 반환, open+matched 포함, completed/cancelled 제외
- AC2 matched 포함: 비활성 표시이지만 목록에서 제외 안 됨
- AC3 피드 상세: 카테고리 일치 요청 반환, 불일치 403, 미존재 404
- AC4 권한: 비인증 401, CUSTOMER 403, ADMIN 403, 카테고리 미설정 PRO → 빈 목록
"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_request import ServiceRequest, ServiceRequestStatus

from tests.helpers import (
    _assign_pro_categories,
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
    status: ServiceRequestStatus = ServiceRequestStatus.OPEN,
    description: str = "테스트 요청",
    desired_schedule: str | None = None,
    budget: int | None = None,
) -> ServiceRequest:
    import uuid_extensions

    req = ServiceRequest(
        id=uuid_extensions.uuid7(),
        customer_id=customer.id,  # type: ignore[attr-defined]
        category_id=category.id,  # type: ignore[attr-defined]
        region="서울 강남구",
        description=description,
        status=status,
        desired_schedule=desired_schedule,
        budget=budget,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    return req


# ---- 피드 목록: AC4 카테고리 없는 PRO ----


async def test_feed_empty_when_no_categories_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """카테고리 미설정 PRO → 빈 목록 반환, 오류 없음 (AC4)."""
    pro = await _make_pro(db_session, "feed-nocat@example.com")

    r = await client_db.get("/api/v1/service-requests/feed", headers=_auth(pro))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"] == []
    assert body["nextCursor"] is None


# ---- 피드 목록: AC1 정상 조회 ----


async def test_feed_returns_matching_open_requests_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """카테고리 일치 open 요청이 목록에 반환된다 (AC1)."""
    pro = await _make_pro(db_session, "feed-open@example.com")
    customer = await _make_customer(db_session, "feed-open-c@example.com")
    cat = await _make_category(db_session, "피드-open")
    req = await _make_service_request(db_session, customer, cat)
    await _assign_pro_categories(db_session, pro, [cat])

    r = await client_db.get("/api/v1/service-requests/feed", headers=_auth(pro))
    assert r.status_code == 200, r.text
    ids = [item["id"] for item in r.json()["items"]]
    assert str(req.id) in ids


# ---- 피드 목록: AC2 matched 포함 ----


async def test_feed_includes_matched_requests_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """matched 상태 요청은 피드 목록에서 제외되지 않는다 (AC2)."""
    pro = await _make_pro(db_session, "feed-matched@example.com")
    customer = await _make_customer(db_session, "feed-matched-c@example.com")
    cat = await _make_category(db_session, "피드-matched")
    req = await _make_service_request(
        db_session, customer, cat, status=ServiceRequestStatus.MATCHED
    )
    await _assign_pro_categories(db_session, pro, [cat])

    r = await client_db.get("/api/v1/service-requests/feed", headers=_auth(pro))
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    ids = [item["id"] for item in items]
    assert str(req.id) in ids
    matched_item = next(i for i in items if i["id"] == str(req.id))
    assert matched_item["status"] == "matched"


# ---- 피드 목록: completed/cancelled 제외 ----


async def test_feed_excludes_completed_cancelled(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """completed·cancelled 요청은 피드에서 제외된다 (AC1)."""
    pro = await _make_pro(db_session, "feed-excl@example.com")
    customer = await _make_customer(db_session, "feed-excl-c@example.com")
    cat = await _make_category(db_session, "피드-excl")
    req_completed = await _make_service_request(
        db_session, customer, cat, status=ServiceRequestStatus.COMPLETED
    )
    req_cancelled = await _make_service_request(
        db_session, customer, cat, status=ServiceRequestStatus.CANCELLED
    )
    await _assign_pro_categories(db_session, pro, [cat])

    r = await client_db.get("/api/v1/service-requests/feed", headers=_auth(pro))
    assert r.status_code == 200, r.text
    ids = [item["id"] for item in r.json()["items"]]
    assert str(req_completed.id) not in ids
    assert str(req_cancelled.id) not in ids


# ---- 피드 목록: 카테고리 불일치 제외 ----


async def test_feed_excludes_non_matching_categories(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """PRO 카테고리와 일치하지 않는 요청은 피드에서 제외된다 (AC1)."""
    pro = await _make_pro(db_session, "feed-catmiss@example.com")
    customer = await _make_customer(db_session, "feed-catmiss-c@example.com")
    cat_pro = await _make_category(db_session, "피드-pro카테고리")
    cat_other = await _make_category(db_session, "피드-다른카테고리")
    req_mine = await _make_service_request(db_session, customer, cat_pro)
    req_other = await _make_service_request(db_session, customer, cat_other)
    await _assign_pro_categories(db_session, pro, [cat_pro])

    r = await client_db.get("/api/v1/service-requests/feed", headers=_auth(pro))
    assert r.status_code == 200, r.text
    ids = [item["id"] for item in r.json()["items"]]
    assert str(req_mine.id) in ids
    assert str(req_other.id) not in ids


# ---- 피드 목록: 소프트삭제 제외 ----


async def test_feed_excludes_soft_deleted_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """소프트 삭제된 요청은 피드에서 제외된다 (AC1)."""
    pro = await _make_pro(db_session, "feed-softdel@example.com")
    customer = await _make_customer(db_session, "feed-softdel-c@example.com")
    cat = await _make_category(db_session, "피드-softdel")
    req_active = await _make_service_request(db_session, customer, cat, description="활성")
    req_deleted = await _make_service_request(db_session, customer, cat, description="삭제됨")
    req_deleted.deleted_at = datetime.now(timezone.utc)
    await db_session.flush()
    await _assign_pro_categories(db_session, pro, [cat])

    r = await client_db.get("/api/v1/service-requests/feed", headers=_auth(pro))
    assert r.status_code == 200, r.text
    ids = [item["id"] for item in r.json()["items"]]
    assert str(req_active.id) in ids
    assert str(req_deleted.id) not in ids


# ---- 피드 목록: cursor 페이지네이션 ----


async def test_feed_cursor_pagination_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """limit=1 → nextCursor 반환, 두 번째 호출로 나머지 조회 (AC1)."""
    pro = await _make_pro(db_session, "feed-page@example.com")
    customer = await _make_customer(db_session, "feed-page-c@example.com")
    cat = await _make_category(db_session, "피드-page")
    req1 = await _make_service_request(db_session, customer, cat, description="오래된")
    req2 = await _make_service_request(db_session, customer, cat, description="최신")
    await _assign_pro_categories(db_session, pro, [cat])

    # 첫 번째 페이지 (limit=1) → 최신(req2)
    r = await client_db.get(
        "/api/v1/service-requests/feed", params={"limit": 1}, headers=_auth(pro)
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(req2.id)
    assert body["nextCursor"] is not None

    # 두 번째 페이지 → req1
    r2 = await client_db.get(
        "/api/v1/service-requests/feed",
        params={"limit": 1, "cursor": body["nextCursor"]},
        headers=_auth(pro),
    )
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert len(body2["items"]) == 1
    assert body2["items"][0]["id"] == str(req1.id)
    assert body2["nextCursor"] is None


# ---- 피드 목록: 권한 (AC4) ----


async def test_feed_no_token_401(client_db: AsyncClient) -> None:
    """토큰 없음 → 401 not_authenticated (AC4)."""
    r = await client_db.get("/api/v1/service-requests/feed")
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "not_authenticated"


async def test_feed_customer_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """CUSTOMER 역할 → 403 forbidden (AC4)."""
    customer = await _make_customer(db_session, "feed-cust-403@example.com")
    r = await client_db.get("/api/v1/service-requests/feed", headers=_auth(customer))
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "forbidden"


async def test_feed_admin_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """ADMIN 역할 → 403 forbidden (AC4)."""
    admin = await _make_admin(db_session, "feed-admin-403@example.com")
    r = await client_db.get("/api/v1/service-requests/feed", headers=_auth(admin))
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "forbidden"


# ---- 피드 상세: 성공 (AC3) ----


async def test_feed_detail_success_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """카테고리 일치 요청 상세 조회 → 200, 모든 필드 반환 (AC3)."""
    pro = await _make_pro(db_session, "feedd-ok@example.com")
    customer = await _make_customer(db_session, "feedd-ok-c@example.com")
    cat = await _make_category(db_session, "피드상세-ok")
    req = await _make_service_request(
        db_session, customer, cat,
        description="상세 테스트",
        desired_schedule="2026-07-01",
        budget=50000,
    )
    await _assign_pro_categories(db_session, pro, [cat])

    r = await client_db.get(f"/api/v1/service-requests/feed/{req.id}", headers=_auth(pro))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == str(req.id)
    assert body["categoryId"] == str(cat.id)
    assert body["region"] == "서울 강남구"
    assert body["description"] == "상세 테스트"
    assert body["status"] == "open"
    assert body["desiredSchedule"] == "2026-07-01"
    assert body["budget"] == 50000
    assert "createdAt" in body
    assert "updatedAt" in body


async def test_feed_detail_matched_request_visible_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """matched 상태 요청도 피드 상세에서 조회 가능하다 (AC3)."""
    pro = await _make_pro(db_session, "feedd-matched@example.com")
    customer = await _make_customer(db_session, "feedd-matched-c@example.com")
    cat = await _make_category(db_session, "피드상세-matched")
    req = await _make_service_request(
        db_session, customer, cat, status=ServiceRequestStatus.MATCHED
    )
    await _assign_pro_categories(db_session, pro, [cat])

    r = await client_db.get(f"/api/v1/service-requests/feed/{req.id}", headers=_auth(pro))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "matched"


# ---- 피드 상세: 거부 케이스 (AC3, AC4) ----


async def test_feed_detail_category_mismatch_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """카테고리 불일치 요청 접근 → 403 forbidden (AC3)."""
    pro = await _make_pro(db_session, "feedd-mismatch@example.com")
    customer = await _make_customer(db_session, "feedd-mismatch-c@example.com")
    cat_pro = await _make_category(db_session, "피드상세-pro")
    cat_other = await _make_category(db_session, "피드상세-other")
    req = await _make_service_request(db_session, customer, cat_other)
    await _assign_pro_categories(db_session, pro, [cat_pro])

    r = await client_db.get(f"/api/v1/service-requests/feed/{req.id}", headers=_auth(pro))
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "forbidden"


async def test_feed_detail_not_found_404(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """존재하지 않는 id → 404 service_request_not_found (AC3)."""
    pro = await _make_pro(db_session, "feedd-404@example.com")
    cat = await _make_category(db_session, "피드상세-404")
    await _assign_pro_categories(db_session, pro, [cat])
    nonexistent_id = "00000000-0000-0000-0000-000000000099"

    r = await client_db.get(
        f"/api/v1/service-requests/feed/{nonexistent_id}", headers=_auth(pro)
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "service_request_not_found"


async def test_feed_detail_no_token_401(client_db: AsyncClient) -> None:
    """토큰 없음 → 401 not_authenticated (AC4)."""
    r = await client_db.get(
        "/api/v1/service-requests/feed/00000000-0000-0000-0000-000000000001"
    )
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "not_authenticated"


async def test_feed_detail_customer_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """CUSTOMER 역할 → 403 forbidden (AC4)."""
    customer = await _make_customer(db_session, "feedd-cust-403@example.com")
    r = await client_db.get(
        "/api/v1/service-requests/feed/00000000-0000-0000-0000-000000000001",
        headers=_auth(customer),
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "forbidden"


async def test_feed_detail_admin_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """ADMIN 역할 → 403 forbidden (AC4)."""
    admin = await _make_admin(db_session, "feedd-admin-403@example.com")
    r = await client_db.get(
        "/api/v1/service-requests/feed/00000000-0000-0000-0000-000000000001",
        headers=_auth(admin),
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "forbidden"


async def test_feed_invalid_cursor_400(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """유효한 base64지만 UUID가 아닌 cursor → 400 invalid_cursor."""
    import base64

    pro = await _make_pro(db_session, "feed-badcursor@example.com")
    cat = await _make_category(db_session, "피드-badcursor")
    await _assign_pro_categories(db_session, pro, [cat])
    bad_cursor = base64.urlsafe_b64encode(b"not-a-uuid").decode()

    r = await client_db.get(
        "/api/v1/service-requests/feed",
        params={"cursor": bad_cursor},
        headers=_auth(pro),
    )
    assert r.status_code == 400, r.text
    assert r.json()["code"] == "invalid_cursor"
