"""ServiceRequestService — 서비스 요청 비즈니스 로직 (Story 2.1, 2.2).

보안 규칙:
- customer_id는 current_user.id로만 설정 (요청 바디 미수용, IDOR 방지).
- status는 서버에서 OPEN으로 고정 (요청 바디 미수용).
- 카테고리 검증: 비활성 카테고리도 404로 처리.
- get_detail: get_by_id → None이면 404 → 소유권 검사(ensure_owner_or_admin).
"""

import uuid
from uuid import UUID

import uuid_extensions
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import ensure_owner_or_admin
from app.core.exceptions import (
    CategoryNotFoundError,
    ForbiddenError,
    InvalidCursorError,
    InvalidStatusTransitionError,
    ServiceRequestNotFoundError,
)
from app.core.pagination import decode_cursor, encode_cursor
from app.models.service_request import ServiceRequest, ServiceRequestStatus
from app.models.user import User
from app.repositories.categories import CategoryRepository
from app.repositories.pro_categories import ProCategoryRepository
from app.repositories.service_requests import ServiceRequestRepository
from app.schemas.pagination import Page
from app.schemas.service_request import ServiceRequestCreate, ServiceRequestRead


class ServiceRequestService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ServiceRequestRepository(session)
        self.cat_repo = CategoryRepository(session)

    async def create(
        self, data: ServiceRequestCreate, current_user: User
    ) -> ServiceRequest:
        category = await self.cat_repo.get_by_id(data.category_id)
        if category is None:
            raise CategoryNotFoundError()

        new_id = uuid_extensions.uuid7()
        instance = ServiceRequest(
            id=new_id,
            customer_id=current_user.id,
            status=ServiceRequestStatus.OPEN,
            **data.model_dump(),
        )
        result = await self.repo.create(instance)
        await self.session.commit()
        return result

    async def list_mine(
        self, current_user: User, cursor: str | None, limit: int
    ) -> Page[ServiceRequestRead]:
        """본인 요청을 id DESC(최신순) cursor 페이지네이션으로 조회."""
        # 라우터의 ge=1 검증이 1차 방어선이지만, 내부 직접 호출 시 IndexError 방지
        limit = max(1, limit)
        after_id: UUID | None = None
        if cursor is not None:
            decoded = decode_cursor(cursor)
            try:
                after_id = UUID(decoded)
            except (ValueError, AttributeError, TypeError) as exc:
                raise InvalidCursorError() from exc

        rows = await self.repo.list_by_customer(current_user.id, after_id, limit + 1)
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = encode_cursor(str(page_rows[-1].id)) if has_more else None

        return Page[ServiceRequestRead](
            items=[ServiceRequestRead.model_validate(r) for r in page_rows],
            next_cursor=next_cursor,
        )

    async def get_detail(
        self, id: uuid.UUID, current_user: User
    ) -> ServiceRequest:
        """id로 요청 조회 후 소유권 검사. 없으면 404, 타인 소유 시 403."""
        request = await self.repo.get_by_id(id)
        if request is None:
            raise ServiceRequestNotFoundError()
        # request.customer_id는 ORM에서 UUID 타입으로 반환 — str 변환 없이 직접 전달
        ensure_owner_or_admin(request.customer_id, current_user)
        return request

    async def get_feed(
        self, current_user: User, cursor: str | None, limit: int
    ) -> Page[ServiceRequestRead]:
        """PRO 피드: 내 카테고리와 일치하는 요청 목록(open+matched). cursor id DESC."""
        limit = max(1, limit)

        pro_cat_repo = ProCategoryRepository(self.session)
        pro_cats = await pro_cat_repo.list_by_user(current_user.id)
        category_ids = [pc.category_id for pc in pro_cats]

        if not category_ids:
            return Page[ServiceRequestRead](items=[], next_cursor=None)

        after_id: UUID | None = None
        if cursor is not None:
            decoded = decode_cursor(cursor)
            try:
                after_id = UUID(decoded)
            except (ValueError, AttributeError, TypeError) as exc:
                raise InvalidCursorError() from exc

        rows = await self.repo.list_by_categories(category_ids, after_id, limit + 1)
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = encode_cursor(str(page_rows[-1].id)) if has_more else None

        return Page[ServiceRequestRead](
            items=[ServiceRequestRead.model_validate(r) for r in page_rows],
            next_cursor=next_cursor,
        )

    async def get_feed_detail(
        self, request_id: uuid.UUID, current_user: User
    ) -> ServiceRequest:
        """PRO 피드 상세: 자신의 카테고리와 일치하는 요청만 열람 가능."""
        request = await self.repo.get_by_id(request_id)
        if request is None:
            raise ServiceRequestNotFoundError()

        pro_cat_repo = ProCategoryRepository(self.session)
        pro_cats = await pro_cat_repo.list_by_user(current_user.id)
        category_ids = {pc.category_id for pc in pro_cats}

        if request.category_id not in category_ids:
            raise ForbiddenError()

        return request

    async def change_status(
        self, id: UUID, action: str, current_user: User
    ) -> ServiceRequest:
        """상태 전이 시행 (취소: open→cancelled, 완료: matched→completed).

        순서: 404 우선 → 소유권(403) → 전이 규칙(409) → save.
        """
        request = await self.repo.get_by_id(id)
        if request is None:
            raise ServiceRequestNotFoundError()
        # request.customer_id는 ORM에서 UUID 타입 — str 변환 절대 금지
        ensure_owner_or_admin(request.customer_id, current_user)

        if action == "cancel":
            if request.status != ServiceRequestStatus.OPEN:
                raise InvalidStatusTransitionError()
            request.status = ServiceRequestStatus.CANCELLED
        elif action == "complete":
            if request.status != ServiceRequestStatus.MATCHED:
                raise InvalidStatusTransitionError()
            request.status = ServiceRequestStatus.COMPLETED
        else:
            raise InvalidStatusTransitionError()

        result = await self.repo.save(request)
        await self.session.commit()
        return result
