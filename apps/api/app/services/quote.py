"""QuoteService — 견적 비즈니스 로직 (Story 3.3/3.4).

보안 규칙:
- service_request_id/pro_id는 서버에서만 설정(IDOR 방지).
- status는 PENDING으로 고정(변조 방지).
- 카테고리 일치 검사: PRO가 해당 카테고리의 요청에만 견적 가능(FR10/FR11).
- 중복 견적 검사: service 단 사전 검증 + DB UniqueConstraint는 last-resort.
"""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DuplicateQuoteError,
    ForbiddenError,
    InvalidCursorError,
    QuoteNotFoundError,
    QuoteNotPendingError,
    ServiceRequestAlreadyMatchedError,
    ServiceRequestNotFoundError,
    ServiceRequestNotOpenForQuoteError,
)
from app.core.pagination import decode_cursor, encode_cursor
from app.models.chat_room import ChatRoom
from app.models.quote import Quote, QuoteStatus
from app.models.service_request import ServiceRequest, ServiceRequestStatus
from app.models.user import User
from app.repositories.chat_rooms import ChatRoomRepository
from app.repositories.pro_categories import ProCategoryRepository
from app.repositories.quotes import QuoteRepository
from app.repositories.service_requests import ServiceRequestRepository
from app.repositories.users import UserRepository
from app.schemas.pagination import Page
from app.schemas.quote import (
    ProInfoSummary,
    QuoteCreate,
    QuoteListItem,
    QuoteWithProInfo,
    ServiceRequestSummary,
)


