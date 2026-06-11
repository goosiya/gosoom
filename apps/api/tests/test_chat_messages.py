"""채팅 메시지 전송·수신 엔드포인트 테스트 (실 DB + 트랜잭션 롤백, Story 4.4).

검증 대상:
- AC2 메시지 전송 성공 (CUSTOMER): 201, senderId=customer.id
- AC2 메시지 전송 성공 (PRO): 201, senderId=pro.id
- AC3 목록 초기 조회 (after 없음): 200, items 반환
- AC3 목록 증분 조회 (after=lastId): 신규 메시지만 반환
- AC3 after 이후 신규 없음: 200, items=[]
- AC4 비인증 → 401 not_authenticated
- AC4 비참여자(타 고객) 전송 → 403 forbidden
- AC4 비참여자(타 고수) 전송 → 403 forbidden
- AC4 비참여자(ADMIN) → 403 forbidden
- AC4 존재하지 않는 채팅방 → 404 chat_room_not_found
- AC4 빈 content 전송 → 422
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_room import ChatRoom
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

FAKE_UUID = "00000000-0000-0000-0000-000000000001"


async def _make_chat_room(
    db: AsyncSession, customer, pro, sr, quote
) -> ChatRoom:
    """테스트용 ChatRoom 생성 헬퍼."""
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


async def _setup_chat_room(db: AsyncSession):
    """기본 채팅방 + 참여자 셋업 헬퍼."""
    customer = await _make_customer(db, "chat-cust@example.com")
    pro = await _make_pro(db, "chat-pro@example.com")
    cat = await _make_category(db, "채팅테스트")
    sr = await _make_service_request(
        db, customer, cat, status=ServiceRequestStatus.MATCHED
    )
    quote = await _make_quote(db, pro, sr, status=QuoteStatus.ACCEPTED)
    cr = await _make_chat_room(db, customer, pro, sr, quote)
    return customer, pro, cr


# ---- AC2: 메시지 전송 성공 ----


async def test_send_message_customer_201(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """CUSTOMER 전송 성공: 201, senderId=customer.id."""
    customer, pro, cr = await _setup_chat_room(db_session)

    resp = await client_db.post(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        json={"content": "내일 오전 10시 가능한가요?"},
        headers=_auth(customer),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["content"] == "내일 오전 10시 가능한가요?"
    assert data["senderId"] == str(customer.id)
    assert data["chatRoomId"] == str(cr.id)
    assert "id" in data
    assert "createdAt" in data


async def test_send_message_pro_201(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """PRO 전송 성공: 201, senderId=pro.id."""
    customer = await _make_customer(db_session, "chat-pro-send-cust@example.com")
    pro = await _make_pro(db_session, "chat-pro-send-pro@example.com")
    cat = await _make_category(db_session, "채팅PRO전송")
    sr = await _make_service_request(
        db_session, customer, cat, status=ServiceRequestStatus.MATCHED
    )
    quote = await _make_quote(db_session, pro, sr, status=QuoteStatus.ACCEPTED)
    cr = await _make_chat_room(db_session, customer, pro, sr, quote)

    resp = await client_db.post(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        json={"content": "네, 가능합니다."},
        headers=_auth(pro),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["senderId"] == str(pro.id)


# ---- AC3: 메시지 목록 조회 ----


async def test_list_messages_initial_200(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """초기 조회 (after 없음): 200, items 반환."""
    customer = await _make_customer(db_session, "chat-list-init-cust@example.com")
    pro = await _make_pro(db_session, "chat-list-init-pro@example.com")
    cat = await _make_category(db_session, "채팅목록초기")
    sr = await _make_service_request(
        db_session, customer, cat, status=ServiceRequestStatus.MATCHED
    )
    quote = await _make_quote(db_session, pro, sr, status=QuoteStatus.ACCEPTED)
    cr = await _make_chat_room(db_session, customer, pro, sr, quote)

    # 메시지 2개 전송
    await client_db.post(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        json={"content": "첫 번째 메시지"},
        headers=_auth(customer),
    )
    await client_db.post(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        json={"content": "두 번째 메시지"},
        headers=_auth(pro),
    )

    resp = await client_db.get(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        headers=_auth(customer),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 2
    # ASC 정렬 확인
    assert data["items"][0]["content"] == "첫 번째 메시지"
    assert data["items"][1]["content"] == "두 번째 메시지"


async def test_list_messages_incremental_after(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """증분 폴링 (after=msg1_id): msg2만 반환, msg1 제외."""
    customer = await _make_customer(db_session, "chat-incr-cust@example.com")
    pro = await _make_pro(db_session, "chat-incr-pro@example.com")
    cat = await _make_category(db_session, "채팅증분")
    sr = await _make_service_request(
        db_session, customer, cat, status=ServiceRequestStatus.MATCHED
    )
    quote = await _make_quote(db_session, pro, sr, status=QuoteStatus.ACCEPTED)
    cr = await _make_chat_room(db_session, customer, pro, sr, quote)

    # 메시지 1 전송
    resp1 = await client_db.post(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        json={"content": "첫 메시지"},
        headers=_auth(customer),
    )
    assert resp1.status_code == 201
    msg1_id = resp1.json()["id"]

    # 메시지 2 전송
    resp2 = await client_db.post(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        json={"content": "두 번째 메시지"},
        headers=_auth(pro),
    )
    assert resp2.status_code == 201

    # after=msg1_id → msg2만 반환
    resp = await client_db.get(
        f"/api/v1/chat-rooms/{cr.id}/messages?after={msg1_id}",
        headers=_auth(customer),
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["content"] == "두 번째 메시지"


async def test_list_messages_empty_after_latest(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """after=최신메시지ID → items=[] 반환."""
    customer = await _make_customer(db_session, "chat-empty-cust@example.com")
    pro = await _make_pro(db_session, "chat-empty-pro@example.com")
    cat = await _make_category(db_session, "채팅빈폴링")
    sr = await _make_service_request(
        db_session, customer, cat, status=ServiceRequestStatus.MATCHED
    )
    quote = await _make_quote(db_session, pro, sr, status=QuoteStatus.ACCEPTED)
    cr = await _make_chat_room(db_session, customer, pro, sr, quote)

    # 메시지 1개 전송
    resp1 = await client_db.post(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        json={"content": "유일 메시지"},
        headers=_auth(customer),
    )
    msg1_id = resp1.json()["id"]

    # after=msg1_id → 신규 없음 → items=[]
    resp = await client_db.get(
        f"/api/v1/chat-rooms/{cr.id}/messages?after={msg1_id}",
        headers=_auth(customer),
    )
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ---- AC4: 권한 검사 ----


async def test_send_message_unauthenticated_401(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """비인증 → 401 not_authenticated."""
    customer, pro, cr = await _setup_chat_room(db_session)

    resp = await client_db.post(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        json={"content": "메시지"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "not_authenticated"


async def test_send_message_non_participant_customer_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """비참여자(타 고객) 전송 → 403 forbidden."""
    customer, pro, cr = await _setup_chat_room(db_session)
    other_customer = await _make_customer(db_session, "chat-other-cust@example.com")

    resp = await client_db.post(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        json={"content": "메시지"},
        headers=_auth(other_customer),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


async def test_send_message_non_participant_pro_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """비참여자(타 고수) 전송 → 403 forbidden."""
    customer, pro, cr = await _setup_chat_room(db_session)
    other_pro = await _make_pro(db_session, "chat-other-pro@example.com")

    resp = await client_db.post(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        json={"content": "메시지"},
        headers=_auth(other_pro),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


async def test_send_message_admin_403(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """비참여자(ADMIN) 전송 → 403 forbidden."""
    customer, pro, cr = await _setup_chat_room(db_session)
    admin = await _make_admin(db_session, "chat-admin@example.com")

    resp = await client_db.post(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        json={"content": "메시지"},
        headers=_auth(admin),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


async def test_send_message_not_found_404(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """존재하지 않는 채팅방 → 404 chat_room_not_found."""
    customer = await _make_customer(db_session, "chat-404-cust@example.com")

    resp = await client_db.post(
        f"/api/v1/chat-rooms/{FAKE_UUID}/messages",
        json={"content": "메시지"},
        headers=_auth(customer),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "chat_room_not_found"


async def test_send_message_empty_content_422(
    client_db: AsyncClient, db_session: AsyncSession
) -> None:
    """빈 content → 422 Unprocessable Entity."""
    customer, pro, cr = await _setup_chat_room(db_session)

    resp = await client_db.post(
        f"/api/v1/chat-rooms/{cr.id}/messages",
        json={"content": ""},
        headers=_auth(customer),
    )
    assert resp.status_code == 422
