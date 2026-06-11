---
baseline_commit: 8f838532fe9cd47150063589ab9c5327710562d3
---

# Story 3.3: 견적 제안

- **Status:** done
- **Epic:** 3 — 고수 카테고리 & 견적 (FR9-12)
- **Story ID / Key:** 3-3 / 3-3-submit-quote
- **작성일:** 2026-06-09

---

## 사용자 스토리

As a 로그인한 고수(PRO),  
open 상태의 요청에 가격과 제안 메시지를 담아 견적을 제안하고 싶다.  
So that 고객에게 나를 어필하고 거래로 이어갈 수 있다.

---

## 인수 기준 (BDD)

**AC1** — quotes 테이블 마이그레이션

- **Given** `quotes` 테이블(id UUIDv7, service_request_id FK→service_requests.id, pro_id FK→users.id, price 정수 KRW, message TEXT, status enum[pending|accepted|rejected|closed], created_at, updated_at, deleted_at)과 UNIQUE(service_request_id, pro_id) 제약이 마이그레이션될 때
- **When** `alembic upgrade head`를 실행하면
- **Then** 테이블·FK·유니크 제약·인덱스가 생성되고 멱등하게 재적용 가능하다

**AC2** — 견적 제안 성공: `POST /api/v1/service-requests/{id}/quotes`

- **Given** PRO가 자신의 활동 카테고리와 일치하는 `open` 요청에 대해
- **When** `POST /api/v1/service-requests/{id}/quotes`에 price·message를 보내면
- **Then** 견적이 `status=pending`으로 생성되고 `pro_id`는 현재 로그인 PRO의 id로 설정된다(FR11)
- **And** 응답은 201 + QuoteRead(id, serviceRequestId, proId, price, message, status, createdAt, updatedAt)를 반환한다

**AC3** — 중복 제안 방지 (요청당 PRO 1개 견적, FR11)

- **Given** 한 요청에 이미 본인 견적이 존재할 때
- **When** 같은 요청에 다시 `POST`를 시도하면
- **Then** 409 + `{code: "duplicate_quote"}` 반환 — DB 유니크 제약 + service 사전 검증

**AC4** — 요청 상태·카테고리 불일치 거부 (FR10/FR11)

- **Given** 요청이 `open`이 아닐 때(matched/completed/cancelled)
- **When** 견적 제안을 시도하면
- **Then** 409 + `{code: "service_request_not_open"}` 반환

- **Given** 요청의 카테고리가 PRO의 활동 카테고리에 없을 때
- **When** 견적 제안을 시도하면
- **Then** 403 + `{code: "forbidden"}` 반환

**AC5** — 권한 제어 (FR4)

- **Given** 각 역할/인증 상태에서 요청 시
- **Then** 비인증 → 401 `not_authenticated`, CUSTOMER 역할 → 403 `forbidden`, ADMIN 역할 → 403 `forbidden`

**AC6** — user-web `(pro)/feed/[id]` 견적 제안 화면

- **Given** user-web `(pro)/feed/[id]` 상세 화면에서 open 요청을 볼 때
- **When** 고수가 가격(정수 KRW)과 제안 메시지를 입력해 제출하면
- **Then** Orval 훅(`useCreateServiceRequestQuote`)으로 견적이 생성되고 성공 피드백(버튼 비활성화 + "견적이 제출되었습니다" 메시지)이 표시된다
- **And** 이미 견적을 제출한 경우 폼 대신 "이미 견적을 제출했습니다" 메시지가 표시된다(AC3 UX 대응)
- **And** matched 요청에는 견적 폼이 렌더링되지 않는다

---

## 태스크 및 서브태스크

- [x] **Task 1:** `quotes` 테이블 Alembic 마이그레이션
  - [x] `apps/api/app/models/quote.py` 생성 — `QuoteStatus` enum + `Quote` ORM 모델
  - [x] `alembic revision --autogenerate -m "add_quotes_table"` 실행 후 검수
  - [x] downgrade에 Enum 타입 명시 삭제 추가 (service_request 마이그레이션 패턴 동일)

- [x] **Task 2:** Pydantic 스키마 생성
  - [x] `apps/api/app/schemas/quote.py` 생성 — `QuoteCreate`(price, message), `QuoteRead`(전 필드)

- [x] **Task 3:** `QuoteRepository` 생성
  - [x] `apps/api/app/repositories/quotes.py` 생성
  - [x] `create()`, `get_by_id()`, `get_by_request_and_pro()` 메서드

- [x] **Task 4:** `QuoteService.submit()` 구현
  - [x] `apps/api/app/services/quote.py` 생성
  - [x] 순서: 요청 존재(404) → 요청 상태 OPEN 검사(409) → 카테고리 일치 검사(403) → 중복 견적 검사(409) → 생성

