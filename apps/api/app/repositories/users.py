"""UserRepository — users 테이블 DB 접근(첫 도메인 repository).

규약(architecture#Structure Patterns):
- 조회는 소프트삭제 공통 필터 `deleted_at IS NULL` 적용.
- 트랜잭션(commit)은 소유하지 않는다 — service가 commit/rollback을 관리. 여기선 flush까지만.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """users 테이블 CRUD 경계."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        """이메일로 활성(미삭제) 사용자 조회. 없으면 None.

        이메일은 소문자로 정규화해 조회 — 저장도 동일 정규화(SignupRequest/seed)되므로
        모든 호출자(service·seed)가 대소문자 무관하게 일관된 결과를 얻는다.
        """
        normalized = email.strip().lower()
        result = await self.session.execute(
            select(User).where(User.email == normalized, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """ID로 활성(미삭제) 사용자 조회. 없으면 None.

        refresh가 토큰의 user_id로 현재 사용자 상태(is_active/user_role)를 재조회하는 데 사용.
        `deleted_at IS NULL` 공통 필터 유지 — 삭제된 계정이 토큰으로 부활하지 못하게 한다.
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_by_ids(self, ids: list[UUID]) -> list[User]:
        """UUID 목록으로 미삭제 사용자 batch 조회."""
        if not ids:
            return []
        result = await self.session.execute(
            select(User).where(
                User.id.in_(ids),
                User.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def create(self, user: User) -> User:
        """사용자 추가 후 flush/refresh로 DB 생성값(타임스탬프 등) 반영. commit은 service가 수행."""
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user
