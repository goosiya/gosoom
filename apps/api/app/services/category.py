"""CategoryService — 카테고리 조회 비즈니스 로직(Story 1.6).

규약(architecture#Structure Patterns):
- service는 비즈니스 로직(cursor 페이지네이션)만. 권한은 읽기 전용·소유권 무관(참조 데이터)이라
  ensure_owner_or_admin 호출 없음 — 라우터 CurrentUser 인증만으로 충분.
- limit 검증은 라우터(Pydantic Query)에서 — service는 이미 검증된 limit을 받는다.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCursorError
from app.core.pagination import decode_cursor, encode_cursor
from app.repositories.categories import CategoryRepository
from app.schemas.category import CategoryRead
from app.schemas.pagination import Page


class CategoryService:
    """카테고리 도메인 서비스(조회 전용)."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = CategoryRepository(session)

    async def list_active(self, cursor: str | None, limit: int) -> Page[CategoryRead]:
        """활성 카테고리를 cursor 페이지네이션으로 조회(AC1/AC4).

        cursor 디코드 → keyset 경계 id로 변환. base64 유효하나 UUID가 아닌 cursor도
        InvalidCursorError(400)로 정규화(500 누수 방지). limit+1 패턴으로 다음 페이지 존재를
        판정하고, nextCursor는 잘린 마지막 항목(rows[:limit][-1])의 id를 인코딩한다.
        """
        # ① cursor 디코드(decode_cursor는 비-base64를 자체 처리). base64는 유효하나
        #    비-UUID인 cursor 방어를 위해 UUID 변환 실패도 InvalidCursorError로 변환.
        after_id: UUID | None = None
        if cursor is not None:
            decoded = decode_cursor(cursor)
            try:
                after_id = UUID(decoded)
            except (ValueError, AttributeError, TypeError) as exc:
                raise InvalidCursorError() from exc

        # ② limit+1로 조회해 "다음 페이지 존재" 판정.
        rows = await self.repo.list_active(after_id, limit + 1)

        # ③ has_more면 limit개로 자르고, ④ nextCursor는 잘린 마지막 항목 id(rows[-1] 아님!).
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = encode_cursor(str(page_rows[-1].id)) if has_more else None

        return Page[CategoryRead](
            items=[CategoryRead.model_validate(c) for c in page_rows],
            next_cursor=next_cursor,
        )