- [x] **Task 5:** 신규 예외 추가
  - [x] `apps/api/app/core/exceptions.py`에 `DuplicateQuoteError`, `ServiceRequestNotOpenForQuoteError` 추가

- [x] **Task 6:** 라우터 생성 + main.py 등록
  - [x] `apps/api/app/routers/quotes.py` 생성 — `POST /api/v1/service-requests/{request_id}/quotes`
  - [x] `apps/api/app/main.py`에 `quotes_router` import 및 `app.include_router(quotes_router)` 추가

- [x] **Task 7:** `models/__init__.py` 업데이트
  - [x] `Quote`, `QuoteStatus` import 추가 (Alembic autogenerate가 모델 감지하려면 필수)

- [x] **Task 8:** pytest 작성 (`apps/api/tests/test_quotes_submit.py`)
  - [x] AC2 성공: 201, status=pending, proId=현재 PRO, 필드 검증
  - [x] AC3 중복 제안: 409 duplicate_quote
  - [x] AC4 요청 not open (matched, cancelled 각각): 409 service_request_not_open
  - [x] AC4 카테고리 불일치: 403 forbidden
  - [x] AC5 비인증 401, CUSTOMER 403, ADMIN 403
  - [x] 존재하지 않는 request_id: 404 service_request_not_found
  - [x] price 음수: 422, message 빈 문자열: 422
  - [x] price=0 허용: 201

- [x] **Task 9:** user-web 견적 제안 폼 구현
  - [x] `apps/user-web/src/app/(pro)/feed/[id]/page.tsx` 수정
  - [x] 기존 disabled 버튼 → 실제 price+message 폼으로 교체
  - [x] Orval 훅 `useCreateServiceRequestQuote` 사용, 성공/에러 상태 처리

- [x] **Task 10:** Orval 재생성 + api-client index 업데이트
  - [x] API 서버 기동 후 `pnpm orval` 실행
  - [x] `useCreateServiceRequestQuote` 훅 생성 확인
  - [x] `QuoteRead`, `QuoteCreate` 타입 생성 확인

### Review Findings

- [x] [Review][Patch] UniqueConstraint를 partial index로 교체 — WHERE deleted_at IS NULL (재제안 허용 설계 반영) [apps/api/app/models/quote.py:26, alembic/d7bffeb07473:36]
- [x] [Review][Patch] AC6: 페이지 재방문 시 기존 견적 서버 조회 → "이미 견적을 제출했습니다" 표시 [apps/user-web/src/app/(pro)/feed/[id]/page.tsx]
- [x] [Review][Patch] AC6: 성공 후 버튼 비활성화+메시지 동시 표시 (폼 언마운트 대신) [apps/user-web/src/app/(pro)/feed/[id]/page.tsx:74]
- [x] [Review][Patch] quotes FK에 ON DELETE CASCADE 누락 (프로젝트 표준 위반) [apps/api/alembic/versions/d7bffeb07473_add_quotes_table.py:33-34, apps/api/app/models/quote.py:31-35]
- [x] [Review][Patch] 동시 요청 레이스 컨디션 → IntegrityError → 500 미처리 [apps/api/app/services/quote.py:54-57]
- [x] [Review][Patch] price 상한 없음 — DB Integer overflow 시 500 [apps/api/app/schemas/quote.py:17]
- [x] [Review][Patch] message 최대 길이 없음 — 대용량 페이로드 허용 [apps/api/app/schemas/quote.py:18]
- [x] [Review][Defer] 서비스 레이어 역할 미재검증 [apps/api/app/services/quote.py] — deferred, pre-existing (전체 아키텍처 패턴)
- [x] [Review][Defer] 프론트 에러 메시지 원시 노출 [apps/user-web/src/app/(pro)/feed/[id]/page.tsx:104] — deferred, pre-existing (api-client 인터셉터 설계 관련)
- [x] [Review][Defer] status cancelled 등 UI 안내 없음 [apps/user-web/src/app/(pro)/feed/[id]/page.tsx] — deferred, pre-existing (UX 개선, 스코프 밖)
- [x] [Review][Defer] 프론트 더블 제출 — 서버 409로 보호됨 [apps/user-web/src/app/(pro)/feed/[id]/page.tsx] — deferred, pre-existing
- [x] [Review][Defer] downgrade checkfirst=False 멱등성 미보장 [alembic/versions/d7bffeb07473:48] — deferred, pre-existing (전체 프로젝트 일괄 교체 예정)

---

## 개발자 노트

### 핵심 설계 결정

#### 1. quotes 라우터 — prefix 전략

