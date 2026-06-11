"""POST /api/v1/quotes/{id}/accept 엔드포인트 테스트 (실 DB + 트랜잭션 롤백, Story 4.2).

검증 대상:
- AC1 수락 성공: 200, chat_room 생성, sr→matched, 수락 견적→accepted, 나머지 pending→closed
- AC1 타 pending 견적 closed 전환 확인
- AC3 이미 matched 요청 → 409 service_request_already_matched
- AC3 소유권: 타 고객 견적 수락 → 403
- AC3 견적 not pending → 409 quote_not_pending (rejected 견적으로 테스트)
- AC3 존재하지 않는 견적 → 404 quote_not_found
- AC4 비인증 → 401
- AC4 PRO → 403
- AC4 ADMIN → 403
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import QuoteStatus
from app.models.service_request import ServiceRequestStatus

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


# ---- AC1: 수락 성공 ----


async def test_accept_quote_success_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """수락 성공: 200, chatRoomId 반환, sr→matched, 견적→accepted."""
    customer = await _make_customer(db_session, "acc-ok-cust@example.com")
    pro = await _make_pro(db_session, "acc-ok-pro@example.com")
    cat = await _make_category(db_session, "청소-수락성공")
    sr = await _make_service_request(db_session, customer, cat)
    quote = await _make_quote(db_session, pro, sr)

    resp = await client_db.post(
        f"/api/v1/quotes/{quote.id}/accept", headers=_auth(customer)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "id" in data
    assert data["customerId"] == str(customer.id)
    assert data["proId"] == str(pro.id)
    assert data["quoteId"] == str(quote.id)
    assert data["serviceRequestId"] == str(sr.id)
    assert "createdAt" in data

    # DB 상태 검증
    await db_session.refresh(sr)
    assert sr.status == ServiceRequestStatus.MATCHED

    await db_session.refresh(quote)
    assert quote.status == QuoteStatus.ACCEPTED


async def test_accept_quote_closes_other_pending(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """수락 시 나머지 pending 견적 → closed 전환 검증."""
    customer = await _make_customer(db_session, "acc-close-cust@example.com")
    pro1 = await _make_pro(db_session, "acc-close-pro1@example.com")
    pro2 = await _make_pro(db_session, "acc-close-pro2@example.com")
    cat = await _make_category(db_session, "청소-타견적닫기")
    sr = await _make_service_request(db_session, customer, cat)
    quote1 = await _make_quote(db_session, pro1, sr)
    quote2 = await _make_quote(db_session, pro2, sr)

    resp = await client_db.post(
        f"/api/v1/quotes/{quote1.id}/accept", headers=_auth(customer)
    )
    assert resp.status_code == 200, resp.text

    # 수락된 견적 → accepted
    await db_session.refresh(quote1)
    assert quote1.status == QuoteStatus.ACCEPTED

    # 나머지 pending 견적 → closed
    await db_session.refresh(quote2)
    assert quote2.status == QuoteStatus.CLOSED


# ---- AC3: 거부 케이스 ----


async def test_accept_quote_already_matched_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """이미 matched 상태 요청의 견적 수락 → 409 service_request_already_matched."""
    customer = await _make_customer(db_session, "acc-matched-cust@example.com")
    pro = await _make_pro(db_session, "acc-matched-pro@example.com")
    cat = await _make_category(db_session, "청소-이미매칭")
    sr = await _make_service_request(
        db_session, customer, cat, status=ServiceRequestStatus.MATCHED
    )
    quote = await _make_quote(db_session, pro, sr)

    resp = await client_db.post(
        f"/api/v1/quotes/{quote.id}/accept", headers=_auth(customer)
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "service_request_already_matched"


async def test_accept_quote_other_customer_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """타 고객의 요청 견적 수락 → 403 forbidden."""
    owner = await _make_customer(db_session, "acc-own-cust@example.com")
    other = await _make_customer(db_session, "acc-other-cust@example.com")
    pro = await _make_pro(db_session, "acc-own-pro@example.com")
    cat = await _make_category(db_session, "청소-소유권")
    sr = await _make_service_request(db_session, owner, cat)
    quote = await _make_quote(db_session, pro, sr)

    resp = await client_db.post(
        f"/api/v1/quotes/{quote.id}/accept", headers=_auth(other)
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


async def test_accept_quote_not_pending_rejected_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """pending 아닌 견적(rejected) 수락 → 409 quote_not_pending."""
    customer = await _make_customer(db_session, "acc-notpend-cust@example.com")
    pro = await _make_pro(db_session, "acc-notpend-pro@example.com")
    cat = await _make_category(db_session, "청소-비펜딩")
    sr = await _make_service_request(db_session, customer, cat)
    quote = await _make_quote(db_session, pro, sr, status=QuoteStatus.REJECTED)

    resp = await client_db.post(
        f"/api/v1/quotes/{quote.id}/accept", headers=_auth(customer)
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "quote_not_pending"


async def test_accept_quote_not_pending_accepted_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """pending 아닌 견적(accepted) 수락 → 409 quote_not_pending."""
    customer = await _make_customer(db_session, "acc-notpend-acc-cust@example.com")
    pro = await _make_pro(db_session, "acc-notpend-acc-pro@example.com")
    cat = await _make_category(db_session, "청소-비펜딩수락")
    sr = await _make_service_request(db_session, customer, cat)
    quote = await _make_quote(db_session, pro, sr, status=QuoteStatus.ACCEPTED)

    resp = await client_db.post(
        f"/api/v1/quotes/{quote.id}/accept", headers=_auth(customer)
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "quote_not_pending"


async def test_accept_quote_not_pending_closed_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """pending 아닌 견적(closed) 수락 → 409 quote_not_pending."""
    customer = await _make_customer(db_session, "acc-notpend-cls-cust@example.com")
    pro = await _make_pro(db_session, "acc-notpend-cls-pro@example.com")
    cat = await _make_category(db_session, "청소-비펜딩마감")
    sr = await _make_service_request(db_session, customer, cat)
    quote = await _make_quote(db_session, pro, sr, status=QuoteStatus.CLOSED)

    resp = await client_db.post(
        f"/api/v1/quotes/{quote.id}/accept", headers=_auth(customer)
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "quote_not_pending"


async def test_accept_quote_not_found_404(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """존재하지 않는 견적 ID → 404 quote_not_found."""
    import uuid

    customer = await _make_customer(db_session, "acc-nf-cust@example.com")

    resp = await client_db.post(
        f"/api/v1/quotes/{uuid.uuid4()}/accept", headers=_auth(customer)
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "quote_not_found"


# ---- AC4: 권한 제어 ----


async def test_accept_quote_unauthenticated_401(client_db: AsyncClient) -> None:
    """비인증 요청 → 401 not_authenticated."""
    import uuid

    resp = await client_db.post(f"/api/v1/quotes/{uuid.uuid4()}/accept")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "not_authenticated"


async def test_accept_quote_pro_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """PRO 역할 → 403 forbidden."""
    import uuid

    pro = await _make_pro(db_session, "acc-pro-role@example.com")

    resp = await client_db.post(
        f"/api/v1/quotes/{uuid.uuid4()}/accept", headers=_auth(pro)
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


async def test_accept_quote_admin_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """ADMIN 역할 → 403 forbidden."""
    import uuid

    admin = await _make_admin(db_session, "acc-admin-role@example.com")

    resp = await client_db.post(
        f"/api/v1/quotes/{uuid.uuid4()}/accept", headers=_auth(admin)
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"
