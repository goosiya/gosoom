"""ServiceRequest 라우터 — /api/v1/service-requests (Story 2.1, 2.2).

require_role(CUSTOMER): PRO·ADMIN 포함 CUSTOMER 외 모든 역할 403 거부 (의도적).
customer_id는 current_user.id에서 주입 — 요청 바디 미수용(IDOR 방지).

라우터 등록 순서 유의: FastAPI는 순서대로 매칭 → 고정 경로(GET /) 먼저, 동적 경로(GET /{id}) 나중.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps import CurrentUser, require_role
from app.models.user import UserRole
from app.schemas.pagination import Page
from app.schemas.service_request import ServiceRequestCreate, ServiceRequestRead, ServiceRequestStatusUpdate
from app.services.service_request import ServiceRequestService

router = APIRouter(prefix="/api/v1/service-requests", tags=["service-requests"])


@router.post("/", response_model=ServiceRequestRead, status_code=201)
async def create_service_request(
    body: ServiceRequestCreate,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
) -> ServiceRequestRead:
    svc = ServiceRequestService(session)
    result = await svc.create(body, current_user)
    return result


@router.get("/", response_model=Page[ServiceRequestRead])
async def list_my_service_requests(
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Page[ServiceRequestRead]:
    svc = ServiceRequestService(session)
    return await svc.list_mine(current_user, cursor, limit)


@router.get("/feed", response_model=Page[ServiceRequestRead])
async def list_service_request_feed(
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Page[ServiceRequestRead]:
    svc = ServiceRequestService(session)
    return await svc.get_feed(current_user, cursor, limit)


@router.get("/feed/{request_id}", response_model=ServiceRequestRead)
async def get_service_request_feed_detail(
    request_id: uuid.UUID,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
) -> ServiceRequestRead:
    svc = ServiceRequestService(session)
    return await svc.get_feed_detail(request_id, current_user)


@router.get("/{request_id}", response_model=ServiceRequestRead)
async def get_service_request(
    request_id: uuid.UUID,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
) -> ServiceRequestRead:
    svc = ServiceRequestService(session)
    result = await svc.get_detail(request_id, current_user)
    return result


@router.patch("/{request_id}", response_model=ServiceRequestRead)
async def update_service_request_status(
    request_id: uuid.UUID,
    body: ServiceRequestStatusUpdate,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
) -> ServiceRequestRead:
    svc = ServiceRequestService(session)
    result = await svc.change_status(request_id, body.action, current_user)
    return result
