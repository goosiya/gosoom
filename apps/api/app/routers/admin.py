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
from app.schemas.pagination import Page
from app.services.admin import AdminUserService

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
