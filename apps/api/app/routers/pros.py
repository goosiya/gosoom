"""pros 라우터 — /api/v1/pros (Story 3.1).

require_role(PRO): CUSTOMER·ADMIN 포함 PRO 외 모든 역할 403 거부.
user_id는 current_user.id에서 주입 — 경로·바디 미수용(IDOR 방지).
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps import CurrentUser, require_role
from app.models.user import UserRole
from app.schemas.pro_category import ProCategoriesRead, ProCategoriesUpdate
from app.services.pro_category import ProCategoryService

router = APIRouter(prefix="/api/v1/pros", tags=["pros"])


@router.get("/me/categories", response_model=ProCategoriesRead)
async def get_pro_categories(
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
) -> ProCategoriesRead:
    svc = ProCategoryService(session)
    return await svc.get_my_categories(current_user)


@router.put("/me/categories", response_model=ProCategoriesRead)
async def set_pro_categories(
    body: ProCategoriesUpdate,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
) -> ProCategoriesRead:
    svc = ProCategoryService(session)
    return await svc.set_my_categories(body.category_ids, current_user)
