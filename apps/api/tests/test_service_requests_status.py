"""PATCH /api/v1/service-requests/{id} 상태 전이 테스트 (Story 2.3).

검증 대상:
- AC1 취소: open → cancelled 200
- AC2 완료: matched → completed 200
- AC3 허용되지 않는 전이: 409 + code == "invalid_status_transition"
- AC4 권한 제어: 403(타인·PRO·ADMIN), 401(미인증·비활성), 404(미존재)
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_request import ServiceRequestStatus

from tests.helpers import (
    _auth,
    _make_admin,
    _make_category,
    _make_customer,
    _make_pro,
    _make_service_request,
)

pytestmark = pytest.mark.asyncio


# ---- 테스트 케이스 ----


async def test_cancel_open_request_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    customer = await _make_customer(db_session, "cancel_open@test.com")
    cat = await _make_category(db_session, "청소_c1")
    req = await _make_service_request(db_session, customer, cat, ServiceRequestStatus.OPEN)

    r = await client_db.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(customer),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


async def test_complete_matched_request_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    customer = await _make_customer(db_session, "complete_matched@test.com")
    cat = await _make_category(db_session, "청소_c2")
    req = await _make_service_request(db_session, customer, cat, ServiceRequestStatus.MATCHED)

    r = await client_db.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "complete"},
        headers=_auth(customer),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


async def test_cancel_matched_request_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    customer = await _make_customer(db_session, "cancel_matched@test.com")
    cat = await _make_category(db_session, "청소_c3")
    req = await _make_service_request(db_session, customer, cat, ServiceRequestStatus.MATCHED)

    r = await client_db.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(customer),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "invalid_status_transition"


async def test_complete_open_request_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    customer = await _make_customer(db_session, "complete_open@test.com")
    cat = await _make_category(db_session, "청소_c4")
    req = await _make_service_request(db_session, customer, cat, ServiceRequestStatus.OPEN)

    r = await client_db.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "complete"},
        headers=_auth(customer),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "invalid_status_transition"


async def test_cancel_cancelled_request_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    customer = await _make_customer(db_session, "cancel_cancelled@test.com")
    cat = await _make_category(db_session, "청소_c5")
    req = await _make_service_request(db_session, customer, cat, ServiceRequestStatus.CANCELLED)

    r = await client_db.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(customer),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "invalid_status_transition"


async def test_cancel_completed_request_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    customer = await _make_customer(db_session, "cancel_completed@test.com")
    cat = await _make_category(db_session, "청소_c6")
    req = await _make_service_request(db_session, customer, cat, ServiceRequestStatus.COMPLETED)

    r = await client_db.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(customer),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "invalid_status_transition"


async def test_other_customer_cancel_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    owner = await _make_customer(db_session, "owner403@test.com")
    other = await _make_customer(db_session, "other403@test.com")
    cat = await _make_category(db_session, "청소_c7")
    req = await _make_service_request(db_session, owner, cat, ServiceRequestStatus.OPEN)

    r = await client_db.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(other),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


async def test_not_found_404(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    customer = await _make_customer(db_session, "notfound404@test.com")
    fake_id = uuid.uuid4()

    r = await client_db.patch(
        f"/api/v1/service-requests/{fake_id}",
        json={"action": "cancel"},
        headers=_auth(customer),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "service_request_not_found"


async def test_no_token_401(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    customer = await _make_customer(db_session, "notoken401@test.com")
    cat = await _make_category(db_session, "청소_c8")
    req = await _make_service_request(db_session, customer, cat)

    r = await client_db.patch(f"/api/v1/service-requests/{req.id}", json={"action": "cancel"})
    assert r.status_code == 401


async def test_inactive_customer_401(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    customer = await _make_customer(db_session, "inactive401@test.com")
    customer.is_active = False
    await db_session.flush()
    cat = await _make_category(db_session, "청소_c9")
    req = await _make_service_request(db_session, customer, cat)

    r = await client_db.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(customer),
    )
    assert r.status_code == 401


async def test_complete_cancelled_request_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    customer = await _make_customer(db_session, "complete_cancelled@test.com")
    cat = await _make_category(db_session, "청소_c12")
    req = await _make_service_request(db_session, customer, cat, ServiceRequestStatus.CANCELLED)

    r = await client_db.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "complete"},
        headers=_auth(customer),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "invalid_status_transition"


async def test_complete_completed_request_409(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    customer = await _make_customer(db_session, "complete_completed@test.com")
    cat = await _make_category(db_session, "청소_c13")
    req = await _make_service_request(db_session, customer, cat, ServiceRequestStatus.COMPLETED)

    r = await client_db.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "complete"},
        headers=_auth(customer),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "invalid_status_transition"


async def test_pro_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    pro = await _make_pro(db_session, "pro403@test.com")
    customer = await _make_customer(db_session, "pro403_owner@test.com")
    cat = await _make_category(db_session, "청소_c10")
    req = await _make_service_request(db_session, customer, cat)

    r = await client_db.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(pro),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


async def test_admin_role_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await _make_admin(db_session, "admin403@test.com")
    customer = await _make_customer(db_session, "admin403_owner@test.com")
    cat = await _make_category(db_session, "청소_c11")
    req = await _make_service_request(db_session, customer, cat)

    r = await client_db.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(admin),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"