`routers/quotes.py`는 prefix=`/api/v1/service-requests`로 생성한다. Story 3.3의 유일한 엔드포인트 `POST /{request_id}/quotes`가 서비스 요청에 중첩된 URL이기 때문이다. `main.py`에 `service_requests_router`와 별개로 `quotes_router`를 등록한다. FastAPI는 동일 prefix 라우터 중복 등록을 허용한다.

Story 3.4에서 `GET /api/v1/quotes?mine=true` 추가 시 quotes_router에 두 번째 엔드포인트를 추가하거나 prefix를 `/api/v1`로 변경 후 `service-requests/{id}/quotes`와 `quotes/` 두 경로를 모두 처리하면 된다.

```python
# routers/quotes.py
router = APIRouter(prefix="/api/v1/service-requests", tags=["quotes"])

@router.post("/{request_id}/quotes", response_model=QuoteRead, status_code=201)
async def create_service_request_quote(
    request_id: uuid.UUID,
    body: QuoteCreate,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
) -> QuoteRead:
    svc = QuoteService(session)
    return await svc.submit(request_id, body, current_user)
```

**Orval operationId**: 함수명 `create_service_request_quote` → `createServiceRequestQuote` → 훅 이름 `useCreateServiceRequestQuote`.

#### 2. 서비스 로직 순서 (QuoteService.submit)

순서가 중요하다. 잘못된 순서는 503 서비스 오류나 정보 노출을 유발한다.

```python
async def submit(self, request_id: UUID, data: QuoteCreate, current_user: User) -> Quote:
    # 1. 요청 존재 확인 (deleted_at IS NULL 포함)
    request = await self.sr_repo.get_by_id(request_id)
    if request is None:
        raise ServiceRequestNotFoundError()
    
    # 2. 요청 상태 OPEN 검사 — matched/completed/cancelled 모두 거부
    if request.status != ServiceRequestStatus.OPEN:
        raise ServiceRequestNotOpenForQuoteError()
    
    # 3. 카테고리 일치 검사 — PRO의 활동 카테고리에 요청 카테고리가 있어야 함
    pro_cats = await self.pro_cat_repo.list_by_user(current_user.id)
    category_ids = {pc.category_id for pc in pro_cats}
    if request.category_id not in category_ids:
        raise ForbiddenError()
    
    # 4. 중복 견적 검사 (service 단에서 409, DB 유니크 제약은 last-resort)
    existing = await self.quote_repo.get_by_request_and_pro(request_id, current_user.id)
    if existing is not None:
        raise DuplicateQuoteError()
    
    # 5. 견적 생성
    new_quote = Quote(
        service_request_id=request_id,
        pro_id=current_user.id,
        price=data.price,
        message=data.message,
        status=QuoteStatus.PENDING,
    )
    result = await self.quote_repo.create(new_quote)
    await self.session.commit()
    return result
```

#### 3. Quote 모델 UniqueConstraint

`Quote` 모델에 `__table_args__`로 유니크 제약을 선언한다. Alembic autogenerate가 이를 감지해 마이그레이션에 추가한다.

```python
class Quote(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "quotes"
    __table_args__ = (
        sa.UniqueConstraint("service_request_id", "pro_id", name="uq_quotes_request_pro"),
    )
    ...
```

**주의:** `uq_quotes_accepted_per_request`(Story 4.2 partial unique index)는 이 스토리의 마이그레이션에 포함하지 않는다. Story 4.2에서 별도로 추가한다.

#### 4. QuoteStatus Enum 패턴

`ServiceRequestStatus`와 동일한 `values_callable` 패턴을 사용한다. DB에 소문자 값("pending")으로 저장.

```python
class QuoteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CLOSED = "closed"

# 모델 내:
status: Mapped[QuoteStatus] = mapped_column(
    sa.Enum(
        QuoteStatus,
        name="quote_status",
        values_callable=lambda e: [m.value for m in e],
    ),
    nullable=False,
    default=QuoteStatus.PENDING,
)
```

#### 5. 마이그레이션 downgrade Enum 삭제

`service_request` 마이그레이션 패턴 참조. downgrade 함수 마지막에 Enum 타입 명시 삭제 추가:

```python
def downgrade() -> None:
    op.drop_index(op.f('ix_quotes_service_request_id'), table_name='quotes')
    op.drop_index(op.f('ix_quotes_pro_id'), table_name='quotes')
    op.drop_table('quotes')
    # PG enum 타입 명시 삭제 (drop_table은 Enum 타입을 제거하지 않음)
    sa.Enum(name='quote_status').drop(op.get_bind(), checkfirst=False)
```

---

### 구현 세부 사항

#### `models/quote.py`