class QuoteService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.quote_repo = QuoteRepository(session)
        self.sr_repo = ServiceRequestRepository(session)
        self.pro_cat_repo = ProCategoryRepository(session)

    async def submit(
        self, request_id: UUID, data: QuoteCreate, current_user: User
    ) -> Quote:
        # 1. 요청 존재 확인
        request = await self.sr_repo.get_by_id(request_id)
        if request is None:
            raise ServiceRequestNotFoundError()

        # 2. 요청 상태 OPEN 검사
        if request.status != ServiceRequestStatus.OPEN:
            raise ServiceRequestNotOpenForQuoteError()

        # 3. 카테고리 일치 검사 (set으로 O(1) 조회)
        pro_cats = await self.pro_cat_repo.list_by_user(current_user.id)
        category_ids = {pc.category_id for pc in pro_cats}
        if request.category_id not in category_ids:
            raise ForbiddenError()

        # 4. 중복 견적 검사
        existing = await self.quote_repo.get_by_request_and_pro(request_id, current_user.id)
        if existing is not None:
            raise DuplicateQuoteError()

        # 5. 견적 생성 — IntegrityError는 레이스 컨디션(동시 요청) 중복으로 처리
        new_quote = Quote(
            service_request_id=request_id,
            pro_id=current_user.id,
            price=data.price,
            message=data.message,
            status=QuoteStatus.PENDING,
        )
        try:
            result = await self.quote_repo.create(new_quote)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise DuplicateQuoteError()
        return result

    async def list_mine(
        self, current_user: User, cursor: str | None, limit: int
    ) -> Page[QuoteListItem]:
        """PRO 본인 견적 목록을 id DESC keyset cursor 페이지네이션으로 반환 (Story 3.4)."""
        limit = max(1, limit)
        after_id: UUID | None = None
        if cursor is not None:
            decoded = decode_cursor(cursor)
            try:
                after_id = UUID(decoded)
            except (ValueError, AttributeError, TypeError) as exc:
                raise InvalidCursorError() from exc

        rows = await self.quote_repo.list_by_pro(current_user.id, after_id, limit + 1)
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = encode_cursor(str(page_rows[-1].id)) if has_more else None

        # 대상 요청 batch 조회 (두 쿼리 방식 — relationship 없음)
        request_ids = [r.service_request_id for r in page_rows]
        request_map: dict[UUID, ServiceRequest] = {}
        if request_ids:
            sr_rows = await self.sr_repo.list_by_ids(request_ids)
            request_map = {r.id: r for r in sr_rows}

        items = []
        for q in page_rows:
            sr = request_map.get(q.service_request_id)
            items.append(
                QuoteListItem(
                    id=q.id,
                    service_request_id=q.service_request_id,
                    price=q.price,
                    message=q.message,
                    status=q.status,
                    created_at=q.created_at,
                    updated_at=q.updated_at,
                    service_request=ServiceRequestSummary.model_validate(sr) if sr else None,
                )
            )

        return Page[QuoteListItem](items=items, next_cursor=next_cursor)

    async def list_for_request(
        self, request_id: UUID, current_user: User, cursor: str | None, limit: int
    ) -> "Page[QuoteWithProInfo]":
        """고객 본인의 서비스 요청에 들어온 견적 목록을 id DESC keyset cursor로 반환 (Story 4.1)."""
        # 1. 요청 존재 + 소유권 검사
        request = await self.sr_repo.get_by_id(request_id)
        if request is None:
            raise ServiceRequestNotFoundError()
        if request.customer_id != current_user.id:
            raise ForbiddenError()

        # 2. cursor 디코드 — "{request_id}:{quote_id}" 형식으로 scope 검증
        limit = max(1, limit)
        after_id: UUID | None = None
        if cursor is not None:
            decoded = decode_cursor(cursor)
            try:
                scope, raw_id = decoded.split(":", 1)
                if scope != str(request_id):
                    raise ValueError("cursor scope mismatch")
                after_id = UUID(raw_id)
            except (ValueError, AttributeError, TypeError) as exc:
                raise InvalidCursorError() from exc

        # 3. 견적 목록 (keyset)
        rows = await self.quote_repo.list_by_request(request_id, after_id, limit + 1)
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = encode_cursor(f"{request_id}:{page_rows[-1].id}") if has_more else None

        # 4. PRO 사용자 batch 조회
        pro_ids = list({q.pro_id for q in page_rows})
        user_repo = UserRepository(self.session)
        users = await user_repo.list_by_ids(pro_ids)
        user_map: dict[UUID, User] = {u.id: u for u in users}

        # 5. PRO 카테고리 batch 조회
        pro_cats = await self.pro_cat_repo.list_by_users(pro_ids)
        cat_map: dict[UUID, list[UUID]] = {}
        for pc in pro_cats:
            cat_map.setdefault(pc.user_id, []).append(pc.category_id)

        # 6. 조립
        items = [
            QuoteWithProInfo(
                id=q.id,
                pro_id=q.pro_id,
                price=q.price,
                message=q.message,
                status=q.status,
                created_at=q.created_at,
                updated_at=q.updated_at,
                pro=ProInfoSummary(
                    id=q.pro_id,
                    display_name=user_map[q.pro_id].display_name if q.pro_id in user_map else "알 수 없음",
                    category_ids=cat_map.get(q.pro_id, []),
                ),
            )
            for q in page_rows
        ]
        return Page[QuoteWithProInfo](items=items, next_cursor=next_cursor)

    async def accept(self, quote_id: UUID, current_user: User) -> ChatRoom:
        """견적 수락 — 단일 트랜잭션 원자적 처리 (AC1, AR7, FR13).

        순서:
        1. 견적 존재 확인
        2. 서비스 요청 행 비관적 잠금 (SELECT FOR UPDATE) — race 차단
        3. 소유권 검사 (본인 요청의 견적만)
        4. 요청 상태 OPEN 검사
        5. 견적 상태 PENDING 검사
        6. 요청 → matched
        7. 채팅방 생성
        8. 수락 견적 → accepted
        9. 나머지 pending 견적 → closed (bulk)
        10. flush → partial unique index 검증 → commit
        """
        # 1. 견적 존재 확인
        quote = await self.quote_repo.get_by_id(quote_id)
        if quote is None:
            raise QuoteNotFoundError()

        # 2. 서비스 요청 행 잠금 (SELECT ... FOR UPDATE) — race 차단
        request = await self.sr_repo.get_by_id_for_update(quote.service_request_id)
        if request is None:
            raise ServiceRequestNotFoundError()

        # 3. 소유권 검사
        if request.customer_id != current_user.id:
            raise ForbiddenError()

        # 4. 요청 상태 검사
        if request.status != ServiceRequestStatus.OPEN:
            raise ServiceRequestAlreadyMatchedError()

        # 5. 견적 상태 검사
        if quote.status != QuoteStatus.PENDING:
            raise QuoteNotPendingError()

        # 6. 요청 → matched
        request.status = ServiceRequestStatus.MATCHED

        # 7. 채팅방 생성
        chat_room = ChatRoom(
            service_request_id=quote.service_request_id,
            customer_id=request.customer_id,
            pro_id=quote.pro_id,
            quote_id=quote.id,
        )

        # 8. 수락 견적 → accepted
        quote.status = QuoteStatus.ACCEPTED

        # 9. 나머지 pending 견적 → closed (bulk, flush 전에 실행)
        await self.quote_repo.close_pending_except(quote.service_request_id, quote.id)

        # 10. flush → partial unique index 검증 (concurrent accept 차단) → commit
        chat_room_repo = ChatRoomRepository(self.session)
        try:
            await chat_room_repo.create(chat_room)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ServiceRequestAlreadyMatchedError()

        return chat_room

    async def reject(self, quote_id: UUID, current_user: User) -> Quote:
        """견적 거절 — 단일 견적 상태 전이 (AC1, FR14).

        순서:
        1. 견적 존재 확인
        2. 서비스 요청 조회 (소유권 확인용 — FOR UPDATE 불필요)
        3. 소유권 검사 (본인 요청의 견적만)
        4. 견적 상태 PENDING 검사
        5. 거절 처리 → commit → refresh
        """
        # 1. 견적 존재 확인
        quote = await self.quote_repo.get_by_id(quote_id)
        if quote is None:
            raise QuoteNotFoundError()

        # 2. 서비스 요청 조회 (소유권 확인용)
        request = await self.sr_repo.get_by_id(quote.service_request_id)
        if request is None:
            raise ServiceRequestNotFoundError()

        # 3. 소유권 검사 — 본인 요청의 견적만 거절 가능
        if request.customer_id != current_user.id:
            raise ForbiddenError()

        # 4. 견적 상태 검사 — pending만 거절 가능
        if quote.status != QuoteStatus.PENDING:
            raise QuoteNotPendingError()

        # 5. 거절 처리
        quote.status = QuoteStatus.REJECTED
        await self.session.commit()
        await self.session.refresh(quote)
        return quote
