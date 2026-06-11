"""ChatRoomRepository — chat_rooms 테이블 DB 접근 (Story 4.2, 4.5).

규약:
- 트랜잭션(commit)은 소유하지 않는다 — 호출측(service)이 관리.
- create: flush/refresh만 수행, commit은 service에서.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_room import ChatRoom


class ChatRoomRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, obj: ChatRoom) -> ChatRoom:
        """채팅방 추가 후 flush/refresh. commit은 service 계층에서."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, chat_room_id: uuid.UUID) -> ChatRoom | None:
        """PK로 채팅방 단건 조회."""
        return await self.session.get(ChatRoom, chat_room_id)

    async def list_mine(
        self,
        user_id: uuid.UUID,
        role: str,
        after_id: uuid.UUID | None,
        limit: int = 20,
    ) -> list[ChatRoom]:
        """역할별 필터 + keyset cursor + ORDER BY id DESC."""
        if role == "customer":
            stmt = select(ChatRoom).where(ChatRoom.customer_id == user_id)
        else:
            stmt = select(ChatRoom).where(ChatRoom.pro_id == user_id)
        if after_id is not None:
            stmt = stmt.where(ChatRoom.id < after_id)
        stmt = stmt.order_by(ChatRoom.id.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