```python
"""Quote ORM 모델 (Story 3.3).

status Enum은 DB에 소문자 값("pending")으로 저장 — values_callable 필수.
service_request_id / pro_id는 서비스 계층에서만 설정, 요청 바디 미수용(IDOR 방지).
UNIQUE(service_request_id, pro_id): 요청당 PRO 1개 견적 DB 레벨 강제.
"""

import enum
import uuid as _uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class QuoteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CLOSED = "closed"


class Quote(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "quotes"
    __table_args__ = (
        sa.UniqueConstraint("service_request_id", "pro_id", name="uq_quotes_request_pro"),
    )

    service_request_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("service_requests.id"), nullable=False, index=True
    )
    pro_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id"), nullable=False, index=True
    )
    price: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    status: Mapped[QuoteStatus] = mapped_column(
        sa.Enum(
            QuoteStatus,
            name="quote_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=QuoteStatus.PENDING,
    )
```

#### `schemas/quote.py`

```python
"""Quote Pydantic 스키마 (Story 3.3).

QuoteCreate: 클라이언트 입력. service_request_id/pro_id/status 미포함 — 서버에서만 설정(IDOR/변조 방지).
QuoteRead: API 응답. ORM 직렬화(from_attributes=True via CamelModel).
금액(price)은 정수 KRW(원 단위), 소수점 없음 (AR12 Format Patterns).
"""

import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.base import CamelModel


class QuoteCreate(CamelModel):
    price: int = Field(ge=0)          # 0원 허용(무료 서비스 가능), 음수 불가
    message: str = Field(min_length=1)

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("공백만 입력할 수 없습니다.")
        return stripped


class QuoteRead(CamelModel):
    id: uuid.UUID
    service_request_id: uuid.UUID
    pro_id: uuid.UUID
    price: int
    message: str
    status: str
    created_at: datetime
    updated_at: datetime
```

#### `repositories/quotes.py`

```python
"""QuoteRepository — quotes 테이블 DB 접근 (Story 3.3).

규약:
- 트랜잭션(commit)은 소유하지 않는다 — 호출측(service)이 관리.
- get_by_id: deleted_at IS NULL 필터 적용.
- get_by_request_and_pro: deleted_at IS NULL 필터 적용 (중복 검사는 미삭제 견적만).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote


class QuoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, obj: Quote) -> Quote:
        """견적 추가 후 flush/refresh. commit은 service 계층에서."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: uuid.UUID) -> Quote | None:
        """id로 미삭제 견적 조회."""
        result = await self.session.execute(
            select(Quote).where(
                Quote.id == id,
                Quote.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_request_and_pro(
        self, request_id: uuid.UUID, pro_id: uuid.UUID
    ) -> Quote | None:
        """특정 요청에 대한 특정 PRO의 미삭제 견적 조회 (중복 검사용)."""
        result = await self.session.execute(
            select(Quote).where(
                Quote.service_request_id == request_id,
                Quote.pro_id == pro_id,
                Quote.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
```

#### `services/quote.py`

```python
"""QuoteService — 견적 비즈니스 로직 (Story 3.3).

보안 규칙:
- service_request_id/pro_id는 서버에서만 설정(IDOR 방지).
- status는 PENDING으로 고정(변조 방지).
- 카테고리 일치 검사: PRO가 해당 카테고리의 요청에만 견적 가능(FR10/FR11).
- 중복 견적 검사: service 단 사전 검증 + DB UniqueConstraint는 last-resort.
"""

import uuid
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DuplicateQuoteError,
    ForbiddenError,
    ServiceRequestNotFoundError,
    ServiceRequestNotOpenForQuoteError,
)
from app.models.quote import Quote, QuoteStatus
from app.models.service_request import ServiceRequestStatus
from app.models.user import User
from app.repositories.pro_categories import ProCategoryRepository
from app.repositories.quotes import QuoteRepository
from app.repositories.service_requests import ServiceRequestRepository
from app.schemas.quote import QuoteCreate


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

        # 5. 견적 생성
        new_quote = Quote(
            service_request_id=request_id,
            pro_id=current_user.id,
            price=data.price,
            message=data.message,
            status=QuoteStatus.PENDING,
        )
        result = await self.quote_repo.create(new_quote)
        await self.session.commit()
        return result
```

#### `core/exceptions.py` — 추가할 예외

```python
class DuplicateQuoteError(AppError):
    """동일 요청에 이미 견적을 제안한 경우(Story 3.3 AC3). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="duplicate_quote",
            message="이미 이 요청에 견적을 제안했습니다.",
            status_code=409,
        )


class ServiceRequestNotOpenForQuoteError(AppError):
    """견적 제안 시 요청이 open 상태가 아닌 경우(Story 3.3 AC4). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="service_request_not_open",
            message="견적 제안은 open 상태의 요청에만 가능합니다.",
            status_code=409,
        )
```

#### `routers/quotes.py`

