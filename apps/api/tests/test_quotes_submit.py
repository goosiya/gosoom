"""POST /api/v1/service-requests/{id}/quotes 엔드포인트 테스트 (실 DB + 트랜잭션 롤백, Story 3.3).

검증 대상:
- AC2 성공: 201, status=pending, proId=현재 PRO, 필드 검증
- price=0 허용: 201
- AC3 중복 제안: 409 duplicate_quote
- AC4 요청 not open (matched, cancelled): 409 service_request_not_open
- AC4 카테고리 불일치: 403 forbidden
- AC5 비인증: 401 not_authenticated, CUSTOMER: 403 forbidden, ADMIN: 403 forbidden
- 존재하지 않는 request_id: 404 service_request_not_found
- price 음수: 422, message 빈 문자열: 422
- price 필드 누락: 422, message 필드 누락: 422
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_request import ServiceRequestStatus

from tests.helpers import (
    _auth,
    _assign_pro_categories,
    _make_admin,
    _make_category,
    _make_customer,
    _make_pro,
    _make_service_request,
)

pytestmark = pytest.mark.asyncio


# ---- AC2: 성공 케이스 ----


async def test_submit_quote_success_201(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """정상 PRO + 활동 카테고리 + open 요청 → 201, status=pending, proId=현재 PRO."""
    pro = await _make_pro(db_session, "qt-ok@example.com")
    customer = await _make_customer(db_session, "qt-ok-customer@example.com")
    cat = await _make_category(db_session, "청소-성공")
    await _assign_pro_categories(db_session, pro, [cat])
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        headers=_auth(pro),
        json={"price": 50000, "message": "잘 할 수 있습니다."},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "pending"
    assert data["proId"] == str(pro.id)
    assert data["serviceRequestId"] == str(sr.id)
    assert data["price"] == 50000
    assert data["message"] == "잘 할 수 있습니다."
    assert "id" in data
    assert "createdAt" in data
    assert "updatedAt" in data


async def test_submit_quote_price_zero_201(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """price=0 허용(무료 서비스 가능) → 201."""
    pro = await _make_pro(db_session, "qt-zero@example.com")
    customer = await _make_customer(db_session, "qt-zero-customer@example.com")
    cat = await _make_category(db_session, "청소-제로")
    await _assign_pro_categories(db_session, pro, [cat])
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        headers=_auth(pro),
        json={"price": 0, "message": "무료로 도와드리겠습니다."},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["price"] == 0


# ---- AC3: 중복 제안 ----


async def test_submit_quote_duplicate_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """동일 요청에 재제안 → 409 duplicate_quote."""
    pro = await _make_pro(db_session, "qt-dup@example.com")
    customer = await _make_customer(db_session, "qt-dup-customer@example.com")
    cat = await _make_category(db_session, "청소-중복")
    await _assign_pro_categories(db_session, pro, [cat])
    sr = await _make_service_request(db_session, customer, cat)

    body = {"price": 30000, "message": "첫 번째 제안"}
    await client_db.post(f"/api/v1/service-requests/{sr.id}/quotes", headers=_auth(pro), json=body)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        headers=_auth(pro),
        json={"price": 25000, "message": "두 번째 제안"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "duplicate_quote"


# ---- AC4: 요청 상태·카테고리 불일치 ----


async def test_submit_quote_request_matched_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """matched 요청 → 409 service_request_not_open."""
    pro = await _make_pro(db_session, "qt-matched@example.com")
    customer = await _make_customer(db_session, "qt-matched-customer@example.com")
    cat = await _make_category(db_session, "청소-매칭됨")
    await _assign_pro_categories(db_session, pro, [cat])
    sr = await _make_service_request(db_session, customer, cat, ServiceRequestStatus.MATCHED)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        headers=_auth(pro),
        json={"price": 40000, "message": "견적 제안"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "service_request_not_open"


async def test_submit_quote_request_cancelled_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """cancelled 요청 → 409 service_request_not_open."""
    pro = await _make_pro(db_session, "qt-cancelled@example.com")
    customer = await _make_customer(db_session, "qt-cancelled-customer@example.com")
    cat = await _make_category(db_session, "청소-취소됨")
    await _assign_pro_categories(db_session, pro, [cat])
    sr = await _make_service_request(db_session, customer, cat, ServiceRequestStatus.CANCELLED)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        headers=_auth(pro),
        json={"price": 40000, "message": "견적 제안"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "service_request_not_open"


async def test_submit_quote_category_mismatch_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """PRO 카테고리 불일치(요청 카테고리가 PRO 활동 카테고리에 없음) → 403 forbidden."""
    pro = await _make_pro(db_session, "qt-cat-mismatch@example.com")
    customer = await _make_customer(db_session, "qt-cat-mismatch-customer@example.com")
    request_cat = await _make_category(db_session, "청소-불일치요청")
    other_cat = await _make_category(db_session, "청소-불일치고수")
    # PRO는 other_cat만 활동, request_cat 아님
    await _assign_pro_categories(db_session, pro, [other_cat])
    sr = await _make_service_request(db_session, customer, request_cat)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        headers=_auth(pro),
        json={"price": 40000, "message": "견적 제안"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


# ---- AC5: 권한 제어 ----


async def test_submit_quote_no_token_401(client_db: AsyncClient, db_session: AsyncSession) -> None:
    """비인증 → 401 not_authenticated."""
    customer = await _make_customer(db_session, "qt-noauth-customer@example.com")
    cat = await _make_category(db_session, "청소-비인증")
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        json={"price": 30000, "message": "견적"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "not_authenticated"


async def test_submit_quote_customer_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """CUSTOMER 역할 → 403 forbidden."""
    customer = await _make_customer(db_session, "qt-customer-role@example.com")
    other_customer = await _make_customer(db_session, "qt-customer-role-2@example.com")
    cat = await _make_category(db_session, "청소-고객역할")
    sr = await _make_service_request(db_session, other_customer, cat)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        headers=_auth(customer),
        json={"price": 30000, "message": "견적"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


async def test_submit_quote_admin_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """ADMIN 역할 → 403 forbidden."""
    admin = await _make_admin(db_session, "qt-admin@example.com")
    customer = await _make_customer(db_session, "qt-admin-customer@example.com")
    cat = await _make_category(db_session, "청소-어드민")
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        headers=_auth(admin),
        json={"price": 30000, "message": "견적"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


# ---- 404: 존재하지 않는 request_id ----


async def test_submit_quote_request_not_found_404(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """존재하지 않는 request_id → 404 service_request_not_found."""
    pro = await _make_pro(db_session, "qt-notfound@example.com")
    cat = await _make_category(db_session, "청소-없는요청")
    await _assign_pro_categories(db_session, pro, [cat])

    fake_id = "00000000-0000-0000-0000-000000000099"
    resp = await client_db.post(
        f"/api/v1/service-requests/{fake_id}/quotes",
        headers=_auth(pro),
        json={"price": 30000, "message": "견적"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "service_request_not_found"


# ---- 422: 유효성 검사 ----


async def test_submit_quote_price_negative_422(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """price=-1 → 422."""
    pro = await _make_pro(db_session, "qt-neg@example.com")
    customer = await _make_customer(db_session, "qt-neg-customer@example.com")
    cat = await _make_category(db_session, "청소-음수가격")
    await _assign_pro_categories(db_session, pro, [cat])
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        headers=_auth(pro),
        json={"price": -1, "message": "견적"},
    )
    assert resp.status_code == 422, resp.text


async def test_submit_quote_missing_price_422(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """price 필드 누락 → 422."""
    pro = await _make_pro(db_session, "qt-noprice@example.com")
    customer = await _make_customer(db_session, "qt-noprice-customer@example.com")
    cat = await _make_category(db_session, "청소-가격누락")
    await _assign_pro_categories(db_session, pro, [cat])
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        headers=_auth(pro),
        json={"message": "견적"},
    )
    assert resp.status_code == 422, resp.text


async def test_submit_quote_empty_message_422(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """message 빈 문자열 → 422."""
    pro = await _make_pro(db_session, "qt-emptymsg@example.com")
    customer = await _make_customer(db_session, "qt-emptymsg-customer@example.com")
    cat = await _make_category(db_session, "청소-빈메시지")
    await _assign_pro_categories(db_session, pro, [cat])
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        headers=_auth(pro),
        json={"price": 30000, "message": ""},
    )
    assert resp.status_code == 422, resp.text


async def test_submit_quote_missing_message_422(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """message 필드 누락 → 422."""
    pro = await _make_pro(db_session, "qt-nomsg@example.com")
    customer = await _make_customer(db_session, "qt-nomsg-customer@example.com")
    cat = await _make_category(db_session, "청소-메시지누락")
    await _assign_pro_categories(db_session, pro, [cat])
    sr = await _make_service_request(db_session, customer, cat)

    resp = await client_db.post(
        f"/api/v1/service-requests/{sr.id}/quotes",
        headers=_auth(pro),
        json={"price": 30000},
    )
    assert resp.status_code == 422, resp.text
