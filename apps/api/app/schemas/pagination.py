"""목록 응답 단일 형식(`{items, nextCursor}`)과 opaque cursor 규약의 단일 소스(Story 1.6).

Epic 2(요청)·3(견적)·4(채팅)·6(관리자)의 모든 목록 엔드포인트가 이 `Page`를 재사용한다.
**단, keyset 쿼리 자체는 각 도메인이 자신의 정렬(예: createdAt DESC)로 작성한다** —
`Page`는 envelope+규약만 제공하고 컬럼/방향을 일반화하지 않는다(결정 사항 #1).
재사용 자산은 ① 이 `Page` envelope, ② cursor가 opaque 문자열이라는 규약(core/pagination.py)뿐이다.
"""

from typing import Generic, TypeVar

from app.schemas.base import CamelModel

T = TypeVar("T")


class Page(CamelModel, Generic[T]):
    """cursor 페이지네이션 응답 envelope.

    직렬화 경계는 `{items, nextCursor}`(CamelModel alias). `next_cursor`는 opaque 문자열 또는
    null — 클라이언트는 내부 구조를 해석하지 않는다(architecture#Format Patterns line 297 정합).
    FastAPI `response_model=Page[CategoryRead]` 사용 시 OpenAPI 스키마명 `Page_CategoryRead_`가
    자동 생성된다(Orval 소비는 1.7).
    """

    items: list[T]
    next_cursor: str | None = None
