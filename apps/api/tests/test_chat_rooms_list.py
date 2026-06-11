"""채팅방 목록 조회 엔드포인트 테스트 (실 DB + 트랜잭션 롤백, Story 4.5).

검증 대상:
- AC1 CUSTOMER 목록 조회: 200, items 반환, customer_id 기준 필터링
- AC2 PRO 목록 조회: 200, items 반환, pro_id 기준 필터링
- AC3 counterpart_display_name 포함: CUSTOMER → pro displayName, PRO → customer displayName
- AC3 service_request 포함: id·description·region·status 필드
- AC3 이메일 미노출: 응답 dict에 'email' 키 없음
- AC4 cursor 페이지네이션: 21개 생성 → 첫 페이지 20개 + nextCursor, 두 번째 페이지 1개 + null
- AC5 비인증 → 401 not_authenticated
- 타 사용자 채팅방 미노출 (교차 오염 방지)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_room import ChatRoom
from app.models.quote import QuoteStatus

from tests.helpers import (
    _auth,
    _make_category,
    _make_customer,
    _make_pro,
    _make_quote,
    _make_service_request,
)

pytestmark = pytest.mark.asyncio

URL = "/api/v1/chat-rooms"


async def _make_chat_room(db: AsyncSession, customer, pro, sr, quote) -> ChatRoom:
    cr = ChatRoom(
        service_request_id=sr.id,
        customer_id=customer.id,
        pro_id=pro.id,
        quote_id=quote.id,
    )
    db.add(cr)
    await db.flush()
    await db.refresh(cr)
    return cr


async def _setup_base(db: AsyncSession):
    """기본 CUSTOMER, PRO, Category, ServiceRequest, Quote, ChatRoom 셋업."""
    customer = await _make_customer(db, "cr-list-cust@example.com")
    pro = await _make_pro(db, "cr-list-pro@example.com")
    cat = await _make_category(db, "채팅방목록테스트")
    sr = await _make_service_request(db, customer, cat, description="기본 서비스 요청")
    quote = await _make_quote(db, pro, sr, status=QuoteStatus.ACCEPTED)
    room = await _make_chat_room(db, customer, pro, sr, quote)
    return customer, pro, cat, sr, quote, room


async def test_ac1_customer_list_200(db_session: AsyncSession, client_db: AsyncClient):
    """AC1: CUSTOMER 기준 채팅방 목록 200 반환."""
    customer, _pro, _cat, _sr, _quote, _room = await _setup_base(db_session)
    resp = await client_db.get(URL, params={"mine": True}, headers=_auth(customer))
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 1


async def test_ac2_pro_list_200(db_session: AsyncSession, client_db: AsyncClient):
    """AC2: PRO 기준 채팅방 목록 200 반환."""
    _customer, pro, _cat, _sr, _quote, _room = await _setup_base(db_session)
    resp = await client_db.get(URL, params={"mine": True}, headers=_auth(pro))
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 1


async def test_ac3_counterpart_display_name_customer(
    db_session: AsyncSession, client_db: AsyncClient
):
    """AC3: CUSTOMER 조회 시 counterpartDisplayName = pro displayName."""
    customer, pro, _cat, _sr, _quote, _room = await _setup_base(db_session)
    resp = await client_db.get(URL, params={"mine": True}, headers=_auth(customer))
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["counterpartDisplayName"] == pro.display_name


async def test_ac3_counterpart_display_name_pro(
    db_session: AsyncSession, client_db: AsyncClient
):
    """AC3: PRO 조회 시 counterpartDisplayName = customer displayName."""
    customer, pro, _cat, _sr, _quote, _room = await _setup_base(db_session)
    resp = await client_db.get(URL, params={"mine": True}, headers=_auth(pro))
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["counterpartDisplayName"] == customer.display_name


async def test_ac3_service_request_fields(db_session: AsyncSession, client_db: AsyncClient):
    """AC3: serviceRequest 필드에 id·description·region·status 포함."""
    customer, _pro, _cat, sr, _quote, _room = await _setup_base(db_session)
    resp = await client_db.get(URL, params={"mine": True}, headers=_auth(customer))
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    sr_data = item["serviceRequest"]
    assert sr_data is not None
    assert "id" in sr_data
    assert "categoryId" in sr_data
    assert sr_data["description"] == sr.description
    assert "region" in sr_data
    assert "status" in sr_data


async def test_ac3_no_email_in_response(db_session: AsyncSession, client_db: AsyncClient):
    """AC3: 응답 JSON에 실제 이메일 주소 미노출."""
    customer, _pro, _cat, _sr, _quote, _room = await _setup_base(db_session)
    resp = await client_db.get(URL, params={"mine": True}, headers=_auth(customer))
    assert resp.status_code == 200
    raw = str(resp.json())
    assert "cr-list-cust@example.com" not in raw
    assert "cr-list-pro@example.com" not in raw


async def test_ac4_cursor_pagination(db_session: AsyncSession, client_db: AsyncClient):
    """AC4: 21개 채팅방 → 첫 페이지 20개 + nextCursor, 두 번째 페이지 1개 + null."""
    customer = await _make_customer(db_session, "cr-page-cust@example.com")
    pro = await _make_pro(db_session, "cr-page-pro@example.com")
    cat = await _make_category(db_session, "페이지네이션테스트")

    for i in range(21):
        sr = await _make_service_request(
            db_session, customer, cat, description=f"요청{i}"
        )
        quote = await _make_quote(db_session, pro, sr, status=QuoteStatus.ACCEPTED)
        await _make_chat_room(db_session, customer, pro, sr, quote)

    resp1 = await client_db.get(URL, params={"mine": True}, headers=_auth(customer))
    assert resp1.status_code == 200
    page1 = resp1.json()
    assert len(page1["items"]) == 20
    assert page1["nextCursor"] is not None

    resp2 = await client_db.get(
        URL, params={"mine": True, "cursor": page1["nextCursor"]}, headers=_auth(customer)
    )
    assert resp2.status_code == 200
    page2 = resp2.json()
    assert len(page2["items"]) == 1
    assert page2["nextCursor"] is None


async def test_ac5_unauthenticated_401(client_db: AsyncClient):
    """AC5: 비인증 요청 → 401 not_authenticated."""
    resp = await client_db.get(URL, params={"mine": True})
    assert resp.status_code == 401
    assert resp.json()["code"] == "not_authenticated"


async def test_cross_user_isolation(db_session: AsyncSession, client_db: AsyncClient):
    """타 사용자 채팅방 미노출 — 교차 오염 방지."""
    customer1, _pro1, _cat, _sr, _quote, _room = await _setup_base(db_session)

    # 별도 사용자 채팅방 생성
    customer2 = await _make_customer(db_session, "cr-other-cust@example.com")
    pro2 = await _make_pro(db_session, "cr-other-pro@example.com")
    cat2 = await _make_category(db_session, "타사용자테스트")
    sr2 = await _make_service_request(db_session, customer2, cat2)
    quote2 = await _make_quote(db_session, pro2, sr2, status=QuoteStatus.ACCEPTED)
    await _make_chat_room(db_session, customer2, pro2, sr2, quote2)

    # customer1은 자신의 방 1개만 조회
    resp = await client_db.get(URL, params={"mine": True}, headers=_auth(customer1))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    # customer1의 방만 포함
    for item in items:
        assert str(item["serviceRequestId"]) == str(_sr.id)
