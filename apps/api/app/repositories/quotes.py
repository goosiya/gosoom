"""QuoteRepository — quotes 테이블 DB 접근 (Story 3.3/3.4/4.1).

규약:
- 트랜잭션(commit)은 소유하지 않는다 — 호출측(service)이 관리.
- get_by_id: deleted_at IS NULL 필터 적용.
- get_by_request_and_pro: deleted_at IS NULL 필터 적용 (중복 검사는 미삭제 견적만).
- list_by_pro: deleted_at IS NULL 필터 + id DESC keyset cursor 페이지네이션.
- list_by_request: deleted_at IS NULL 필터 + id DESC keyset cursor 페이지네이션 (Story 4.1).
"""

import uuid

from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote, QuoteStatus


class QuoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, obj: Quote) -> Quote:
        """견적 추가 후 flush/refresh. commit은 service 계층에서."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: uuid.UUID) -> Quote | None:
        """id로 미삭제 견적 조회."""
        result = await self.session.execute(
            select(Quote).where(
                Quote.id == id,
                Quote.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_request_and_pro(
        self, request_id: uuid.UUID, pro_id: uuid.UUID
    ) -> Quote | None:
        """특정 요청에 대한 특정 PRO의 미삭제 견적 조회 (중복 검사용)."""
        result = await self.session.execute(
            select(Quote).where(
                Quote.service_request_id == request_id,
                Quote.pro_id == pro_id,
                Quote.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_pro(
        self, pro_id: uuid.UUID, after_id: uuid.UUID | None, limit: int
    ) -> list[Quote]:
        """PRO의 견적을 id DESC(최신순) keyset으로 조회. deleted_at IS NULL 필터."""
        stmt = select(Quote).where(
            Quote.pro_id == pro_id,
            Quote.deleted_at.is_(None),
        )
        if after_id is not None:
            stmt = stmt.where(Quote.id < after_id)
        stmt = stmt.order_by(Quote.id.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def close_pending_except(
        self, request_id: uuid.UUID, exclude_quote_id: uuid.UUID
    ) -> None:
        """해당 요청의 현재 견적 제외 pending 견적을 bulk closed로 전환.

        synchronize_session=False: bulk update는 ORM 세션 캐시를 갱신하지 않음.
        호출측에서 이미 로드된 Quote 객체를 재사용하지 않으므로 안전.
        """
        await self.session.execute(
            sa_update(Quote)
            .where(
                Quote.service_request_id == request_id,
                Quote.status == QuoteStatus.PENDING,
                Quote.id != exclude_quote_id,
                Quote.deleted_at.is_(None),
            )
            .values(status=QuoteStatus.CLOSED)
            .execution_options(synchronize_session=False)
        )

    async def list_by_request(
        self, request_id: uuid.UUID, after_id: uuid.UUID | None, limit: int
    ) -> list[Quote]:
        """특정 요청의 견적을 id DESC(최신순) keyset으로 조회. deleted_at IS NULL 필터."""
        stmt = select(Quote).where(
            Quote.service_request_id == request_id,
            Quote.deleted_at.is_(None),
        )
        if after_id is not None:
            stmt = stmt.where(Quote.id < after_id)
        stmt = stmt.order_by(Quote.id.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
