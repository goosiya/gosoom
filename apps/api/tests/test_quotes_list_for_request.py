"""GET /api/v1/service-requests/{id}/quotes 엔드포인트 테스트 (실 DB + 트랜잭션 롤백, Story 4.1).

검증 대상:
- AC1 기본 성공: 200, pro.displayName 존재, 이메일 미포함, 필드 검증
- AC1 빈 목록: 200, items=[]
- AC1 모든 상태 포함: pending/accepted/rejected/closed 반환 확인
- AC2 소유권: 타 고객 → 403
- AC3 존재하지 않는 요청 → 404
- AC4 페이지네이션: nextCursor 반환, 두 번째 페이지 조회
- AC4 잘못된 cursor → 400
- AC5 비인증 → 401
- AC5 PRO → 403
- AC5 ADMIN → 403
- 추가: matched 요청도 조회 가능(소유권만 만족하면 상태 제한 없음)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import QuoteStatus
from app.models.service_request import ServiceRequestStatus

from tests.helpers import (
    _assign_pro_categories,
    _auth,
    _make_admin,
    _make_category,
    _make_customer,
    _make_pro,
    _make_quote,
    _make_service_request,
)

pytestmark = pytest.mark.asyncio


# ---- AC1: 기본 성공 ----


async def test_list_quotes_for_request_success_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """기본 성공: 200, pro.displayName 존재, 이메일 미포함, 필드 검증."""
    customer = await _make_customer(db_session, "lqr-ok-cust@example.com")
    pro = await _make_pro(db_session, "lqr-ok-pro@example.com")
    cat = await _make_category(db_session, "청소-lqr-ok")
    await _assign_pro_categories(db_session, pro, [cat])
    sr = await _make_service_request(db_session, customer, cat)
    quote = await _make_quote(db_session, pro, sr, price=50000, message="최선을 다하겠습니다.")

    resp = await client_db.get(
        f"/api/v1/service-requests/{sr.id}/quotes", headers=_auth(customer)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "items" in data
    assert "nextCursor" in data
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["id"] == str(quote.id)
    assert item["proId"] == str(pro.id)
    assert item["price"] == 50000
    assert item["message"] == "최선을 다하겠습니다."
    assert item["status"] == "pending"
    assert "createdAt" in item
    assert "updatedAt" in item

    # pro 필드 검증
    pro_info = item["pro"]
    assert pro_info["id"] == str(pro.id)
    assert pro_info["displayName"] == "고수유저"
    assert str(cat.id) in pro_info["categoryIds"]

    # 이메일 미포함 확인 (개인정보 최소 노출)
    assert "email" not in item
    assert "email" not in pro_info


# ---- AC1: 빈 목록 ----


async def test_list_quotes_for_request_empty_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """견적 없음: 200, items=[]."""
    customer = await _make_customer(db_session, "lqr-empty@example.com")
    cat = await _make_category(db_session, "청소-lqr-empty")
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.get(
        f"/api/v1/service-requests/{sr.id}/quotes", headers=_auth(customer)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["items"] == []
    assert data["nextCursor"] is None


# ---- AC1: 모든 상태 포함 ----


async def test_list_quotes_for_request_all_statuses(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """pending/accepted/rejected/closed 모든 상태 견적이 반환된다."""
    customer = await _make_customer(db_session, "lqr-allst-cust@example.com")
    pro1 = await _make_pro(db_session, "lqr-allst-pro1@example.com")
    pro2 = await _make_pro(db_session, "lqr-allst-pro2@example.com")
    pro3 = await _make_pro(db_session, "lqr-allst-pro3@example.com")
    pro4 = await _make_pro(db_session, "lqr-allst-pro4@example.com")
    cat = await _make_category(db_session, "청소-lqr-allst")
    sr = await _make_service_request(db_session, customer, cat)

    await _make_quote(db_session, pro1, sr, message="pending 견적", status=QuoteStatus.PENDING)
    await _make_quote(db_session, pro2, sr, message="accepted 견적", status=QuoteStatus.ACCEPTED)
    await _make_quote(db_session, pro3, sr, message="rejected 견적", status=QuoteStatus.REJECTED)
    await _make_quote(db_session, pro4, sr, message="closed 견적", status=QuoteStatus.CLOSED)

    resp = await client_db.get(
        f"/api/v1/service-requests/{sr.id}/quotes", headers=_auth(customer)
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 4

    statuses = {item["message"]: item["status"] for item in items}
    assert statuses["pending 견적"] == "pending"
    assert statuses["accepted 견적"] == "accepted"
    assert statuses["rejected 견적"] == "rejected"
    assert statuses["closed 견적"] == "closed"


# ---- AC2: 소유권 검사 ----


async def test_list_quotes_for_request_other_customer_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """타 고객의 요청 → 403 forbidden."""
    customer = await _make_customer(db_session, "lqr-own-cust@example.com")
    other_customer = await _make_customer(db_session, "lqr-other-cust@example.com")
    cat = await _make_category(db_session, "청소-lqr-own")
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.get(
        f"/api/v1/service-requests/{sr.id}/quotes", headers=_auth(other_customer)
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


# ---- AC3: 존재하지 않는 요청 ----


async def test_list_quotes_for_request_not_found_404(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """존재하지 않는 요청 id → 404 service_request_not_found."""
    customer = await _make_customer(db_session, "lqr-notfound@example.com")
    import uuid
    fake_id = uuid.uuid4()

    resp = await client_db.get(
        f"/api/v1/service-requests/{fake_id}/quotes", headers=_auth(customer)
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "service_request_not_found"


# ---- AC4: 페이지네이션 ----


async def test_list_quotes_for_request_pagination_next_cursor(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """limit=2, 3개 견적 → nextCursor non-null."""
    customer = await _make_customer(db_session, "lqr-page1-cust@example.com")
    pro1 = await _make_pro(db_session, "lqr-page1-pro1@example.com")
    pro2 = await _make_pro(db_session, "lqr-page1-pro2@example.com")
    pro3 = await _make_pro(db_session, "lqr-page1-pro3@example.com")
    cat = await _make_category(db_session, "청소-lqr-page1")
    sr = await _make_service_request(db_session, customer, cat)

    await _make_quote(db_session, pro1, sr, message="견적 1")
    await _make_quote(db_session, pro2, sr, message="견적 2")
    await _make_quote(db_session, pro3, sr, message="견적 3")

    resp = await client_db.get(
        f"/api/v1/service-requests/{sr.id}/quotes?limit=2", headers=_auth(customer)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["nextCursor"] is not None


async def test_list_quotes_for_request_pagination_second_page(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """nextCursor로 두 번째 페이지 → 나머지 견적 + nextCursor=null."""
    customer = await _make_customer(db_session, "lqr-page2-cust@example.com")
    pro1 = await _make_pro(db_session, "lqr-page2-pro1@example.com")
    pro2 = await _make_pro(db_session, "lqr-page2-pro2@example.com")
    pro3 = await _make_pro(db_session, "lqr-page2-pro3@example.com")
    cat = await _make_category(db_session, "청소-lqr-page2")
    sr = await _make_service_request(db_session, customer, cat)

    await _make_quote(db_session, pro1, sr, message="견적 A")
    await _make_quote(db_session, pro2, sr, message="견적 B")
    await _make_quote(db_session, pro3, sr, message="견적 C")

    # 첫 페이지
    resp1 = await client_db.get(
        f"/api/v1/service-requests/{sr.id}/quotes?limit=2", headers=_auth(customer)
    )
    assert resp1.status_code == 200
    cursor = resp1.json()["nextCursor"]
    assert cursor is not None

    # 두 번째 페이지
    resp2 = await client_db.get(
        f"/api/v1/service-requests/{sr.id}/quotes?limit=2&cursor={cursor}",
        headers=_auth(customer),
    )
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["nextCursor"] is None


async def test_list_quotes_for_request_invalid_cursor_400(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """잘못된 cursor → 400 invalid_cursor."""
    customer = await _make_customer(db_session, "lqr-badcur@example.com")
    cat = await _make_category(db_session, "청소-lqr-badcur")
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.get(
        f"/api/v1/service-requests/{sr.id}/quotes?cursor=!!!invalid!!!",
        headers=_auth(customer),
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "invalid_cursor"


# ---- AC5: 권한 제어 ----


async def test_list_quotes_for_request_no_token_401(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """비인증 → 401 not_authenticated."""
    customer = await _make_customer(db_session, "lqr-noauth-cust@example.com")
    cat = await _make_category(db_session, "청소-lqr-noauth")
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.get(f"/api/v1/service-requests/{sr.id}/quotes")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "not_authenticated"


async def test_list_quotes_for_request_pro_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """PRO 역할 → 403 forbidden."""
    customer = await _make_customer(db_session, "lqr-prorole-cust@example.com")
    pro = await _make_pro(db_session, "lqr-prorole-pro@example.com")
    cat = await _make_category(db_session, "청소-lqr-prorole")
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.get(
        f"/api/v1/service-requests/{sr.id}/quotes", headers=_auth(pro)
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


async def test_list_quotes_for_request_admin_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """ADMIN 역할 → 403 forbidden."""
    customer = await _make_customer(db_session, "lqr-adminrole-cust@example.com")
    admin = await _make_admin(db_session, "lqr-adminrole-admin@example.com")
    cat = await _make_category(db_session, "청소-lqr-adminrole")
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.get(
        f"/api/v1/service-requests/{sr.id}/quotes", headers=_auth(admin)
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


# ---- 추가: matched 요청도 조회 가능 ----


async def test_list_quotes_for_matched_request_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """matched 상태 요청도 소유권 만족 시 견적 조회 가능(상태 제한 없음)."""
    customer = await _make_customer(db_session, "lqr-matched-cust@example.com")
    pro = await _make_pro(db_session, "lqr-matched-pro@example.com")
    cat = await _make_category(db_session, "청소-lqr-matched")
    sr = await _make_service_request(
        db_session, customer, cat, status=ServiceRequestStatus.MATCHED
    )
    await _make_quote(db_session, pro, sr, message="매칭된 요청 견적")

    resp = await client_db.get(
        f"/api/v1/service-requests/{sr.id}/quotes", headers=_auth(customer)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["message"] == "매칭된 요청 견적"
