"""MessageRepository — messages 테이블 DB 접근 (Story 4.4).

규약:
- 트랜잭션(commit)은 소유하지 않는다 — 호출측(service)이 관리.
- create: flush/refresh만 수행, commit은 service에서.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, obj: Message) -> Message:
        """메시지 추가 후 flush/refresh. commit은 service 계층에서."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def list_before(
        self,
        chat_room_id: uuid.UUID,
        before_id: uuid.UUID | None,
        limit: int = 50,
    ) -> list[Message]:
        """관리자 전용: before_id보다 이전(오래된) 메시지를 limit개 조회. ASC 순서 반환."""
        stmt = select(Message).where(Message.chat_room_id == chat_room_id)
        if before_id is not None:
            stmt = stmt.where(Message.id < before_id)
        stmt = stmt.order_by(Message.id.desc()).limit(limit)
        result = await self.session.execute(stmt)
        msgs = list(result.scalars().all())
        return list(reversed(msgs))

    async def list_after(
        self,
        chat_room_id: uuid.UUID,
        after_id: uuid.UUID | None,
        limit: int = 50,
    ) -> list[Message]:
        """채팅방 메시지 목록 조회.

        after_id=None: 최신 50개를 DESC로 가져와 ASC 역순 반환(초기 로드).
        after_id 있음: after_id 이후 신규 메시지만 ASC 순서로 반환(증분 폴링).
        UUIDv7 상위 48비트 = 밀리초 타임스탬프 → id > after_id는 시간 순 비교와 동일.
        """
        if after_id is None:
            stmt = (
                select(Message)
                .where(Message.chat_room_id == chat_room_id)
                .order_by(Message.id.desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            msgs = list(result.scalars().all())
            return list(reversed(msgs))
        else:
            stmt = (
                select(Message)
                .where(
                    Message.chat_room_id == chat_room_id,
                    Message.id > after_id,
                )
                .order_by(Message.id.asc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
