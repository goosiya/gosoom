"""GET /api/v1/quotes 엔드포인트 테스트 (실 DB + 트랜잭션 롤백, Story 3.4).

검증 대상:
- AC1 성공: 200, 본인 견적만, serviceRequest 포함, 필드 검증
- AC1 빈 목록: 200, items=[]
- AC2 페이지네이션: limit=1 + nextCursor non-null, 두 번째 페이지 조회
- AC2 nextCursor=null (마지막 페이지)
- AC2 잘못된 cursor: 400 invalid_cursor
- AC3 타 PRO 견적 미포함 확인
- AC4 비인증: 401 not_authenticated
- AC4 CUSTOMER: 403 forbidden
- AC4 ADMIN: 403 forbidden
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import QuoteStatus

from tests.helpers import (
    _auth,
    _make_admin,
    _make_category,
    _make_customer,
    _make_pro,
    _make_quote,
    _make_service_request,
)

pytestmark = pytest.mark.asyncio


# ---- AC1: 기본 목록 성공 ----


async def test_list_my_quotes_success_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """본인 견적 반환, serviceRequest 포함, 필드 검증."""
    pro = await _make_pro(db_session, "myq-ok@example.com")
    customer = await _make_customer(db_session, "myq-ok-cust@example.com")
    cat = await _make_category(db_session, "청소-목록성공")
    sr = await _make_service_request(db_session, customer, cat, region="부산", description="청소 요청")
    quote = await _make_quote(db_session, pro, sr, price=50000, message="최선을 다하겠습니다.")

    resp = await client_db.get("/api/v1/quotes", headers=_auth(pro))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "items" in data
    assert "nextCursor" in data
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["id"] == str(quote.id)
    assert item["serviceRequestId"] == str(sr.id)
    assert item["price"] == 50000
    assert item["message"] == "최선을 다하겠습니다."
    assert item["status"] == "pending"
    assert "createdAt" in item
    assert "updatedAt" in item

    # serviceRequest 포함 검증
    assert item["serviceRequest"] is not None
    sr_summary = item["serviceRequest"]
    assert sr_summary["id"] == str(sr.id)
    assert sr_summary["categoryId"] == str(cat.id)
    assert sr_summary["region"] == "부산"
    assert sr_summary["description"] == "청소 요청"
    assert sr_summary["status"] == "open"


# ---- AC1: 빈 목록 ----


async def test_list_my_quotes_empty_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """견적 없음: 200, items=[]."""
    pro = await _make_pro(db_session, "myq-empty@example.com")

    resp = await client_db.get("/api/v1/quotes", headers=_auth(pro))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["items"] == []
    assert data["nextCursor"] is None


# ---- AC2: 페이지네이션 ----


async def test_list_my_quotes_pagination_next_cursor(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """limit=1, 2개 견적 → nextCursor non-null."""
    pro = await _make_pro(db_session, "myq-page1@example.com")
    customer = await _make_customer(db_session, "myq-page1-cust@example.com")
    cat = await _make_category(db_session, "청소-페이지1")
    sr1 = await _make_service_request(db_session, customer, cat)
    sr2 = await _make_service_request(db_session, customer, cat)
    await _make_quote(db_session, pro, sr1, message="첫 번째 견적")
    await _make_quote(db_session, pro, sr2, message="두 번째 견적")

    resp = await client_db.get("/api/v1/quotes?limit=1", headers=_auth(pro))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["nextCursor"] is not None


async def test_list_my_quotes_pagination_second_page(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """nextCursor로 두 번째 페이지 조회 → 나머지 항목 + nextCursor=null."""
    pro = await _make_pro(db_session, "myq-page2@example.com")
    customer = await _make_customer(db_session, "myq-page2-cust@example.com")
    cat = await _make_category(db_session, "청소-페이지2")
    sr1 = await _make_service_request(db_session, customer, cat)
    sr2 = await _make_service_request(db_session, customer, cat)
    await _make_quote(db_session, pro, sr1, message="견적 A")
    await _make_quote(db_session, pro, sr2, message="견적 B")

    # 첫 페이지
    resp1 = await client_db.get("/api/v1/quotes?limit=1", headers=_auth(pro))
    assert resp1.status_code == 200
    cursor = resp1.json()["nextCursor"]
    assert cursor is not None

    # 두 번째 페이지
    resp2 = await client_db.get(f"/api/v1/quotes?limit=1&cursor={cursor}", headers=_auth(pro))
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["nextCursor"] is None


async def test_list_my_quotes_invalid_cursor_400(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """잘못된 cursor → 400 invalid_cursor."""
    pro = await _make_pro(db_session, "myq-badcur@example.com")

    resp = await client_db.get("/api/v1/quotes?cursor=!!!invalid!!!", headers=_auth(pro))
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "invalid_cursor"


# ---- AC3: 소유권 검사 ----


async def test_list_my_quotes_no_other_pro_quotes(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """타 PRO 견적은 목록에 포함되지 않는다."""
    pro = await _make_pro(db_session, "myq-own@example.com")
    other_pro = await _make_pro(db_session, "myq-other@example.com")
    customer = await _make_customer(db_session, "myq-own-cust@example.com")
    cat = await _make_category(db_session, "청소-소유권")
    sr = await _make_service_request(db_session, customer, cat)
    # 본인 견적
    my_quote = await _make_quote(db_session, pro, sr, message="내 견적")
    # 타 PRO 견적은 동일 요청에 둘 다 추가하면 unique 제약 위반 — 별도 요청 생성
    sr2 = await _make_service_request(db_session, customer, cat)
    await _make_quote(db_session, other_pro, sr2, message="타 PRO 견적")

    resp = await client_db.get("/api/v1/quotes", headers=_auth(pro))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    ids = [item["id"] for item in data["items"]]
    assert str(my_quote.id) in ids
    assert len(ids) == 1  # 타 PRO 견적 미포함


# ---- AC4: 권한 제어 ----


async def test_list_my_quotes_no_token_401(client_db: AsyncClient) -> None:
    """비인증 → 401 not_authenticated."""
    resp = await client_db.get("/api/v1/quotes")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "not_authenticated"


async def test_list_my_quotes_customer_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """CUSTOMER 역할 → 403 forbidden."""
    customer = await _make_customer(db_session, "myq-cust-role@example.com")

    resp = await client_db.get("/api/v1/quotes", headers=_auth(customer))
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


async def test_list_my_quotes_admin_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """ADMIN 역할 → 403 forbidden."""
    admin = await _make_admin(db_session, "myq-admin@example.com")

    resp = await client_db.get("/api/v1/quotes", headers=_auth(admin))
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


# ---- AC5: 상태 변경 반영 ----


async def test_list_my_quotes_status_reflected(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """accepted/rejected/closed 상태의 견적이 목록에 정확히 반영된다 (AC5)."""
    pro = await _make_pro(db_session, "myq-status@example.com")
    customer = await _make_customer(db_session, "myq-status-cust@example.com")
    cat = await _make_category(db_session, "청소-상태반영")
    sr1 = await _make_service_request(db_session, customer, cat)
    sr2 = await _make_service_request(db_session, customer, cat)
    sr3 = await _make_service_request(db_session, customer, cat)

    await _make_quote(db_session, pro, sr1, status=QuoteStatus.ACCEPTED, message="수락됨")
    await _make_quote(db_session, pro, sr2, status=QuoteStatus.REJECTED, message="거절됨")
    await _make_quote(db_session, pro, sr3, status=QuoteStatus.CLOSED, message="마감됨")

    resp = await client_db.get("/api/v1/quotes", headers=_auth(pro))
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 3

    statuses = {item["message"]: item["status"] for item in items}
    assert statuses["수락됨"] == "accepted"
    assert statuses["거절됨"] == "rejected"
    assert statuses["마감됨"] == "closed"
