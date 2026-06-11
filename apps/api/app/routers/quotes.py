"""Quote 라우터 — 두 독립 네임스페이스를 별개 서브라우터로 분리.

- POST /api/v1/service-requests/{request_id}/quotes : 견적 제안 (Story 3.3)
- GET  /api/v1/quotes                              : 내 견적 목록 조회 (Story 3.4)

prefix가 다른 두 경로를 하나의 넓은 /api/v1 prefix로 묶는 대신, 각자의
네임스페이스를 가진 서브라우터(_sr_router, _q_router)로 분리해 관리한다.
main.py는 기존과 동일하게 단일 `router`만 include한다.

보안 규칙:
- require_role(PRO): CUSTOMER·ADMIN 403 거부 (의도적).
- service_request_id/pro_id는 current_user.id에서 주입 — 요청 바디 미수용(IDOR 방지).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps import CurrentUser, require_role
from app.models.user import UserRole
from app.schemas.chat_room import ChatRoomRead
from app.schemas.pagination import Page
from app.schemas.quote import QuoteCreate, QuoteListItem, QuoteRead, QuoteWithProInfo
from app.services.quote import QuoteService

# 서브라우터 1: /api/v1/service-requests 네임스페이스 (견적 제안)
_sr_router = APIRouter(prefix="/api/v1/service-requests", tags=["quotes"])


@_sr_router.post("/{request_id}/quotes", response_model=QuoteRead, status_code=201)
async def create_service_request_quote(
    request_id: uuid.UUID,
    body: QuoteCreate,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
) -> QuoteRead:
    svc = QuoteService(session)
    return await svc.submit(request_id, body, current_user)


@_sr_router.get("/{request_id}/quotes", response_model=Page[QuoteWithProInfo])
async def list_service_request_quotes(
    request_id: uuid.UUID,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Page[QuoteWithProInfo]:
    svc = QuoteService(session)
    return await svc.list_for_request(request_id, current_user, cursor, limit)


# 서브라우터 2: /api/v1/quotes 네임스페이스 (내 견적 목록)
_q_router = APIRouter(prefix="/api/v1/quotes", tags=["quotes"])


@_q_router.get("", response_model=Page[QuoteListItem])
async def list_my_quotes(
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Page[QuoteListItem]:
    svc = QuoteService(session)
    return await svc.list_mine(current_user, cursor, limit)


@_q_router.post("/{quote_id}/accept", response_model=ChatRoomRead, status_code=200)
async def accept_quote(
    quote_id: uuid.UUID,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
) -> ChatRoomRead:
    svc = QuoteService(session)
    return await svc.accept(quote_id, current_user)


@_q_router.post("/{quote_id}/reject", response_model=QuoteRead, status_code=200)
async def reject_quote(
    quote_id: uuid.UUID,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
) -> QuoteRead:
    svc = QuoteService(session)
    return await svc.reject(quote_id, current_user)


# main.py가 include하는 단일 진입점 — 내부적으로 두 서브라우터를 포함
router = APIRouter()
router.include_router(_sr_router)
router.include_router(_q_router)