```python
"""Quote 라우터 — /api/v1/service-requests/{id}/quotes (Story 3.3).

prefix="/api/v1/service-requests"로 설정해 중첩 URL을 처리한다.
Story 3.4에서 GET /api/v1/quotes?mine=true 추가 시 두 번째 엔드포인트 추가 또는 별도 라우터 생성.

require_role(PRO): CUSTOMER·ADMIN 403 거부 (의도적).
service_request_id/pro_id는 current_user.id에서 주입 — 요청 바디 미수용(IDOR 방지).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps import CurrentUser, require_role
from app.models.user import UserRole
from app.schemas.quote import QuoteCreate, QuoteRead
from app.services.quote import QuoteService

router = APIRouter(prefix="/api/v1/service-requests", tags=["quotes"])


@router.post("/{request_id}/quotes", response_model=QuoteRead, status_code=201)
async def create_service_request_quote(
    request_id: uuid.UUID,
    body: QuoteCreate,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
) -> QuoteRead:
    svc = QuoteService(session)
    return await svc.submit(request_id, body, current_user)
```

#### `main.py` 변경

```python
# 기존 imports 끝 부분에 추가
from app.routers.quotes import router as quotes_router

# app.include_router 목록에 추가 (pros_router 뒤)
app.include_router(quotes_router)
```

#### `models/__init__.py` 변경

```python
# 기존 imports에 추가
from app.models.quote import Quote, QuoteStatus

__all__ = ["Category", "ProCategory", "Quote", "QuoteStatus", "ServiceRequest", "ServiceRequestStatus", "User", "UserRole"]
```

---

### 테스트 파일 구조 (`test_quotes_submit.py`)

기존 `test_service_requests_create.py`의 헬퍼 패턴을 참고하되, 독립 헬퍼를 정의한다.

```python
# 헬퍼 함수 구조
async def _make_pro(session, email) -> User: ...
async def _make_customer(session, email) -> User: ...
async def _make_admin(session, email) -> User: ...
async def _make_category(session, name="청소") -> Category: ...
async def _make_service_request(session, customer, category, status="open") -> ServiceRequest: ...
async def _assign_pro_categories(session, pro, categories) -> None: ...  # ProCategory 행 직접 삽입
def _auth(user) -> dict: ...  # {"Authorization": "Bearer <jwt>"}
```

`_make_service_request` status 파라미터: matched/completed/cancelled 요청을 직접 생성할 때 `ServiceRequest(status=ServiceRequestStatus.MATCHED, ...)` ORM 직접 생성 허용(테스트 헬퍼이므로 상태 전이 API 불필요).

테스트 케이스 목록 (14개):

| # | 테스트명 | 검증 |
|---|---------|------|
| 1 | `test_submit_quote_success_201` | 정상: 201, status=pending, proId=현재 PRO |
| 2 | `test_submit_quote_price_zero_201` | price=0 허용(무료 서비스): 201 |
| 3 | `test_submit_quote_duplicate_409` | 동일 요청 재제안: 409 duplicate_quote |
| 4 | `test_submit_quote_request_matched_409` | matched 요청: 409 service_request_not_open |
| 5 | `test_submit_quote_request_cancelled_409` | cancelled 요청: 409 service_request_not_open |
| 6 | `test_submit_quote_category_mismatch_403` | PRO 카테고리 불일치: 403 forbidden |
| 7 | `test_submit_quote_no_token_401` | 비인증: 401 not_authenticated |
| 8 | `test_submit_quote_customer_role_403` | CUSTOMER: 403 forbidden |
| 9 | `test_submit_quote_admin_role_403` | ADMIN: 403 forbidden |
| 10 | `test_submit_quote_request_not_found_404` | 존재하지 않는 request_id: 404 service_request_not_found |
| 11 | `test_submit_quote_price_negative_422` | price=-1: 422 |
| 12 | `test_submit_quote_missing_price_422` | price 필드 누락: 422 |
| 13 | `test_submit_quote_empty_message_422` | message 빈 문자열: 422 |
| 14 | `test_submit_quote_missing_message_422` | message 필드 누락: 422 |

---

### user-web 프론트엔드 (`(pro)/feed/[id]/page.tsx`)

기존 disabled 버튼을 실제 폼으로 교체한다.

