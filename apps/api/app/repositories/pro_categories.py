"""ProCategoryRepository — pro_categories 테이블 DB 접근 (Story 3.1).

규약:
- 트랜잭션(commit)은 소유하지 않는다 — 호출측(service)이 관리.
- replace: 기존 행 DELETE + 신규 행 INSERT를 단일 flush에서 처리.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pro_category import ProCategory


class ProCategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(self, user_id: uuid.UUID) -> list[ProCategory]:
        result = await self.session.execute(
            select(ProCategory).where(ProCategory.user_id == user_id)
        )
        return list(result.scalars().all())

    async def list_by_users(self, user_ids: list[uuid.UUID]) -> list[ProCategory]:
        """여러 고수의 카테고리를 batch 조회."""
        if not user_ids:
            return []
        result = await self.session.execute(
            select(ProCategory).where(ProCategory.user_id.in_(user_ids))
        )
        return list(result.scalars().all())

    async def replace(self, user_id: uuid.UUID, category_ids: list[uuid.UUID]) -> list[ProCategory]:
        """고수의 카테고리를 완전 교체. 기존 삭제 → 신규 삽입 → flush."""
        await self.session.execute(
            delete(ProCategory).where(ProCategory.user_id == user_id)
        )
        new_rows = [
            ProCategory(user_id=user_id, category_id=cat_id)
            for cat_id in category_ids
        ]
        for row in new_rows:
            self.session.add(row)
        await self.session.flush()
        return new_rows
