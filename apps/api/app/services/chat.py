"""ChatService — 채팅 메시지 전송·수신·목록 서비스 (Story 4.4, 4.5)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ChatRoomNotFoundError, ForbiddenError
from app.models.message import Message
from app.models.user import User
from app.repositories.chat_rooms import ChatRoomRepository
from app.repositories.messages import MessageRepository
from app.repositories.service_requests import ServiceRequestRepository
from app.repositories.users import UserRepository
from app.schemas.chat_room import ChatRoomListItem, PageChatRoomListItem
from app.schemas.service_request import ServiceRequestSummary


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.chat_room_repo = ChatRoomRepository(session)
        self.message_repo = MessageRepository(session)

    async def _get_room_and_check_participant(self, chat_room_id: uuid.UUID, current_user: User):
        """채팅방 조회 + 참여자 검사 — 두 엔드포인트 공통 가드."""
        chat_room = await self.chat_room_repo.get_by_id(chat_room_id)
        if chat_room is None:
            raise ChatRoomNotFoundError()
        if current_user.id not in (chat_room.customer_id, chat_room.pro_id):
            raise ForbiddenError()
        return chat_room

    async def send_message(
        self, chat_room_id: uuid.UUID, content: str, current_user: User
    ) -> Message:
        """메시지 전송 — 채팅방 존재 및 참여자 확인 후 저장."""
        await self._get_room_and_check_participant(chat_room_id, current_user)
        msg = Message(
            chat_room_id=chat_room_id,
            sender_id=current_user.id,
            content=content,
        )
        await self.message_repo.create(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg

    async def list_messages(
        self,
        chat_room_id: uuid.UUID,
        after_id: uuid.UUID | None,
        current_user: User,
    ) -> list[Message]:
        """메시지 목록 조회 — 채팅방 존재 및 참여자 확인 후 조회."""
        await self._get_room_and_check_participant(chat_room_id, current_user)
        return await self.message_repo.list_after(chat_room_id, after_id)

    async def list_my_chat_rooms(
        self,
        current_user: User,
        cursor: uuid.UUID | None,
    ) -> PageChatRoomListItem:
        """현재 사용자의 채팅방 목록 — LIMIT+1 cursor 페이지네이션."""
        LIMIT = 20
        rooms = await self.chat_room_repo.list_mine(
            current_user.id,
            current_user.user_role.value,
            cursor,
            LIMIT + 1,
        )
        has_more = len(rooms) > LIMIT
        if has_more:
            rooms = rooms[:LIMIT]

        if not rooms:
            return PageChatRoomListItem(items=[], next_cursor=None)

        next_cursor = rooms[-1].id if has_more else None

        user_repo = UserRepository(self.session)
        sr_repo = ServiceRequestRepository(self.session)

        is_customer = current_user.user_role.value == "customer"
        counterpart_ids = [r.pro_id if is_customer else r.customer_id for r in rooms]
        sr_ids = [r.service_request_id for r in rooms]

        counterparts = {u.id: u for u in await user_repo.list_by_ids(counterpart_ids)}
        srs = {sr.id: sr for sr in await sr_repo.list_by_ids(sr_ids)}

        items = []
        for room in rooms:
            cp_id = room.pro_id if is_customer else room.customer_id
            cp = counterparts.get(cp_id)
            sr = srs.get(room.service_request_id)
            items.append(
                ChatRoomListItem(
                    id=room.id,
                    service_request_id=room.service_request_id,
                    created_at=room.created_at,
                    counterpart_display_name=cp.display_name if cp else "알 수 없음",
                    service_request=ServiceRequestSummary.model_validate(sr) if sr else None,
                )
            )

        return PageChatRoomListItem(items=items, next_cursor=next_cursor)