```tsx
"use client";

import { use, useState } from "react";

import {
  useGetServiceRequestFeedDetail,
  useCreateServiceRequestQuote,
  type ServiceRequestRead,
  type QuoteRead,
} from "@gosoom/api-client";

export default function FeedDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const detail = useGetServiceRequestFeedDetail<ServiceRequestRead, Error>(id);
  const submitQuote = useCreateServiceRequestQuote<QuoteRead, Error>();

  const [price, setPrice] = useState("");
  const [message, setMessage] = useState("");
  const [submitted, setSubmitted] = useState(false);

  if (detail.isPending) return <div>로딩 중...</div>;
  if (detail.isError) return <div>요청을 불러오는 중 오류가 발생했습니다.</div>;

  const req = detail.data;
  if (!req) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const priceNum = parseInt(price, 10);
    if (isNaN(priceNum) || priceNum < 0 || !message.trim()) return;

    submitQuote.mutate(
      { requestId: id, data: { price: priceNum, message: message.trim() } },
      {
        onSuccess: () => setSubmitted(true),
      }
    );
  };

  return (
    <main style={{ padding: "1.5rem" }}>
      <h1>요청 상세</h1>
      <p><strong>카테고리 ID:</strong> {req.categoryId}</p>
      <p><strong>지역:</strong> {req.region}</p>
      <p><strong>내용:</strong> {req.description}</p>
      <p>
        <strong>상태:</strong>{" "}
        {req.status === "open" ? "견적 가능" : req.status === "matched" ? "이미 매칭됨" : req.status}
      </p>
      {req.desiredSchedule && <p><strong>희망 일정:</strong> {req.desiredSchedule}</p>}
      {req.budget != null && <p><strong>예산:</strong> {req.budget.toLocaleString()}원</p>}

      {req.status === "open" && !submitted && (
        <form onSubmit={handleSubmit} style={{ marginTop: "1.5rem" }}>
          <h2>견적 제안</h2>
          <div>
            <label>
              가격 (원):
              <input
                type="number"
                min={0}
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                required
                style={{ marginLeft: "0.5rem" }}
              />
            </label>
          </div>
          <div style={{ marginTop: "0.5rem" }}>
            <label>
              제안 메시지:
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                required
                rows={4}
                style={{ display: "block", width: "100%", marginTop: "0.25rem" }}
              />
            </label>
          </div>
          {submitQuote.isError && (
            <p style={{ color: "red" }}>
              {(submitQuote.error as Error)?.message ?? "견적 제출 중 오류가 발생했습니다."}
            </p>
          )}
          <button
            type="submit"
            disabled={submitQuote.isPending}
            style={{ marginTop: "1rem" }}
          >
            {submitQuote.isPending ? "제출 중..." : "견적 제안하기"}
          </button>
        </form>
      )}

      {req.status === "open" && submitted && (
        <p style={{ color: "green", marginTop: "1rem" }}>견적이 제출되었습니다.</p>
      )}

      {req.status === "matched" && (
        <p style={{ color: "gray", marginTop: "1rem" }}>
          이 요청은 이미 다른 고수와 매칭되었습니다.
        </p>
      )}
    </main>
  );
}
```

**주의:** `useCreateServiceRequestQuote` Orval 훅의 정확한 mutate 시그니처는 Orval 재생성 후 확인한다. `requestId`와 `data` 파라미터 이름은 Orval이 생성하는 타입에 따라 달라질 수 있다. 실제 생성된 훅의 시그니처를 보고 조정할 것.

---

### Orval 재생성 절차

1. API 서버 실행: `cd apps/api && uvicorn app.main:app --reload --port 8000`
2. `pnpm orval` (프로젝트 루트)
3. 생성 확인:
   - 훅: `useCreateServiceRequestQuote`
   - 타입: `QuoteCreate`, `QuoteRead`, `QuoteStatus`
4. `packages/api-client/src/generated/model/index.ts` 신규 타입 export 확인
5. `packages/api-client/src/index.ts` 신규 훅 re-export 확인

---

## 알려진 함정

### 1. `models/__init__.py` — Alembic autogenerate 필수 조건 ⚠️

`Quote`와 `QuoteStatus`를 `models/__init__.py`에 import하지 않으면 `alembic revision --autogenerate`가 `Quote` 모델을 감지하지 못해 빈 마이그레이션이 생성된다. 반드시 추가할 것.

### 2. `__table_args__` 튜플 문법 — 쉼표 필수 ⚠️

SQLAlchemy에서 `__table_args__`에 단일 제약만 있을 때 튜플로 전달하려면 trailing comma가 필수:

```python
__table_args__ = (
    sa.UniqueConstraint("service_request_id", "pro_id", name="uq_quotes_request_pro"),
)  # 쉼표 없으면 괄호로 인식되어 TypeError 발생
```

### 3. Orval 훅 mutate 시그니처 확인 ⚠️

`useCreateServiceRequestQuote` 훅의 mutate 파라미터 이름(requestId? serviceRequestId?)은 FastAPI 라우트 파라미터 이름 `request_id`를 Orval이 camelCase로 변환해 결정된다. 생성된 `quotes/quotes.ts` 파일을 열어 실제 함수 시그니처를 확인하고 프론트엔드 코드를 맞출 것.

