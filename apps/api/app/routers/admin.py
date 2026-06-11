"""admin 라우터 — 관리자 콘솔 전용 엔드포인트 (Story 6.2~6.6).

모든 엔드포인트에 require_role(UserRole.ADMIN) 적용.
비즈니스 로직은 AdminUserService가 소유.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps import require_role
from app.models.user import UserRole
from app.schemas.auth import AdminCreateRequest, UserRead
from app.schemas.category import CategoryAdminRead, CategoryCreate, CategoryUpdate
from app.schemas.chat_room import ChatRoomAdminRead
from app.schemas.message import MessagePageResponse
from app.schemas.pagination import Page
from app.schemas.service_request import ServiceRequestAdminRead, ServiceRequestStatusUpdate
from app.services.admin import AdminCategoryService, AdminChatService, AdminServiceRequestService, AdminUserService

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


@router.get("/users", response_model=Page[UserRead])
async def list_admin_users(
    role: UserRole = Query(..., description="customer 또는 pro (admin 불허 — 관리자 목록은 GET /admins 사용)"),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Page[UserRead]:
    return await AdminUserService(db).list_users(role, cursor, limit)


@router.get("/users/{user_id}", response_model=UserRead)
async def get_admin_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    return await AdminUserService(db).get_user(user_id)


@router.post("/users/{user_id}/deactivate", response_model=UserRead)
async def deactivate_admin_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    return await AdminUserService(db).deactivate_user(user_id)


@router.post("/users/{user_id}/activate", response_model=UserRead)
async def activate_admin_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    return await AdminUserService(db).activate_user(user_id)


@router.get("/admins", response_model=Page[UserRead])
async def list_admins(
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Page[UserRead]:
    return await AdminUserService(db).list_admins(cursor, limit)


@router.post("/admins", response_model=UserRead, status_code=201)
async def create_admin(
    data: AdminCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    return await AdminUserService(db).create_admin(data)


@router.post("/admins/{admin_id}/deactivate", response_model=UserRead)
async def deactivate_admin(
    admin_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    return await AdminUserService(db).deactivate_admin(admin_id)


@router.get("/service-requests", response_model=Page[ServiceRequestAdminRead])
async def list_admin_service_requests(
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    include_hidden: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> Page[ServiceRequestAdminRead]:
    return await AdminServiceRequestService(db).list_requests(cursor, limit, include_hidden)


@router.post("/service-requests/{request_id}/change-status", response_model=ServiceRequestAdminRead)
async def admin_change_service_request_status(
    request_id: UUID,
    data: ServiceRequestStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> ServiceRequestAdminRead:
    return await AdminServiceRequestService(db).change_status(request_id, data.action)


@router.post("/service-requests/{request_id}/hide", response_model=ServiceRequestAdminRead)
async def admin_hide_service_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ServiceRequestAdminRead:
    return await AdminServiceRequestService(db).hide_request(request_id)


@router.get("/chat-rooms", response_model=Page[ChatRoomAdminRead])
async def list_admin_chat_rooms(
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Page[ChatRoomAdminRead]:
    return await AdminChatService(db).list_chat_rooms(cursor, limit)


@router.get("/chat-rooms/{chat_room_id}", response_model=ChatRoomAdminRead)
async def get_admin_chat_room(
    chat_room_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChatRoomAdminRead:
    return await AdminChatService(db).get_chat_room(chat_room_id)


@router.get("/chat-rooms/{chat_room_id}/messages", response_model=MessagePageResponse)
async def list_admin_chat_messages(
    chat_room_id: UUID,
    before: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> MessagePageResponse:
    return await AdminChatService(db).list_messages(chat_room_id, before, limit)


@router.get("/categories", response_model=Page[CategoryAdminRead])
async def list_admin_categories(
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Page[CategoryAdminRead]:
    return await AdminCategoryService(db).list_categories(cursor, limit)


@router.post("/categories", response_model=CategoryAdminRead, status_code=201)
async def create_admin_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
) -> CategoryAdminRead:
    return await AdminCategoryService(db).create_category(data)


@router.patch("/categories/{category_id}", response_model=CategoryAdminRead)
async def update_admin_category(
    category_id: UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
) -> CategoryAdminRead:
    return await AdminCategoryService(db).update_category(category_id, data)


@router.post("/categories/{category_id}/deactivate", response_model=CategoryAdminRead)
async def deactivate_admin_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CategoryAdminRead:
    return await AdminCategoryService(db).deactivate_category(category_id)
