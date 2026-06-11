"""admin 서비스 — 고객·고수·관리자 계정 관리 (Story 6.2, 6.3).

비즈니스 규칙:
- 고객·고수 대상: list_users/get_user/deactivate_user/activate_user (6.2)
- 관리자 대상: list_admins/create_admin/deactivate_admin (6.3)
- 비활성화: is_active=False → deps.get_current_user가 다음 요청부터 즉시 차단.
- 소프트 비활성화: 데이터 물리 삭제 금지.
- 트랜잭션 commit은 이 service가 직접 수행.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DuplicateEmailError,
    ForbiddenError,
    InvalidCursorError,
    InvalidStatusTransitionError,
    SeedAdminDeactivationError,
    ServiceRequestNotFoundError,
    UserNotFoundError,
)
from app.core.pagination import decode_cursor, encode_cursor
from app.core.security import hash_password
from app.models.service_request import ServiceRequestStatus
from app.models.user import User, UserRole
from app.repositories.service_requests import ServiceRequestRepository
from app.repositories.users import UserRepository
from app.schemas.auth import AdminCreateRequest, UserRead
from app.schemas.pagination import Page
from app.schemas.service_request import ServiceRequestAdminRead


class AdminUserService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = UserRepository(session)
        self.session = session

    async def list_users(
        self,
        role: UserRole,
        cursor: str | None,
        limit: int,
    ) -> Page[UserRead]:
        # 6.2는 customer·pro만 관리. admin 계정 목록 조회는 Story 6.3 범위.
        if role == UserRole.ADMIN:
            raise ForbiddenError()
        assert limit >= 1, "limit must be >= 1"
        after_id: UUID | None = None
        if cursor:
            try:
                after_id = UUID(decode_cursor(cursor))
            except (ValueError, AttributeError) as exc:
                raise InvalidCursorError() from exc
        rows = await self.repo.list_by_role(role, after_id, limit + 1)
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = encode_cursor(str(page[-1].id)) if has_more else None
        return Page(
            items=[UserRead.model_validate(u) for u in page],
            next_cursor=next_cursor,
        )

    async def get_user(self, user_id: UUID) -> UserRead:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        # admin 계정 관리는 Story 6.3 범위
        if user.user_role == UserRole.ADMIN:
            raise ForbiddenError()
        return UserRead.model_validate(user)

    async def deactivate_user(self, user_id: UUID) -> UserRead:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        # admin 계정 관리는 Story 6.3 범위
        if user.user_role == UserRole.ADMIN:
            raise ForbiddenError()
        user.is_active = False
        await self.repo.save(user)
        await self.session.commit()
        return UserRead.model_validate(user)

    async def activate_user(self, user_id: UUID) -> UserRead:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        if user.user_role == UserRole.ADMIN:
            raise ForbiddenError()
        user.is_active = True
        await self.repo.save(user)
        await self.session.commit()
        return UserRead.model_validate(user)

    async def list_admins(
        self,
        cursor: str | None,
        limit: int,
    ) -> "Page[UserRead]":
        """관리자(ADMIN role) 목록 조회 — cursor 페이지네이션."""
        assert limit >= 1, "limit must be >= 1"
        after_id: UUID | None = None
        if cursor:
            try:
                after_id = UUID(decode_cursor(cursor))
            except (ValueError, AttributeError) as exc:
                raise InvalidCursorError() from exc
        rows = await self.repo.list_by_role(UserRole.ADMIN, after_id, limit + 1)
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = encode_cursor(str(page[-1].id)) if has_more else None
        return Page(
            items=[UserRead.model_validate(u) for u in page],
            next_cursor=next_cursor,
        )

    async def create_admin(self, data: AdminCreateRequest) -> UserRead:
        """신규 관리자 생성 — 기존 관리자에 의한 생성 경로만 허용(FR1/FR21)."""
        existing = await self.repo.get_by_email(data.email)
        if existing is not None:
            raise DuplicateEmailError()
        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            display_name=data.display_name,
            user_role=UserRole.ADMIN,
        )
        try:
            await self.repo.create(user)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateEmailError() from exc
        return UserRead.model_validate(user)

    async def deactivate_admin(self, admin_id: UUID) -> UserRead:
        """관리자 계정 비활성화 — 시드 관리자는 보호(FR21)."""
        user = await self.repo.get_by_id(admin_id)
        if user is None:
            raise UserNotFoundError()
        if user.user_role != UserRole.ADMIN:
            raise ForbiddenError()
        if user.is_seed:
            raise SeedAdminDeactivationError()
        user.is_active = False
        await self.repo.save(user)
        await self.session.commit()
        return UserRead.model_validate(user)


class AdminServiceRequestService:
    """서비스 요청 관리 (Story 6.4) — 소유권 검사 없는 관리자 전용 로직."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = ServiceRequestRepository(session)
        self.session = session

    async def list_requests(
        self,
        cursor: str | None,
        limit: int,
        include_hidden: bool = False,
    ) -> "Page[ServiceRequestAdminRead]":
        """전체 서비스 요청 목록 조회 — cursor id DESC 페이지네이션."""
        if limit < 1:
            raise ValueError("limit must be >= 1")
        after_id: UUID | None = None
        if cursor:
            try:
                after_id = UUID(decode_cursor(cursor))
            except (ValueError, AttributeError) as exc:
                raise InvalidCursorError() from exc
        rows = await self.repo.list_all(after_id, limit + 1, include_hidden)
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = encode_cursor(str(page[-1].id)) if has_more else None
        return Page(
            items=[ServiceRequestAdminRead.model_validate(r) for r in page],
            next_cursor=next_cursor,
        )

    async def change_status(
        self,
        request_id: UUID,
        action: str,
    ) -> ServiceRequestAdminRead:
        """상태 전이 시행 (관리자 버전 — 소유권 검사 없음, MATCHED 취소 허용).

        허용: cancel(OPEN→CANCELLED, MATCHED→CANCELLED), complete(MATCHED→COMPLETED).
        그 외: 409 InvalidStatusTransitionError.
        """
        request = await self.repo.get_by_id_any(request_id)
        if request is None:
            raise ServiceRequestNotFoundError()

        if action == "cancel":
            if request.status not in (
                ServiceRequestStatus.OPEN,
                ServiceRequestStatus.MATCHED,
            ):
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
        return ServiceRequestAdminRead.model_validate(result)

    async def hide_request(self, request_id: UUID) -> ServiceRequestAdminRead:
        """서비스 요청 숨김 처리 (deleted_at 설정). 이미 숨김 처리된 경우 멱등 200.

        status는 변경하지 않는다. 연결된 quotes·chat_rooms·messages는 보존.
        """
        request = await self.repo.get_by_id_any(request_id)
        if request is None:
            raise ServiceRequestNotFoundError()
        if request.deleted_at is None:
            request.deleted_at = datetime.now(timezone.utc)
            await self.repo.save(request)
            await self.session.commit()
        return ServiceRequestAdminRead.model_validate(request)