### 4. `QuoteService`의 `ServiceRequestRepository` 임포트

`QuoteService`는 `ServiceRequestRepository`를 의존한다. 순환 임포트 없음(services → repositories, 역방향 없음).

### 5. `get_by_request_and_pro` — deleted_at IS NULL 필터 적용

중복 검사용 `get_by_request_and_pro`에도 `deleted_at IS NULL` 필터를 적용한다. 소프트 삭제된 이전 견적이 있어도 새 견적 제안을 허용하기 위함이다(정책: 소프트 삭제 = 논리적 삭제, 재제안 가능으로 처리). 단, 현재 스토리 범위에서는 소프트 삭제 경로가 없으므로 논쟁이 없다.

### 6. `submitted` 상태는 TanStack Query 캐시가 아닌 로컬 state로 관리

견적 제출 성공 후 "이미 제출" 표시를 위한 `submitted` 상태는 페이지 내 로컬 `useState`로 관리한다(서버 상태 아님). 페이지 새로고침 시 초기화되는 것이 의도된 동작이다 — Story 3.4(내 견적 목록)에서 서버 상태 기반으로 "이미 제출됨"을 표시하는 것이 더 정확한 접근이다.

### 7. `req.status === "open" && submitted` 중복 에러 처리

백엔드가 409(중복 견적)를 반환할 경우 `submitQuote.isError`로 에러를 표시한다. 에러 메시지는 `error.message`(한국어, AR12)로 노출 — api-client 인터셉터가 envelope의 `message` 필드를 Error.message에 매핑한다고 가정한다.

---

## 파일 구조 요약

### 신규 파일 (NEW)

```
apps/api/alembic/versions/<hash>_add_quotes_table.py    # quotes 마이그레이션
apps/api/app/models/quote.py                            # Quote 모델 + QuoteStatus enum
apps/api/app/schemas/quote.py                           # QuoteCreate, QuoteRead
apps/api/app/repositories/quotes.py                    # QuoteRepository
apps/api/app/services/quote.py                          # QuoteService
apps/api/app/routers/quotes.py                          # POST /{request_id}/quotes
apps/api/tests/test_quotes_submit.py                    # 14 pytest 케이스
```

### 수정 파일 (UPDATE)

```
apps/api/app/models/__init__.py          # Quote, QuoteStatus import 추가
apps/api/app/main.py                     # quotes_router import + include_router
apps/api/app/core/exceptions.py          # DuplicateQuoteError, ServiceRequestNotOpenForQuoteError 추가
apps/user-web/src/app/(pro)/feed/[id]/page.tsx  # 견적 제안 폼 구현
packages/api-client/src/generated/      # Orval 재생성 전체
packages/api-client/src/index.ts        # 신규 훅 re-export (Orval 자동)
```

### 수정 없는 파일 (NO CHANGE)

```
apps/api/app/models/service_request.py       # 변경 없음 (ServiceRequestStatus 재사용)
apps/api/app/repositories/service_requests.py # 변경 없음 (get_by_id 재사용)
apps/api/app/repositories/pro_categories.py  # 변경 없음 (list_by_user 재사용)
apps/api/app/routers/service_requests.py     # 변경 없음 (quotes_router는 별도 등록)
apps/user-web/src/app/(pro)/feed/page.tsx    # 변경 없음
apps/user-web/src/app/(pro)/layout.tsx       # 변경 없음
```

---

## 스토리 완료 기준 (Definition of Done)

- [ ] `alembic upgrade head` 통과 (quotes 테이블 + UNIQUE 제약 생성 확인)
- [ ] `pytest apps/api/tests/test_quotes_submit.py` — 14/14 통과
- [ ] 기존 테스트 회귀 없음: `pytest apps/api/` 전체 통과
- [ ] `pnpm typecheck` + `pnpm lint` + `pnpm build` 통과
- [ ] Orval 생성물 커밋 포함 (`packages/api-client/src/generated/` 변경사항)
- [ ] user-web `(pro)/feed/[id]` 화면 동작 확인:
  - PRO 로그인 후 open 요청 상세 → 견적 제안 폼 표시
  - 가격·메시지 입력 후 제출 → "견적이 제출되었습니다" 표시
  - 제출 후 재접속 시 폼 재표시(로컬 state 초기화 — Story 3.4에서 서버 상태 기반 처리)
  - matched 요청 상세 → 견적 폼 없음, "이미 매칭됨" 표시

---

## 이전 스토리 인텔리전스 (Story 3.2 교훈)

1. **`current_user.id` 직접 사용**: 경로 파라미터·바디에서 user_id를 받지 않고 항상 `current_user.id` 사용(IDOR 방지).

