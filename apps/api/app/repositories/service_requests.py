"""ServiceRequestRepository — service_requests 테이블 DB 접근 (Story 2.1).

규약(카테고리·사용자 레포지토리 패턴 계승):
- 조회는 소프트삭제 공통 필터 `deleted_at IS NULL` 적용.
- 트랜잭션(commit)은 소유하지 않는다 — 호출측(service)이 관리.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_request import ServiceRequest, ServiceRequestStatus


class ServiceRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, obj: ServiceRequest) -> ServiceRequest:
        """서비스 요청 추가 후 flush/refresh. commit은 service 계층에서."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: uuid.UUID) -> ServiceRequest | None:
        """id로 미삭제 서비스 요청 조회."""
        result = await self.session.execute(
            select(ServiceRequest).where(
                ServiceRequest.id == id,
                ServiceRequest.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_customer(
        self, customer_id: uuid.UUID, after_id: uuid.UUID | None, limit: int
    ) -> list[ServiceRequest]:
        """고객별 요청을 id DESC(최신순) keyset으로 조회. deleted_at IS NULL 필터."""
        stmt = select(ServiceRequest).where(
            ServiceRequest.customer_id == customer_id,
            ServiceRequest.deleted_at.is_(None),
        )
        if after_id is not None:
            stmt = stmt.where(ServiceRequest.id < after_id)
        stmt = stmt.order_by(ServiceRequest.id.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_categories(
        self,
        category_ids: list[uuid.UUID],
        after_id: uuid.UUID | None,
        limit: int,
    ) -> list[ServiceRequest]:
        """고수 피드: 카테고리 일치 요청(open+matched)을 id DESC로 조회."""
        if not category_ids:
            return []
        stmt = select(ServiceRequest).where(
            ServiceRequest.category_id.in_(category_ids),
            ServiceRequest.deleted_at.is_(None),
            ServiceRequest.status.in_([
                ServiceRequestStatus.OPEN,
                ServiceRequestStatus.MATCHED,
            ]),
        )
        if after_id is not None:
            stmt = stmt.where(ServiceRequest.id < after_id)
        stmt = stmt.order_by(ServiceRequest.id.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_ids(self, ids: list[uuid.UUID]) -> list[ServiceRequest]:
        """UUID 목록으로 미삭제 요청 batch 조회. 정렬 없음(호출측이 order 관리)."""
        if not ids:
            return []
        result = await self.session.execute(
            select(ServiceRequest).where(
                ServiceRequest.id.in_(ids),
                ServiceRequest.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def get_by_id_for_update(self, id: uuid.UUID) -> ServiceRequest | None:
        """FR13 동시 수락 race 차단: 요청 행 비관적 잠금(SELECT ... FOR UPDATE)."""
        result = await self.session.execute(
            select(ServiceRequest)
            .where(
                ServiceRequest.id == id,
                ServiceRequest.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        after_id: uuid.UUID | None,
        limit: int,
        include_hidden: bool = False,
    ) -> list[ServiceRequest]:
        """전체 서비스 요청 조회 (관리자 전용). include_hidden=True이면 deleted_at 필터 제거."""
        stmt = select(ServiceRequest)
        if not include_hidden:
            stmt = stmt.where(ServiceRequest.deleted_at.is_(None))
        if after_id is not None:
            stmt = stmt.where(ServiceRequest.id < after_id)
        stmt = stmt.order_by(ServiceRequest.id.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_id_any(self, id: uuid.UUID) -> ServiceRequest | None:
        """id로 요청 조회. deleted_at 무관 (관리자 상태변경·숨김 처리용)."""
        result = await self.session.execute(
            select(ServiceRequest).where(ServiceRequest.id == id)
        )
        return result.scalar_one_or_none()

    async def save(self, obj: ServiceRequest) -> ServiceRequest:
        """ORM 객체 변경사항을 flush/refresh하여 DB 반영. commit은 service 계층에서."""
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
