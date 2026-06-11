"""ProCategoryService — 고수 활동 카테고리 비즈니스 로직 (Story 3.1).

규칙:
- 제공된 categoryIds 전체 유효성 검증(비활성·미존재 포함 시 InvalidCategoryIdsError).
- replace semantics: DELETE+INSERT 단일 트랜잭션.
- user_id는 current_user.id 직접 사용(IDOR 방지 — 경로 파라미터나 바디 미수용).
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCategoryIdsError
from app.models.user import User
from app.repositories.categories import CategoryRepository
from app.repositories.pro_categories import ProCategoryRepository
from app.schemas.pro_category import ProCategoriesRead


class ProCategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProCategoryRepository(session)
        self.cat_repo = CategoryRepository(session)

    async def get_my_categories(self, current_user: User) -> ProCategoriesRead:
        rows = await self.repo.list_by_user(current_user.id)
        return ProCategoriesRead(category_ids=[r.category_id for r in rows])

    async def set_my_categories(
        self, category_ids: list[uuid.UUID], current_user: User
    ) -> ProCategoriesRead:
        # 중복 제거 (dict.fromkeys로 순서 보존)
        category_ids = list(dict.fromkeys(category_ids))
        # 빈 배열이면 유효성 검증 건너뜀(전체 삭제 허용)
        if category_ids:
            for cat_id in category_ids:
                cat = await self.cat_repo.get_by_id(cat_id)
                if cat is None:
                    raise InvalidCategoryIdsError()
        rows = await self.repo.replace(current_user.id, category_ids)
        await self.session.commit()
        return ProCategoriesRead(category_ids=[r.category_id for r in rows])