2. **카테고리 ID set 변환 패턴**: 카테고리 일치 검사 시 `{pc.category_id for pc in pro_cats}`로 set 생성 → `O(1)` 조회. 이 패턴을 `get_feed_detail`에서 이미 사용 중이므로 동일하게 적용한다.

3. **`ProCategoryRepository` 임포트**: `QuoteService`에서 `ProCategoryRepository`를 임포트한다. 순환 임포트 없음(서비스→레포지토리 단방향).

4. **`CamelModel` 경계**: `QuoteRead`는 `CamelModel` 기반이므로 JSON 직렬화 시 camelCase. 프론트에서 `serviceRequestId`, `proId`, `createdAt` 등으로 접근한다.

5. **router 등록 순서**: 현재 `main.py`에 `pros_router`가 마지막으로 등록되어 있다. `quotes_router`는 그 뒤에 추가한다. FastAPI는 `/api/v1/service-requests` prefix를 가진 두 라우터(기존 `service_requests_router` + 신규 `quotes_router`)를 모두 등록할 수 있다.

6. **commit() 위치**: `submit()`은 쓰기 작업이므로 `await self.session.commit()`을 반드시 포함한다. 기존 `service_request.create()`와 동일 패턴.

---

## Dev Agent Record

### Implementation Plan

1. Quote ORM 모델(`QuoteStatus` enum + `Quote` 클래스) 생성
2. Alembic autogenerate로 마이그레이션 생성 — `pro_categories` 오탐(FK ondelete 비교 차이) 제거 후 `alembic upgrade head` 적용
3. Pydantic 스키마(`QuoteCreate`, `QuoteRead`) 생성
4. `QuoteRepository` — `create`, `get_by_id`, `get_by_request_and_pro` 구현
5. `DuplicateQuoteError`, `ServiceRequestNotOpenForQuoteError` 예외 추가
6. `QuoteService.submit()` — 5단계 검증 후 생성
7. `quotes_router` 생성 + `main.py` 등록
8. `models/__init__.py`에 Quote/QuoteStatus 추가
9. 14개 pytest 케이스 작성 (14/14 통과)
10. openapi.json 서버에서 다시 받아 Orval 재생성 → `quotes/quotes.ts`, `quoteRead.ts`, `quoteCreate.ts` 확인
11. `api-client/src/index.ts`에 `./generated/quotes/quotes` re-export 추가
12. `user-web/(pro)/feed/[id]/page.tsx` — 기존 disabled 버튼 → price+message 폼으로 교체

### Completion Notes

- **모든 14개 pytest 케이스 통과** (AC2~AC5, 유효성 검사, 존재하지 않는 요청 포함)
- **전체 회귀 없음**: 154개 통과 (5개 기존 실패는 DB에 seed 카테고리 잔류 오염 문제, 이번 변경과 무관)
- **Alembic 마이그레이션**: `alembic upgrade head` 성공 — `quotes` 테이블 + UNIQUE 제약 + 인덱스 생성
- **Orval 훅 mutate 시그니처**: `{ requestId: string, data: QuoteCreate }` — 스토리 경고대로 확인 후 프론트 코드에 반영
- **빌드 검증**: `pnpm typecheck` ✅ + `pnpm lint` ✅ + `pnpm build` ✅

### File List

신규 파일:
- `apps/api/alembic/versions/d7bffeb07473_add_quotes_table.py`
- `apps/api/app/models/quote.py`
- `apps/api/app/schemas/quote.py`
- `apps/api/app/repositories/quotes.py`
- `apps/api/app/services/quote.py`
- `apps/api/app/routers/quotes.py`
- `apps/api/tests/test_quotes_submit.py`
- `packages/api-client/src/generated/quotes/quotes.ts`
- `packages/api-client/src/generated/model/quoteCreate.ts`
- `packages/api-client/src/generated/model/quoteRead.ts`

수정 파일:
- `apps/api/app/models/__init__.py` — Quote, QuoteStatus import 추가
- `apps/api/app/main.py` — quotes_router 등록
- `apps/api/app/core/exceptions.py` — DuplicateQuoteError, ServiceRequestNotOpenForQuoteError 추가
- `apps/user-web/src/app/(pro)/feed/[id]/page.tsx` — 견적 제안 폼 구현
- `packages/api-client/src/index.ts` — quotes re-export 추가
- `packages/api-client/src/generated/model/index.ts` — quoteCreate/quoteRead export (Orval 자동)
- `openapi.json` — 최신 스펙 반영

### Change Log

- 2026-06-09: Story 3.3 구현 완료 — `POST /api/v1/service-requests/{id}/quotes` 엔드포인트, quotes 테이블 마이그레이션, QuoteService.submit() 5단계 검증 로직, 14개 pytest 케이스 추가, user-web 견적 제안 폼 구현
