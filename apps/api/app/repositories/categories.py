"""CategoryRepository — categories 테이블 DB 접근(Story 1.6).

규약(architecture#Structure Patterns, UserRepository 패턴 복제):
- 조회는 소프트삭제 공통 필터 `deleted_at IS NULL` 적용.
- 활성 목록은 추가로 `is_active=true` 필터 — 카테고리는 비활성도 목록에서 제외(AC1).
  ⚠️ UserRepository(deleted_at만 필터, is_active는 get_current_user가 검사)와 다르다.
- 트랜잭션(commit)은 소유하지 않는다 — 호출측(service/seed)이 관리. 여기선 flush까지만.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


class CategoryRepository:
    """categories 테이블 조회 경계."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self, after_id: UUID | None, limit: int) -> list[Category]:
        """활성·미삭제 카테고리를 id(UUIDv7) 오름차순 keyset으로 조회.

        is_active=true AND deleted_at IS NULL을 **둘 다** 필터(AC1). after_id가 있으면
        그 id 이후(이전 페이지 마지막 다음)부터. PG `uuid` 비교는 바이트순 = UUIDv7 시간순이라
        불변 시간정렬 키로 안전하다(name은 Epic 6에서 수정 가능 → keyset 경계로 부적합).
        호출측이 limit+1로 요청해 "다음 페이지 존재"를 판정한다.
        """
        stmt = select(Category).where(
            Category.is_active.is_(True), Category.deleted_at.is_(None)
        )
        if after_id is not None:
            stmt = stmt.where(Category.id > after_id)
        stmt = stmt.order_by(Category.id).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_name(self, name: str) -> Category | None:
        """이름으로 미삭제 카테고리 조회(시드 멱등성 선검사용). 없으면 None.

        정규화는 단순 strip만 — 이메일과 달리 소문자화하지 않는다(한국어 카테고리명).
        """
        normalized = name.strip()
        result = await self.session.execute(
            select(Category).where(
                Category.name == normalized, Category.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, id: UUID) -> Category | None:
        """id로 활성·미삭제 카테고리 조회. 비활성(is_active=False)도 None 반환(AC2 not found 처리)."""
        result = await self.session.execute(
            select(Category).where(
                Category.id == id,
                Category.deleted_at.is_(None),
                Category.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, category: Category) -> Category:
        """카테고리 추가 후 flush/refresh로 DB 생성값(타임스탬프 등) 반영. commit은 호출측."""
        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def get_by_id_any(self, id: UUID) -> Category | None:
        """관리자용: is_active 무관, 미삭제 카테고리 단건 조회 (Story 6.6)."""
        result = await self.session.execute(
            select(Category).where(Category.id == id, Category.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_all(self, after_id: UUID | None, limit: int) -> list[Category]:
        """관리자용: 활성·비활성 모두 포함, 미삭제, id ASC cursor (Story 6.6, AC5)."""
        stmt = select(Category).where(Category.deleted_at.is_(None))
        if after_id is not None:
            stmt = stmt.where(Category.id > after_id)
        stmt = stmt.order_by(Category.id).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def save(self, category: Category) -> Category:
        """수정 후 flush/refresh. commit은 호출측 (UserRepository.save 패턴 복제)."""
        await self.session.flush()
        await self.session.refresh(category)
        return category
