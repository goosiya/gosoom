"""POST /api/v1/quotes/{id}/reject 엔드포인트 테스트 (실 DB + 트랜잭션 롤백, Story 4.3).

검증 대상:
- AC1 거절 성공: 200, quote.status → rejected, sr.status → open (변경 없음)
- AC3 소유권: 타 고객 → 403 forbidden
- AC3 견적 not pending (accepted) → 409 quote_not_pending
- AC3 견적 not pending (rejected) → 409 quote_not_pending
- AC3 견적 not pending (closed) → 409 quote_not_pending
- AC3 존재하지 않는 견적 → 404 quote_not_found
- AC4 비인증 → 401 not_authenticated
- AC4 PRO 역할 → 403 forbidden
- AC4 ADMIN 역할 → 403 forbidden
"""

import uuid

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


# ---- AC1: 거절 성공 ----


async def test_reject_quote_success_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """거절 성공: 200, quote.status → rejected, sr.status → open 유지."""
    customer = await _make_customer(db_session, "rej-ok-cust@example.com")
    pro = await _make_pro(db_session, "rej-ok-pro@example.com")
    cat = await _make_category(db_session, "청소-거절성공")
    sr = await _make_service_request(db_session, customer, cat)
    quote = await _make_quote(db_session, pro, sr)

    resp = await client_db.post(
        f"/api/v1/quotes/{quote.id}/reject", headers=_auth(customer)
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["id"] == str(quote.id)
    assert data["status"] == "rejected"

    # DB 상태 검증 — sr.status는 open 유지
    await db_session.refresh(quote)
    assert quote.status == QuoteStatus.REJECTED

    await db_session.refresh(sr)
    assert sr.status == ServiceRequestStatus.OPEN


# ---- AC3: 거부 케이스 ----


async def test_reject_quote_other_customer_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """타 고객의 요청 견적 거절 → 403 forbidden."""
    owner = await _make_customer(db_session, "rej-own-cust@example.com")
    other = await _make_customer(db_session, "rej-other-cust@example.com")
    pro = await _make_pro(db_session, "rej-own-pro@example.com")
    cat = await _make_category(db_session, "청소-거절소유권")
    sr = await _make_service_request(db_session, owner, cat)
    quote = await _make_quote(db_session, pro, sr)

    resp = await client_db.post(
        f"/api/v1/quotes/{quote.id}/reject", headers=_auth(other)
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


async def test_reject_quote_not_pending_accepted_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """pending 아닌 견적(accepted) 거절 → 409 quote_not_pending."""
    customer = await _make_customer(db_session, "rej-notpend-acc-cust@example.com")
    pro = await _make_pro(db_session, "rej-notpend-acc-pro@example.com")
    cat = await _make_category(db_session, "청소-거절비펜딩수락")
    sr = await _make_service_request(db_session, customer, cat)
    quote = await _make_quote(db_session, pro, sr, status=QuoteStatus.ACCEPTED)

    resp = await client_db.post(
        f"/api/v1/quotes/{quote.id}/reject", headers=_auth(customer)
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "quote_not_pending"


async def test_reject_quote_not_pending_rejected_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """pending 아닌 견적(rejected) 거절 → 409 quote_not_pending."""
    customer = await _make_customer(db_session, "rej-notpend-rej-cust@example.com")
    pro = await _make_pro(db_session, "rej-notpend-rej-pro@example.com")
    cat = await _make_category(db_session, "청소-거절비펜딩거절")
    sr = await _make_service_request(db_session, customer, cat)
    quote = await _make_quote(db_session, pro, sr, status=QuoteStatus.REJECTED)

    resp = await client_db.post(
        f"/api/v1/quotes/{quote.id}/reject", headers=_auth(customer)
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "quote_not_pending"


async def test_reject_quote_not_pending_closed_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """pending 아닌 견적(closed) 거절 → 409 quote_not_pending."""
    customer = await _make_customer(db_session, "rej-notpend-cls-cust@example.com")
    pro = await _make_pro(db_session, "rej-notpend-cls-pro@example.com")
    cat = await _make_category(db_session, "청소-거절비펜딩마감")
    sr = await _make_service_request(db_session, customer, cat)
    quote = await _make_quote(db_session, pro, sr, status=QuoteStatus.CLOSED)

    resp = await client_db.post(
        f"/api/v1/quotes/{quote.id}/reject", headers=_auth(customer)
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "quote_not_pending"


async def test_reject_quote_not_found_404(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """존재하지 않는 견적 ID → 404 quote_not_found."""
    customer = await _make_customer(db_session, "rej-nf-cust@example.com")

    resp = await client_db.post(
        f"/api/v1/quotes/{uuid.uuid4()}/reject", headers=_auth(customer)
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "quote_not_found"


# ---- AC4: 권한 제어 ----


async def test_reject_quote_unauthenticated_401(client_db: AsyncClient) -> None:
    """비인증 요청 → 401 not_authenticated."""
    resp = await client_db.post(f"/api/v1/quotes/{uuid.uuid4()}/reject")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "not_authenticated"


async def test_reject_quote_pro_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """PRO 역할 → 403 forbidden."""
    pro = await _make_pro(db_session, "rej-pro-role@example.com")

    resp = await client_db.post(
        f"/api/v1/quotes/{uuid.uuid4()}/reject", headers=_auth(pro)
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


async def test_reject_quote_admin_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """ADMIN 역할 → 403 forbidden."""
    admin = await _make_admin(db_session, "rej-admin-role@example.com")

    resp = await client_db.post(
        f"/api/v1/quotes/{uuid.uuid4()}/reject", headers=_auth(admin)
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"
