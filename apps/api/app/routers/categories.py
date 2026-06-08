"""categories 라우터 — 활성 카테고리 조회(Story 1.6).

규약: router는 HTTP·검증·Depends만. 첫 목록(list) 엔드포인트 — `Page[CategoryRead]` envelope를
노출한다(operationId=`list_categories` 안정화, Orval 소비는 1.7).

인증: `CurrentUser`(인증만 요구, 모든 역할 허용) — `require_role` 미적용. AC 리터럴은 "고객·고수"이나
관리자(Epic 6 카테고리 관리)도 읽어야 하므로 admin을 배제하지 않는다(`/users/me`와 동일 패턴, 결정 #2).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps import CurrentUser
from app.schemas.category import CategoryRead
from app.schemas.pagination import Page
from app.services.category import CategoryService

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=Page[CategoryRead])
async def list_categories(
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Page[CategoryRead]:
    """활성 카테고리 목록을 `{items, nextCursor}`로 반환(AC1/AC3/AC4).

    인증만 필요(모든 역할 허용). 미인증/무효 토큰은 get_current_user가 401로 차단(1.5).
    손상 cursor는 service가 400 invalid_cursor로 정규화. limit 상한 100으로 과대 요청 차단.
    빈 경로(`""`)로 최종 경로 `/api/v1/categories`(trailing-slash 불일치 회피).
    """
    return await CategoryService(db).list_active(cursor, limit)
