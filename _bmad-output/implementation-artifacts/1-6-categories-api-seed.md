---
baseline_commit: NO_VCS
---
# Story 1.6: 카테고리 엔티티·조회 API·시드

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 고객·고수,
I want 서비스 카테고리 목록을 조회하기를,
So that 요청 생성(FR5)과 고수 카테고리 설정(FR9)에서 동일한 카테고리를 선택할 수 있다.

이 스토리는 **두 가지 신규 프리미티브**를 확립한다(1.3이 `CamelModel` 직렬화 경계를, 1.5가 RBAC 가드를 확립한 것과 동일한 "첫 슬라이스가 선례를 만든다" 패턴):
① **첫 목록(list) 응답 프리미티브** — `{items, nextCursor}` 페이지네이션 envelope(`Page` 스키마)와 **opaque cursor 규약**. 이후 Epic 2(요청)·3(견적)·4(채팅)·6(관리자)의 모든 목록 엔드포인트가 이 envelope와 opaque cursor 규약을 **재사용**한다.
② **첫 참조(reference) 도메인** — `categories` 테이블 + 조회 API + 기본 카테고리 시드. Epic 2·3가 빈 의존성 없이 동작하기 위한 시드 데이터.

> ⚠️ **범위의 본질(반드시 인지):** 이 스토리는 **읽기 전용 조회 + 시드**만 한다. 카테고리 **생성/수정/삭제(FR24)는 관리자 Epic 6** 범위이며 이 스토리에 포함하지 않는다. 고수↔카테고리 M:N(`pro_categories`, AR6/G1)는 **Epic 3(Story 3.1)** 범위 — 여기선 `categories` 단일 테이블만. 페이지네이션은 **일반화된 엔진을 만들지 않는다**(아래 "결정 사항 #1" 강력 경고): 재사용 자산은 `Page` envelope + opaque cursor **규약**이지, 컬럼/방향 파라미터화 keyset 엔진이 아니다.

## Acceptance Criteria

**AC1 — categories 테이블 + GET /api/v1/categories: 활성 카테고리만 `{items, nextCursor}`로 반환**
**Given** `categories` 테이블(id UUIDv7, name, is_active, created_at/updated_at, deleted_at)이 마이그레이션될 때
**When** 인증된 사용자가 `GET /api/v1/categories`를 호출하면
**Then** 활성 카테고리 목록이 `{items: [...], nextCursor: string|null}` 형식으로 반환된다 — 비활성(`is_active=false`)·소프트삭제(`deleted_at IS NOT NULL`) 카테고리는 **둘 다** 제외된다. 각 항목은 안전한 표현(`CategoryRead`: id·name·isActive·createdAt·updatedAt)이며 직렬화 경계는 camelCase다(AR12, architecture#Format Patterns line 297).

**AC2 — 기본 카테고리 시드(Epic 2·3 의존성 충족)**
**Given** 초기 부트스트랩 시
**When** seed 스크립트(`uv run python -m app.seed`)가 실행되면
**Then** 기본 카테고리(예: 청소, 정리수납, 이사, 인테리어 등)가 생성되어 Epic 2(요청 생성)·3(고수 카테고리)이 빈 의존성 없이 동작한다(AR5). 시드는 **멱등**이다 — 2회 실행해도 카테고리는 중복 없이 정확히 기본 집합만 존재한다. **카테고리 시드는 외부 시크릿·env 설정을 요구하지 않는다**(관리자 시드와 달리 SEED_* 불요 — 결정 사항 #4).

**AC3 — 인증된 모든 역할 읽기 허용(고객·고수·관리자), 쓰기는 범위 외**
**Given** 인증된 사용자(고객·고수·관리자)가
**When** 카테고리 조회를 요청하면
**Then** 세 역할 **모두** 200으로 읽기가 허용된다. 미인증/무효 토큰은 401(`get_current_user` 차단, 1.5 규칙). 카테고리 **생성/수정/삭제(FR24)는 이 스토리 범위에 포함되지 않는다**(관리자 Epic 6).
> **AC 리터럴 초과 근거(scope creep 아님):** epic AC 원문은 "고객·고수 모두 읽기 허용"이라 적었으나, 관리자(admin)도 카테고리를 읽어야 한다 — Epic 6 카테고리 관리(FR24)가 이 조회 위에 구축되고, 참조 데이터는 특정 역할을 배제할 이유가 없다. 따라서 `require_role(CUSTOMER, PRO)`로 admin을 배제하지 않고 **`CurrentUser`(인증만 요구, 모든 역할 허용)**로 구현한다 — `/users/me`(1.5)와 동일한 "인증만, 역할 무제한" 패턴. (시스템이 end-to-end로 동작하려면 필요한 동작 — 리뷰 시 AC-리터럴 누락이 아니라 의도적 결정으로 읽혀야 함.)

**AC4 — cursor 페이지네이션이 실제로 동작(faked nextCursor 금지)**
**Given** `limit`보다 많은 활성 카테고리가 있을 때(또는 테스트에서 작은 `limit`을 줄 때)
**When** `GET /api/v1/categories?limit=<n>`로 첫 페이지를, 그 응답의 `nextCursor`로 `GET /api/v1/categories?cursor=<nextCursor>&limit=<n>` 다음 페이지를 호출하면
**Then** 첫 페이지는 정확히 `n`개 + 비-null `nextCursor`를, 마지막 페이지는 잔여 항목 + `nextCursor=null`을 반환하며, 두 페이지 사이에 **중복·누락이 없다**. `nextCursor`는 **opaque 문자열**(base64)이며 클라이언트는 내부 구조를 해석하지 않는다. 손상된 cursor는 500이 아니라 400(`invalid_cursor`) 표준 envelope로 거부된다.

## Tasks / Subtasks

- [x] **Task 1 — Category 모델 + models/__init__ 등록** (AC: 1)
  - [x] `app/models/category.py` **신규**: `class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin)` — `__tablename__ = "categories"`.
    - `name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)` — **unique+index는 의도적 추가**(epic AC 컬럼 리터럴엔 "name"만 있고 unique 미명시). 근거: ① 멱등 시드(`get_by_name` 선검사), ② 중복 카테고리 방지. (1.3 `is_seed` 의도적 추가와 동일 성격 — scope creep 아님. 아래 결정 사항 #3.)
    - `is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))` — `User.is_active`와 동일 패턴 복제.
    - ❌ **`is_seed` 컬럼 없음(의도적 부재):** epic AC가 categories에 `is_seed`를 명시하지 않았고, 카테고리는 "잠금 방지" 대상이 아니다(시드 관리자만 FR21 잠금 방지). users의 `is_seed`를 **복제하지 않는다.**
    - ⚠️ **PG enum 없음:** categories는 enum 컬럼이 전혀 없다 → 1.3 users 마이그레이션의 `sa.Enum(name="user_role").drop(...)` downgrade 보정이 **여기엔 해당 없음**. 이 패턴을 카테고리 마이그레이션에 **cargo-cult 복제하지 말 것**(존재하지 않는 타입 drop은 downgrade를 깬다). 아래 Task 6 참조.
  - [x] `app/models/__init__.py` (UPDATE): `from app.models.category import Category` 추가 + `__all__`에 `"Category"`. **alembic autogenerate가 모델을 감지하려면 반드시 여기서 import**(env.py가 `app.models`를 로드 — 1.3 함정 계승). 기존 `User`/`UserRole` import **보존**(append).

- [x] **Task 2 — schemas: Page 페이지네이션 envelope + CategoryRead** (AC: 1, 4)
  - [x] `app/schemas/pagination.py` **신규** — **첫 목록 응답 프리미티브(이후 Epic 2~6 재사용):**
    - `T = TypeVar("T")`; `class Page(CamelModel, Generic[T]): items: list[T]; next_cursor: str | None = None`.
    - 직렬화 경계는 `{items, nextCursor}`(CamelModel alias). `next_cursor`는 **opaque 문자열 또는 null** — architecture#Format Patterns(line 297) 정합.
    - 모듈 docstring: "목록 응답 단일 형식(`{items, nextCursor}`)과 opaque cursor 규약의 단일 소스. Epic 2(요청)·3(견적)·4(채팅)·6(관리자)의 모든 목록 엔드포인트가 이 `Page`를 재사용한다. **단, keyset 쿼리 자체는 각 도메인이 자신의 정렬(예: createdAt DESC)로 작성한다** — `Page`는 envelope+규약만 제공하고 컬럼/방향을 일반화하지 않는다(결정 사항 #1)."
    - ⚠️ **Pydantic v2 Generic + FastAPI:** `response_model=Page[CategoryRead]`는 정상 동작(OpenAPI 스키마명 `Page_CategoryRead_` 자동 생성, Orval 소비는 1.7). `from typing import Generic, TypeVar`.
  - [x] `app/schemas/category.py` **신규**: `class CategoryRead(CamelModel): id: UUID; name: str; is_active: bool; created_at: datetime; updated_at: datetime`. **`deleted_at` 미포함**(내부 마커 — 안전 표현). `from_attributes=True`(CamelModel 상속)로 ORM `Category` 직접 직렬화.

- [x] **Task 3 — core/pagination.py: opaque cursor encode/decode 헬퍼** (AC: 4)
  - [x] `app/core/pagination.py` **신규** — **최소 2함수만**(일반 엔진 금지):
    - `def encode_cursor(value: str) -> str`: `base64.urlsafe_b64encode(value.encode()).decode()` — 경계값(여기선 UUID 문자열)을 opaque 문자열로.
    - `def decode_cursor(cursor: str) -> str`: base64 디코드. 디코드 실패(`binascii.Error`/`ValueError`/`UnicodeDecodeError`)는 잡아 `InvalidCursorError`(Task 7)로 변환 — **500 누수 방지**(1.5 payload 형식 가드 철학 계승).
    - 모듈 docstring: "opaque cursor 규약의 단일 구현. cursor는 정렬 경계값을 base64로 감싼 불투명 문자열 — 클라이언트는 구조를 해석하지 않는다(서버가 자유롭게 키 구성 변경 가능). Epic 2+는 복합 키(createdAt+id 등)를 이 규약으로 인코딩한다 — **재사용 자산은 이 불투명 규약**이지 keyset 로직이 아니다."
  - [x] ⚠️ **카테고리 cursor = `id`(UUIDv7) 문자열을 base64 인코딩.** UUIDv7은 시간정렬 가능·불변(immutable)이라 keyset 경계로 안전(name은 Epic 6에서 수정 가능 → keyset 경계로 부적합). 디코드 후 `UUID(decoded)` 변환 실패도 `InvalidCursorError`로 정규화(Task 5에서 처리).

- [x] **Task 4 — repository: CategoryRepository** (AC: 1, 2, 4)
  - [x] `app/repositories/categories.py` **신규**: `class CategoryRepository: def __init__(self, session: AsyncSession)` — `UserRepository` 패턴 복제(트랜잭션 미소유, 조회만).
    - `async def list_active(self, after_id: UUID | None, limit: int) -> list[Category]`:
      - `stmt = select(Category).where(Category.is_active.is_(True), Category.deleted_at.is_(None))` — **`is_active`와 `deleted_at`을 둘 다 필터**(AC1). ⚠️ 이는 `UserRepository`(deleted_at만 필터, is_active는 get_current_user가 검사)와 **다르다** — 카테고리는 비활성도 목록 단계에서 제외해야 한다.
      - `if after_id is not None: stmt = stmt.where(Category.id > after_id)` — keyset(이전 페이지 마지막 id 이후).
      - `stmt = stmt.order_by(Category.id).limit(limit)` — `id`(UUIDv7) 오름차순 단일 컬럼 keyset. PG `uuid` 비교는 바이트순 = UUIDv7 시간순.
      - `return list((await self.session.execute(stmt)).scalars().all())`.
    - `async def get_by_name(self, name: str) -> Category | None`: `select(Category).where(Category.name == name, Category.deleted_at.is_(None))` — **시드 멱등성 선검사용**(get_by_email 패턴 복제). 정규화는 단순 `name.strip()`(이메일과 달리 소문자화 불요 — 한국어 카테고리명).
    - `async def create(self, category: Category) -> Category`: `add → flush → refresh → return`(commit은 호출측). `UserRepository.create` 복제.
  - [x] ❌ **all-inclusive(비활성 포함) 목록 메서드 만들지 않는다** — 관리자 카테고리 관리(Epic 6)가 자체 메서드를 추가. 이 스토리는 활성-only 조회만(과설계 금지).

- [x] **Task 5 — service: CategoryService.list_active(cursor, limit)** (AC: 1, 4)
  - [x] `app/services/category.py` **신규**: `class CategoryService: def __init__(self, session: AsyncSession)` → 내부 `CategoryRepository(session)`.
    - `async def list_active(self, cursor: str | None, limit: int) -> Page[CategoryRead]`:
      - ① cursor 디코드: `after_id = None`; `if cursor is not None:` → `decode_cursor(cursor)` → `UUID(...)`. 두 변환 실패 모두 `InvalidCursorError`(decode_cursor는 자체 처리, `UUID()`는 여기서 try/except로 `InvalidCursorError` 변환 — base64는 유효하나 UUID가 아닌 cursor 방어).
      - ② `rows = await repo.list_active(after_id, limit + 1)` — **limit+1 패턴**으로 "다음 페이지 존재" 판정.
      - ③ `has_more = len(rows) > limit`; `page_rows = rows[:limit]`.
      - ④ `next_cursor = encode_cursor(str(page_rows[-1].id)) if has_more else None`.
      - ⑤ `return Page[CategoryRead](items=[CategoryRead.model_validate(c) for c in page_rows], next_cursor=next_cursor)`.
    - **권한:** 읽기 전용·소유권 무관(참조 데이터). `ensure_owner_or_admin` 호출 없음 — 인증(라우터 `CurrentUser`)만으로 충분. service는 비즈니스 로직(페이지네이션)만.
  - [x] ⚠️ **limit 검증은 라우터(Pydantic Query)에서** — service는 이미 검증된 limit을 받는다(아래 Task 6). service에서 중복 clamp 불요.

- [x] **Task 6 — router: GET /api/v1/categories + main 등록** (AC: 1, 3, 4)
  - [x] `app/routers/categories.py` **신규**: `router = APIRouter(prefix="/api/v1/categories", tags=["categories"])` — architecture 태그 규약(categories 도메인, line 199·450) 정합.
    - `@router.get("", response_model=Page[CategoryRead])` `async def list_categories(current_user: CurrentUser, cursor: str | None = None, limit: int = Query(default=50, ge=1, le=100)) -> Page[CategoryRead]: return await CategoryService(db).list_active(cursor, limit)`.
      - **함수명 `list_categories`** — operationId 안정화(Orval 함수명 직결, AR9, 소비는 1.7).
      - **`current_user: CurrentUser`** — 인증만 요구(모든 역할 허용, AC3 근거 참조). `require_role` **미적용**(admin 배제하지 않음).
      - `db: AsyncSession = Depends(get_db)` 주입 필요(service 구성용). `current_user`/`cursor`/`limit`/`db` 시그니처 순서 주의(기본값 없는 `current_user`가 먼저, 그 다음 기본값 있는 쿼리·db).
      - `limit`은 `Query(ge=1, le=100, default=50)` — 상한 100으로 과대 요청 차단(DoS 완화). 카테고리 기본 집합은 50 이하라 보통 단일 페이지(nextCursor=null)지만 메커니즘은 **실제 동작**(faked 아님).
    - ⚠️ **빈 경로 라우트:** prefix가 `/api/v1/categories`이므로 `@router.get("")`(빈 문자열) → 최종 경로 `/api/v1/categories`. `@router.get("/")`는 trailing slash 불일치 유발 가능 — `""` 사용(1.5 users `/me`와 동일 명시 경로 규약).
  - [x] `app/main.py` (UPDATE, append): `from app.routers.categories import router as categories_router` + `app.include_router(categories_router)`. **기존 `auth_router`/`users_router`/health/예외 핸들러 등록 보존**(append만, users_router 다음 위치).

- [x] **Task 7 — core/exceptions.py: InvalidCursorError** (AC: 4)
  - [x] 기존 `AppError` 서브클래스 패턴으로 **추가**(기존 예외 전부 보존): `class InvalidCursorError(AppError): def __init__(self): super().__init__(code="invalid_cursor", message="잘못된 커서입니다.", status_code=400)`.
  - [x] 근거: 손상/위조 cursor(비-base64, 비-UUID)가 `decode_cursor`/`UUID()`에서 던지면 전역 Exception 핸들러로 새어 **500**이 된다. 400 표준 envelope로 정규화(1.5 payload 형식 가드 철학 — 사용자 입력 오류는 4xx). 400은 이 스토리가 처음 도입하나 전역 핸들러가 `AppError.status_code`를 그대로 쓰므로 핸들러 수정 불요(403이 1.5에서 자동 envelope였던 것과 동일).

- [x] **Task 8 — Alembic 마이그레이션(categories 테이블)** (AC: 1)
  - [x] Task 1(모델 + `__init__` import) 완료 후 `uv run alembic revision --autogenerate -m "add categories table"`.
  - [x] **down_revision 확인:** 현재 head는 `04c24a1c717d`(users). 자동 생성 파일의 `down_revision = '04c24a1c717d'` 검증. **체인: 38c2a20deb69(baseline) → 04c24a1c717d(users) → <new>(categories).**
  - [x] **autogenerate 검수(사람 검수 필수, architecture line 173):**
    - `categories` 테이블 컬럼(id UUID, name, is_active server_default true, created_at/updated_at server_default now(), deleted_at nullable)이 반영됐는지.
    - `name` unique index(`ix_categories_name`, unique=True)가 생성됐는지.
    - ⚠️ **PG enum drop 보정 불필요:** categories엔 enum 컬럼이 없다 → downgrade는 `drop_index` + `drop_table`만. **`sa.Enum(...).drop()`을 추가하지 말 것**(1.3 users 마이그레이션을 무지성 복제하면 존재하지 않는 타입 drop으로 downgrade 실패). users의 `user_role` enum은 그대로 둔다(별도 마이그레이션 소유).
  - [x] **멱등/재현 검증(1.2/1.3 회귀가드 유지):** `alembic upgrade head` → `downgrade -1`(또는 base) → `upgrade head` 깨끗이 통과. **시드는 이 체인에 넣지 않는다**(Task 9 — `upgrade head`는 순수 스키마만, 무크리덴셜 통과 보존).

- [x] **Task 9 — 시드 확장: seed_categories(session) + main() 배선** (AC: 2)
  - [x] `app/seed.py` (UPDATE, append): `async def seed_categories(session: AsyncSession) -> str` 추가 — **멱등** 카테고리 시드.
    - 기본 카테고리 목록을 **모듈 상수로 하드코딩**: `DEFAULT_CATEGORIES = ["청소", "정리수납", "이사", "인테리어", "수리", "설치"]`(예시 — 적정 기본 집합. 비밀이 아닌 고정 참조값이라 env 불요).
    - 각 이름에 대해 `get_by_name(name)` → 존재하면 skip, 없으면 `Category(name=name, is_active=True)` 생성+add. 루프 후 `await session.commit()`(또는 항목별 flush + 마지막 commit). 생성 개수 카운트해 메시지 반환(예: "카테고리 시드: 신규 3개 / 기존 3개 skip").
    - IntegrityError 가드(seed_admin 패턴): unique 위반(동시 실행/잔존 행) 시 rollback 후 명확한 한국어 ValueError 또는 skip 처리.
  - [x] `main()` (UPDATE): **카테고리 시드를 관리자 시드와 독립**으로 실행 — `seed_categories`는 env 불요로 항상 동작해야 한다(Epic 2/3 의존성). 권장 형태:
    ```python
    async def main() -> None:
        async with SessionLocal() as session:
            print(await seed_categories(session))          # env 불요 — 항상 실행
            try:
                print(await seed_admin(session))            # SEED_ADMIN_* 필요
            except ValueError as exc:
                print(f"[시드 경고] 관리자 시드 건너뜀: {exc}", file=sys.stderr)
    ```
    → **함정 회피:** 현재 `main()`은 `seed_admin`이 SEED_ADMIN_* 미설정 시 ValueError로 즉시 종료한다. 그대로 두면 카테고리 시드가 admin 크리덴셜 부재로 막혀 Epic 2/3가 빈 카테고리로 깨진다. admin 실패를 경고로 격하하고 카테고리 시드를 선행·독립 실행한다. (외곽 `if __name__` try/except는 카테고리 시드 자체의 예외만 잡도록 유지.)
  - [x] ❌ **config.py 변경 없음:** 카테고리는 SEED_* env 필드를 추가하지 않는다(관리자 시드와의 핵심 차이 — 결정 사항 #4). `.env`/`.env.example` 변경 없음.

- [x] **Task 10 — 테스트(실 DB + 트랜잭션 롤백)** (AC: 1, 2, 3, 4)
  - [x] `tests/test_categories_list.py` **신규** — 기존 `client_db`/`db_session` 픽스처 재사용(실 DB + SAVEPOINT 롤백). 토큰은 `create_access_token(user.id, user.user_role)`(1.4) 직접 생성. 카테고리는 `db_session`으로 직접 insert(시드 함수 호출 또는 `Category(...)` 직접).
    - **인증 필요(AC3):** 토큰 없이 `GET /api/v1/categories` → 401 `{code:"not_authenticated"}`.
    - **성공 + envelope 형식(AC1):** 활성 카테고리 2~3개 시드 → 200, 응답에 `items`(list)·`nextCursor` 키 존재, 각 item에 `name`/`isActive`(camel)·`createdAt`, `deletedAt` 키 **부재**. 단일 페이지면 `nextCursor is None`.
    - **비활성·소프트삭제 제외(AC1):** 활성 1 + `is_active=False` 1 + `deleted_at` 설정 1 → 활성 1개만 반환. **두 제외 조건 모두** 증명.
    - **모든 역할 허용(AC3):** customer·pro·**admin** 토큰 각각 → 200(admin 배제 안 됨 증명 — `require_role`가 아니라 `CurrentUser`임을 검증하는 핵심 회귀 테스트).
    - **페이지네이션 실동작(AC4):** 활성 카테고리 N개(예 5) 시드, `limit=2` → 1페이지 2개 + `nextCursor` 비-null; `cursor=<nextCursor>&limit=2` → 2페이지 2개; 3페이지 1개 + `nextCursor=null`. **세 페이지 항목 합집합 = 전체 N, 중복 없음**(id 집합 비교).
    - **손상 cursor(AC4):** `cursor=not-base64!!!` 또는 base64지만 비-UUID → 400 `{code:"invalid_cursor"}`(500 아님).
    - **limit 경계:** `limit=0`/`limit=101` → 422(Pydantic Query ge=1/le=100).
  - [x] `tests/test_seed.py` (UPDATE, append) 또는 `tests/test_seed_categories.py` **신규** — `seed_categories`를 `db_session`으로 직접 2회 호출 → 카테고리가 `DEFAULT_CATEGORIES` 집합과 정확히 일치(중복 0), 멱등 확인. (admin 시드 테스트는 기존 유지.)
  - [x] **기존 테스트 회귀 0 확인:** `uv run pytest -q` 전체 통과(1.3~1.5의 22+ 테스트 회귀 0) + `uv run ruff check .` clean.

## Dev Notes

### 🎯 스코프 경계 (범위 침범 금지)

- ✅ **이 스토리:** `categories` 테이블 1개, `GET /api/v1/categories`(활성 조회만), `Page` 페이지네이션 envelope + opaque cursor 규약, 기본 카테고리 멱등 시드. **첫 목록 응답 프리미티브 + 첫 참조 도메인 확립.**
- ❌ **카테고리 생성/수정/삭제(FR24)는 Epic 6(관리자).** POST/PATCH/DELETE 엔드포인트, 비활성화 로직, 사용 중 카테고리 물리삭제 차단 모두 이 스토리 밖. 읽기 전용.
- ❌ **고수↔카테고리 M:N(`pro_categories`, AR6/G1)은 Epic 3(Story 3.1).** 조인 테이블·고수 카테고리 설정 API 금지. `categories` 단일 테이블만.
- ❌ **service_requests·quotes·chat 테이블 금지** — 각각 Epic 2/3/4. categories 외 도메인 테이블 0개.
- ❌ **페이지네이션 일반 엔진 금지(결정 사항 #1).** 컬럼/방향 파라미터화 keyset 추상화, `Paginator` 클래스, 정렬 전략 레지스트리 등 만들지 않는다. `Page` envelope + opaque cursor 2함수 + categories 전용 단일 컬럼 keyset만.
- ❌ **Orval/api-client/프론트 UI는 1.7.** 이 스토리는 백엔드 + OpenAPI 노출까지(operationId·`Page[CategoryRead]` 스키마 안정화만 신경, 소비는 1.7).
- ❌ **all-inclusive(비활성 포함) 목록 금지** — Epic 6 관리자 조회가 자체 메서드 추가.

### ⚖️ 결정 사항 (Dev가 그대로 채택)

- **🔑 #1 — 페이지네이션은 일반화하지 않는다(가장 중요한 절제):** 재사용 자산은 **딱 두 가지** — ① `Page` Pydantic 모델(`{items, nextCursor}` envelope), ② cursor가 **opaque 문자열**이라는 규약(base64 encode/decode 2함수). 이게 Epic 2+가 상속할 선례다.
  - **하지 말 것:** 컬럼/방향을 파라미터로 받는 범용 keyset 엔진. 이유 — 실제 페이지네이션 소비자는 categories와 **형태가 다르다**: 요청·견적은 `createdAt` **DESC**(architecture line 338), 메시지는 `after=<lastId>` **증분**(line 205 — 이건 cursor 페이지네이션이 *아니라* 별개 패턴). 작은 이름 목록에 맞춰 범용 엔진을 만들면 **틀린 형태**를 만들고 나중에 재작업한다.
  - **할 것:** categories 전용 단일 컬럼 keyset(`id` ASC, `id > after_id`, `LIMIT limit+1`). 정직한 실동작(faked nextCursor 금지). Dev Notes/코드 주석에 명시: "Epic 2는 `Page` envelope + opaque cursor 규약을 재사용하되 자신의 createdAt-DESC keyset을 직접 작성한다."
- **🔑 #2 — 인증은 `CurrentUser`(모든 역할), `require_role` 아님:** AC 리터럴은 "고객·고수"지만 admin 배제 시 Epic 6이 막힌다. `/users/me`와 동일하게 인증만 요구. (AC3 근거 박스 참조 — 리뷰 Acceptance Auditor가 의도적 결정으로 읽도록 스토리에 근거 명시.)
- **🔑 #3 — `name` UNIQUE + index는 의도적 추가:** epic 컬럼 리터럴 초과지만 멱등 시드(`get_by_name`)·중복 방지에 필요. 1.3 `is_seed`와 동일 "AC 리터럴 초과·근거 명시" 성격.
- **🔑 #4 — 카테고리 시드는 env/시크릿 불요:** 관리자 시드(SEED_ADMIN_*, 비밀번호=시크릿)와 달리 카테고리는 고정·비밀 아닌 기본값 → seed.py에 하드코딩, config.py·`.env` 변경 없음. **결과: 이 스토리엔 수동 KTH 체크포인트가 없다**(1.5와 동일 "신규 외부 설정 없음" — 아래 체크포인트 섹션).
- **#5 — cursor 키 = `id`(UUIDv7), name 아님:** UUIDv7은 불변·시간정렬이라 keyset 경계로 안전. `name`은 Epic 6에서 수정 가능 → 페이지네이션 도중 경계 이동 위험. id로 keyset(불변 키 원칙).
- **#6 — 목록 필터는 `is_active AND deleted_at IS NULL` 둘 다:** users repo(deleted_at만, is_active는 get_current_user)와 다르다. 카테고리는 비활성도 목록에서 제외(AC1). repository 메서드를 활성-only로 한정.

### ⚠️ 알려진 함정 (런타임 디버깅 전 미리 적용 — 고가치)

1. **autogenerate 전 모델 import 필수(1.3 계승):** `app/models/__init__.py`에 `Category` import가 없으면 autogen이 빈 마이그레이션 생성(테이블 누락). Task 1 → Task 8 순서 엄수.
2. **PG enum drop 보정 cargo-cult 금지(이 스토리 신규 함정):** 1.3 users 마이그레이션 downgrade엔 `sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=False)`가 있다. **categories엔 enum이 없으므로 이 줄을 복제하면 안 된다** — 존재하지 않는 타입 drop이 downgrade를 깬다. autogen이 생성한 categories downgrade(`drop_index`+`drop_table`)를 그대로 두고 enum 줄을 **추가하지 않는다.** up→down→up 체인으로 검증.
3. **손상 cursor → 500 누수 방지(1.5 형식 가드 계승):** base64 디코드 실패·비-UUID cursor는 `decode_cursor`/`UUID()`에서 예외 → 잡지 않으면 전역 Exception 핸들러로 새어 500. `InvalidCursorError`(400)로 정규화. 테스트로 증명(`cursor=not-base64!!!`).
4. **limit+1 keyset 판정:** "다음 페이지 존재"를 알려면 `LIMIT limit+1`로 조회해 `len(rows) > limit`이면 has_more. 응답 items는 `rows[:limit]`로 잘라 정확히 limit개만. nextCursor는 잘린 마지막 항목(`rows[:limit][-1]`)의 id — `rows[-1]`(limit+1번째)가 아님에 주의.
5. **Pydantic Generic + FastAPI response_model:** `Page[CategoryRead]`를 response_model로 쓸 때 Pydantic v2가 구체화한 모델을 FastAPI가 OpenAPI에 등록한다(스키마명 `Page_CategoryRead_`). `Page`는 `Generic[T]` 상속 필수. `CategoryService.list_active`가 `Page[CategoryRead](...)`로 구체 타입을 인스턴스화해 반환.
6. **라우터 시그니처 인자 순서:** `current_user: CurrentUser`(기본값 없음)가 `cursor`/`limit`/`db`(기본값 있음)보다 **먼저** 와야 Python 문법 오류 없음. FastAPI는 타입으로 주입원을 구분하므로 순서 자유지만 "기본값 없는 인자 먼저" 규칙은 지킨다.
7. **빈 경로 라우트(`@router.get("")`):** prefix `/api/v1/categories` + `""` → `/api/v1/categories`. `"/"`는 trailing-slash 리다이렉트/불일치 유발 — `""` 사용(1.5 `/me` 명시 경로 규약).
8. **카테고리명 정규화는 strip만:** 이메일과 달리 소문자화 안 함(한국어 카테고리명, "청소" 등). `get_by_name`/시드 모두 `name.strip()`만 — 일관 적용.
9. **uuid7 / uv 실행(1.2~1.5 계승):** import는 `from uuid_extensions import uuid7`(이미 base mixin이 사용). 이 PC는 uv managed standalone 3.12 실행 불가 → `[tool.uv] python-preference="only-system"`, `uv sync`/`uv run pytest`/`uv run ruff check .` 사용.

### 현재 코드 상태 (UPDATE/NEW 대상 — 보존할 것)

Story 1.3(가입)·1.4(로그인)·1.5(RBAC)가 auth/users 슬라이스와 인가 프리미티브를 완성. 아래는 현재 실제 상태이며 **덮어쓰지 말고 확장/추가**한다:

- **`app/models/__init__.py`** (UPDATE): 현재 `from app.models.user import User, UserRole` + `__all__=["User","UserRole"]`. → `Category` import 추가, `__all__`에 추가. **기존 보존.**
- **`app/models/base.py`** (그대로 — 상속만): `Base`/`UUIDPrimaryKeyMixin`(uuid7 앱측 default)/`TimestampMixin`(created/updated server_default now())/`SoftDeleteMixin`(deleted_at). **Category가 이 넷 상속**(User와 동일).
- **`app/schemas/base.py`** (그대로 — 상속만): `CamelModel`(alias_generator=to_camel, populate_by_name, from_attributes). `Page`·`CategoryRead`가 상속.
- **`app/core/exceptions.py`** (UPDATE, append): `AppError` + 5개 도메인 예외(DuplicateEmail/InvalidCredentials/InvalidToken/NotAuthenticated/Forbidden). → `InvalidCursorError`(400) **추가**(동일 패턴). 400은 처음 도입이나 핸들러 자동 처리. **기존 보존.**
- **`app/deps.py`** (그대로 — 소비만): `CurrentUser` 별칭(get_current_user) 존재(1.5). categories 라우터가 `CurrentUser` **재사용**. `require_role`은 이 스토리 미사용.
- **`app/core/db.py`** (그대로): `engine`/`SessionLocal`(expire_on_commit=False)/`Base`/`get_db`. Category 모델이 이 `Base` 상속.
- **`app/repositories/users.py`** (그대로 — 패턴 참조): `get_by_email`/`get_by_id`/`create` 패턴을 `CategoryRepository`가 복제.
- **`app/routers/users.py`** (그대로 — 패턴 참조): `/users/me` 라우터(prefix·tags·CurrentUser·operationId 함수명) 패턴을 categories 라우터가 복제.
- **`app/seed.py`** (UPDATE, append): `seed_admin(session)` + `main()` 존재. → `seed_categories(session)` 추가 + `main()`에서 카테고리 시드 독립 실행 배선(Task 9). **`seed_admin` 보존.**
- **`app/core/config.py`** (그대로 — 변경 없음): `Settings`에 DB/JWT/CORS/SEED_ADMIN_* 존재. **카테고리는 신규 필드 0개.**
- **`app/main.py`** (UPDATE, append): `auth_router`·`users_router`·health·핸들러 등록 존재. → `categories_router` include **추가**(users_router 다음). **기존 보존.**
- **`tests/conftest.py`** (그대로 — 재사용): `client`/`db_session`/`client_db`(실 DB SAVEPOINT 롤백, NullPool, expire_on_commit=False). 카테고리 테스트가 `client_db`/`db_session` **그대로 사용**.
- **`pyproject.toml`** (검토만): sqlalchemy/asyncpg/alembic/pydantic/fastapi/uuid7 모두 설치됨. base64는 표준 라이브러리. → **신규 의존성 0건.**
- **`alembic/versions/`** (UPDATE, 신규 파일): `38c2a20deb69`(baseline) → `04c24a1c717d`(users, 현재 head). → `<new>_add_categories_table.py`(down_revision=`04c24a1c717d`) **추가**.

### 아키텍처 준수 (반드시 따를 규약)

- **목록 응답 형식:** `{items: [...], nextCursor: string|null}`. cursor 기반 페이지네이션. 리소스 직접 반환(불필요 래핑 금지, 단 목록은 envelope 허용).
  [Source: architecture.md#Format Patterns (line 297), API Patterns (line 204), Pattern Examples (line 338)]
- **계층:** router(HTTP·검증·Depends) → service(비즈니스·페이지네이션) → repository(DB·`deleted_at IS NULL` 필터). 역방향·라우터 직접 쿼리 금지.
  [Source: architecture.md#Structure Patterns (line 284-289), Anti-Patterns (line 342)]
- **인증:** `OAuth2PasswordBearer` + `Depends(get_current_user)`(=`CurrentUser`). 카테고리 읽기는 인증만(역할 무제한). 권한 최종 시행은 service이나 참조 데이터는 소유권 무관.
  [Source: architecture.md#Authentication & Security (line 191), AR8, 1.5 RBAC 프리미티브]
- **API 패턴:** `/api/v1` 프리픽스, 태그=도메인(categories), operationId=함수명 안정화(`list_categories`). 쿼리=camelCase(`cursor`, `limit`).
  [Source: architecture.md#API & Communication Patterns (line 199-204), Naming (line 267), AR9]
- **에러 envelope:** `{code, message, detail?}` + HTTP status. `code`=기계 판독 안정 식별자, `message`=한국어. 400=invalid_cursor.
  [Source: architecture.md#Format Patterns (line 298-299)]
- **명명:** DB 테이블 복수 snake_case(`categories`), 컬럼 snake_case(`is_active`, `created_at`). Python snake_case 함수, PascalCase 클래스(`Category`/`CategoryRead`/`CategoryRepository`/`CategoryService`), 스키마 PascalCase+접미사. JSON 경계 camelCase(`isActive`, `nextCursor`). PK=`id`(UUIDv7).
  [Source: architecture.md#Naming Patterns (line 256-275)]
- **소프트삭제/비활성:** 카테고리=`is_active`(비활성화, FR24 Epic 6) + `deleted_at`(소프트삭제). 조회 공통 필터 `deleted_at IS NULL` + 활성 목록은 `is_active=true` 추가. 물리삭제 금지.
  [Source: architecture.md#Data Architecture (line 176-179), 참조 무결성 line 179, NFR7]
- **시드:** 기본 카테고리는 seed 스크립트(멱등). 마이그레이션 체인과 직교(스키마/데이터 분리, 1.3 패턴).
  [Source: architecture.md#Data Architecture (line 173), AR5, 1-3 story Task 9]
- **DB 이식성(NFR6):** repository + Alembic로 Phase1→Phase2 코드 변경 없이 이관. UUIDv7 앱측 생성.
  [Source: architecture.md#Data Architecture (line 168-182), AR4]
- **검증:** Pydantic v2(`from_attributes=True`). limit 경계는 Query(ge/le). 서버 검증 신뢰(NFR3).
  [Source: architecture.md#Data Architecture (line 182), Process Patterns (line 319)]

### 라이브러리/버전 (검증 완료 — 그대로 사용)

- FastAPI 0.136.x(`Query`·Generic response_model 지원) · SQLAlchemy 2.0.36(async+asyncpg) · Pydantic 2.10(Generic 모델) · Alembic 1.14+ · asyncpg 0.30+ · uuid7 0.1.0+ · Python 3.12.8. 모두 `.venv` 설치·검증(2026-06-08, Supabase PG17.6 연결 OK).
- **신규 의존성: 없음.** `base64`는 표준 라이브러리. Pydantic Generic·FastAPI Query 모두 기설치 버전 내장.
- **uv 실행(1.2~1.5 계승):** `[tool.uv] python-preference="only-system"`, `uv sync`/`uv run pytest`/`uv run ruff check .`.
  [Source: 1-5 story 라이브러리 섹션, backend-env-setup 메모, architecture.md#Coherence Validation]

### 파일 구조 (생성/수정 위치)

```
apps/api/
  app/
    models/
      __init__.py          (UPDATE) from app.models.category import Category
      category.py          (NEW) Category 모델(name unique, is_active, no is_seed)
    schemas/
      pagination.py        (NEW) Page[T] envelope({items, nextCursor}) — 첫 목록 프리미티브
      category.py          (NEW) CategoryRead
    core/
      pagination.py        (NEW) encode_cursor / decode_cursor (opaque base64)
      exceptions.py        (UPDATE, append) InvalidCursorError(400)
    repositories/
      categories.py        (NEW) CategoryRepository(list_active, get_by_name, create)
    services/
      category.py          (NEW) CategoryService.list_active(cursor, limit) → Page[CategoryRead]
    routers/
      categories.py        (NEW) GET /api/v1/categories (list_categories)
    seed.py                (UPDATE, append) seed_categories(session) + main() 독립 배선
    main.py                (UPDATE, append) categories_router include
    deps.py                (그대로 — CurrentUser 재사용)
  alembic/
    versions/
      <new>_add_categories_table.py  (NEW, autogenerate, down_revision=04c24a1c717d, enum drop 없음)
  tests/
    test_categories_list.py  (NEW) 인증/형식/제외/모든역할/페이지네이션/손상cursor/limit경계
    test_seed_categories.py  (NEW) 또는 test_seed.py(UPDATE) — 카테고리 시드 멱등
    conftest.py              (그대로 — db_session/client_db 재사용)
  # config.py / .env / pyproject.toml: 변경 없음(신규 env·의존성 0)
```
[Source: architecture.md#Complete Project Directory Structure (line 349-426), 1-5 story 파일 구조]

### 테스트 표준

- pytest + `pytest-asyncio`(`asyncio_mode=auto`) + httpx `AsyncClient`(`ASGITransport`) + `dependency_overrides`. **도메인/보호 라우트 테스트는 실 DB + SAVEPOINT 롤백**(`db_session`/`client_db` 재사용 — fake repo 금지: is_active/deleted_at 필터·keyset 정렬을 실 DB로 증명).
- 핵심 경로 우선: 인증 차단·envelope 형식·비활성/삭제 제외·**모든 역할 허용(admin 포함)**·페이지네이션 실동작(중복/누락 0)·손상 cursor 400·limit 경계 422. 시드 멱등.
- 토큰은 `create_access_token(user.id, user.user_role)`(1.4) 직접 생성. 카테고리는 `db_session` 직접 insert 또는 `seed_categories` 호출. CI(`pytest`)는 Story 1.8에서 GitHub Actions + `DATABASE_URL` 시크릿 연결.
  [Source: architecture.md#Structure Patterns (line 289), 1-3/1-5 story 테스트 표준, conftest.py docstring]

### Project Structure Notes

- 정합: `categories` 도메인이 router/service/repository/model/schema로 분리되고 `Page` envelope가 `schemas/pagination.py`, cursor 헬퍼가 `core/pagination.py`에 사는 것은 architecture 디렉터리 구조(line 420-426)·계층 규약(line 284-288) 그대로. categories 라우터·모델은 architecture가 이미 예고(line 199·420·422·450).
- 변이 없음: 신규 패턴(목록 envelope, opaque cursor, 400 status)은 architecture가 이미 명시한 것(line 204·297)의 **첫 구현**. 새 아키텍처 결정 없음. `Page`/cursor 규약은 Epic 2+가 상속할 선례.
- `apps/api`는 Turborepo 그래프 외부(uv/uvicorn 별도 파이프라인) — 1.2~1.5 계승.

### 이전 스토리(1.3/1.4/1.5) 학습 / 정합

- **1.3 도메인 슬라이스 패턴 복제:** router→service→repository, `CamelModel` 직렬화, 실 DB+SAVEPOINT 롤백 테스트, 멱등 시드(스키마/데이터 직교)를 categories에 그대로 적용. `CategoryRepository`=`UserRepository` 구조 미러.
- **1.3 마이그레이션 함정 계승·차이:** 모델 import(autogen 감지)·멱등 up/down/up 검증은 계승. **단 enum drop 보정은 categories에 해당 없음**(enum 컬럼 부재) — 1.3을 무지성 복제하지 말 것(함정 #2).
- **1.5 RBAC 프리미티브 소비:** `CurrentUser`(get_current_user, 매-요청 재조회로 비활성/삭제 즉시 차단)를 categories 라우터가 재사용. 미인증/무효 토큰 401은 1.5 가드가 자동 처리 — 카테고리 라우터는 인증 로직 0줄(주입만). `require_role`는 미사용(모든 역할 허용, 결정 #2).
- **1.5 500 누수 방지 철학 계승:** 1.5가 payload 형식 오류를 401로 정규화했듯, categories는 손상 cursor를 400(`invalid_cursor`)으로 정규화 — 사용자 입력 오류가 500으로 새지 않게.
- **deferred-work.md 무관 확인:** 소프트삭제 이메일 재가입·IntegrityError 매핑·CORS wildcard·enum drop checkfirst는 가입/users/CORS 경로 — categories와 무관. 단 categories도 `deleted_at IS NULL` 공통 필터를 지켜 소프트삭제 일관성 원칙 공유. (categories `name` unique도 1.3 email과 동일하게 비-partial 유니크 — 소프트삭제 행 잔존 시 재시드 충돌 가능성은 Epic 6 카테고리 삭제 플로우 도입 시 partial unique 채택 여부와 함께 결정, 현재 도달 불가.)
  [Source: 1-3-signup-seed-admin.md, 1-5-rbac.md, deferred-work.md]

### References

- [Source: epics.md#Story 1.6: 카테고리 엔티티·조회 API·시드 (line 295-313)] — 3개 AC 원본(BDD): categories 테이블+`{items,nextCursor}` 조회, 기본 카테고리 시드, 고객·고수 읽기 허용·CRUD 범위 외
- [Source: epics.md#Story 2.1 (line 368-390), Story 3.1 (line 441-463)] — 카테고리 소비처(요청 생성 categoryId, 고수 pro_categories) — 이 스토리가 충족할 의존성·범위 경계
- [Source: architecture.md#Format Patterns (line 295-302)] — 목록 `{items, nextCursor}`, 에러 envelope, camelCase 경계
- [Source: architecture.md#API & Communication Patterns (line 197-207)] — `/api/v1`, categories 태그, cursor 페이지네이션, operationId
- [Source: architecture.md#Pattern Examples (line 337-345)] — 목록 cursor 예시·anti-pattern(라우터 직접 쿼리 금지)
- [Source: architecture.md#Data Architecture (line 168-182)] — SQLAlchemy async, Alembic, UUIDv7, 소프트삭제/비활성, 참조 무결성(카테고리), 시드
- [Source: architecture.md#Structure Patterns (line 282-289)] — router→service→repository, 트랜잭션 롤백 테스트
- [Source: architecture.md#Naming Patterns (line 256-275)] — categories 테이블, camelCase 경계, 쿼리 파라미터 camel
- [Source: architecture.md#Complete Project Directory Structure (line 349-426)] — categories 라우터/모델 위치, schemas/core 배치
- [Source: AR5, AR8, AR9, AR12 (epics.md line 79-89)] — 시드, REST 단일 경유, Orval/operationId, 에러 envelope/cursor 페이지네이션 / [Source: FR5, FR9, FR24, NFR3/NFR6] — 카테고리 소비처·CRUD 범위·서버 검증·이식성
- [Source: 1-3-signup-seed-admin.md] — 도메인 슬라이스/시드/마이그레이션 선례, enum drop 함정(차이 주의)
- [Source: 1-5-rbac.md] — CurrentUser/get_current_user 재조회, 500 누수 방지 철학, 격리 테스트·실 DB 롤백 패턴
- [Source: backend-env-setup 메모, manual-setup-checkpoints 메모] — uv only-system, .env 검증, AR23 수동 체크포인트 선안내 원칙

## ⚡ 수동 설정 체크포인트 (AR23 — dev-story 진입 전 KTH 확인)

- **신규 외부 설정 없음.** 카테고리 조회·시드는 기존 `apps/api/.env`의 `DATABASE_URL`(1.2 검증)과 신규 `categories` 테이블(이 스토리 마이그레이션)만 사용한다. **카테고리 시드는 시크릿/env를 요구하지 않는다**(기본값 하드코딩 — 관리자 시드와의 핵심 차이, 결정 #4). Supabase/Railway/JWT 추가 작업 불요(1.5와 동일).
- **검증용(선택):** 마이그레이션(`uv run alembic upgrade head`) 후 `uv run python -m app.seed`로 기본 카테고리 시드 → 로그인 access 토큰으로 `GET /api/v1/categories` 호출 시 시드된 활성 카테고리가 `{items, nextCursor}`로 반환됨을 확인. 테스트는 savepoint 내 자체 시드로 동작하므로 별도 시드 없이 통과한다.
- **확인 요청:** 위 "신규 설정 없음"이 맞는지(=`.env`의 `DATABASE_URL`이 여전히 유효한지) KTH가 확인하면 dev-story 진입. 기본 카테고리 목록(청소/정리수납/이사/인테리어/수리/설치 등)을 변경·추가하고 싶으면 dev-story 진입 전 알려주세요(seed.py 상수에 반영).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Claude Opus 4.8, 1M context) — bmad-dev-story 워크플로우

### Debug Log References

- 베이스라인 검증: `uv run pytest -q` → 56 passed (구현 전 그린 확인, DB 연결 정상)
- 마이그레이션 멱등: `alembic upgrade head → downgrade -1 → upgrade head` 깨끗이 통과
  (enum drop을 추가하지 않았기에 down→up 재적용 성공 — cargo-cult 회피 검증)
- 최종 검증: `uv run pytest -q` → 71 passed (회귀 0), `uv run ruff check .` → All checks passed

### Completion Notes List

- **Task 1~9 전부 스토리 명세대로 구현** — 새 아키텍처 결정 없음(architecture가 이미 예고한 패턴의 첫 구현).
- **첫 목록 응답 프리미티브 확립:** `Page[T]`(`{items, nextCursor}` envelope) + opaque cursor 2함수
  (`encode_cursor`/`decode_cursor`). 일반화된 keyset 엔진은 만들지 않음(결정 #1 절제 준수) —
  categories 전용 단일 컬럼 keyset(`id` ASC, `id > after_id`, `LIMIT limit+1`).
- **인증은 `CurrentUser`(모든 역할), `require_role` 아님**(결정 #2) — customer/pro/admin 3역할
  parametrize 테스트로 admin 비배제 증명.
- **손상 cursor 400 정규화:** 비-base64는 `decode_cursor`가, base64-but-not-UUID는 service가
  `InvalidCursorError`(400)로 변환 — 두 경로 모두 테스트로 500 누수 없음 증명.
- **`next_cursor` 경계 = `page_rows[-1].id`**(잘린 리스트의 마지막, limit+1번째 행 아님) — 트랩 #4 회피.
- **마이그레이션:** autogen 검수 후 enum drop 보정을 **추가하지 않음**(categories는 enum 없음) —
  down→up 재적용 성공으로 검증.
- **시드 멱등 + env 독립:** `seed_categories`는 SEED_* 불요로 `main()`에서 관리자 시드보다 선행·독립
  실행(admin 실패를 경고로 격하). 기본 카테고리는 KTH 확인 후 스토리 기본값(청소/정리수납/이사/
  인테리어/수리/설치) 그대로 채택.
- **신규 의존성 0건**(base64는 표준 라이브러리), **config.py/.env 변경 0건**(결정 #4).

### File List

**신규(NEW)**
- `apps/api/app/models/category.py` — Category 모델(name unique+index, is_active, is_seed 없음)
- `apps/api/app/schemas/pagination.py` — `Page[T]` 페이지네이션 envelope(첫 목록 프리미티브)
- `apps/api/app/schemas/category.py` — `CategoryRead`(deleted_at 미포함 안전 표현)
- `apps/api/app/core/pagination.py` — `encode_cursor`/`decode_cursor`(opaque base64)
- `apps/api/app/repositories/categories.py` — `CategoryRepository`(list_active/get_by_name/create)
- `apps/api/app/services/category.py` — `CategoryService.list_active` → `Page[CategoryRead]`
- `apps/api/app/routers/categories.py` — `GET /api/v1/categories`(list_categories, CurrentUser)
- `apps/api/alembic/versions/4b715631d65e_add_categories_table.py` — categories 테이블 마이그레이션
  (down_revision=04c24a1c717d, enum drop 없음)
- `apps/api/tests/test_categories_list.py` — 인증/형식/제외/모든역할/페이지네이션/손상cursor/limit경계
- `apps/api/tests/test_seed_categories.py` — 카테고리 시드 멱등·기본 집합·전부 활성

**수정(UPDATE)**
- `apps/api/app/models/__init__.py` — `Category` import + `__all__` 추가(기존 User 보존)
- `apps/api/app/core/exceptions.py` — `InvalidCursorError`(400) 추가(기존 예외 보존)
- `apps/api/app/seed.py` — `DEFAULT_CATEGORIES` 상수 + `seed_categories` + `main()` 독립 배선
- `apps/api/app/main.py` — `categories_router` include(기존 라우터 보존)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 1-6 상태 갱신

### Change Log

| 날짜 | 변경 | 작성자 |
|------|------|--------|
| 2026-06-08 | Story 1.6 초안 생성 — 카테고리 엔티티·조회 API·시드 + 첫 목록 응답 프리미티브(Page envelope/opaque cursor). Status → ready-for-dev | create-story (Opus 4.8) |
| 2026-06-08 | Task 1~10 구현 완료 — Category 모델/마이그레이션, `Page[T]` envelope + opaque cursor, CategoryRepository/Service/router, InvalidCursorError(400), 멱등 카테고리 시드. 71 tests passed(회귀 0), ruff clean. Status → review | dev-story (Opus 4.8) |

### Review Findings (code-review 2026-06-08)

3-레이어 적대적 리뷰(Blind Hunter / Edge Case Hunter / Acceptance Auditor) 결과. Acceptance Auditor는 **AC 위반 없음 — 스펙 충실 구현**으로 판정. 페이지네이션 cursor 정확성(limit+1 keyset, has_more, next_cursor=page_rows[-1].id), 손상 cursor→400 정규화, is_active AND deleted_at 둘 다 필터, CurrentUser(모든 역할), enum drop cargo-cult 회피 등 핵심 위험 지점은 모두 정상 검증됨.

- [x] [Review][Patch] 시드 테스트 동어반복(tautological) assertion — `"신규"`/`"skip"`은 메시지 리터럴에 항상 존재해 created/skipped 카운트를 실제로 검증하지 못함. 숫자(`f"신규 {len(DEFAULT_CATEGORIES)}개"`/`"신규 0개"`/`f"기존 {len}개"`)를 단정하도록 강화 — **적용 완료(2026-06-08), 3 passed** [apps/api/tests/test_seed_categories.py:22-23,36,41-42] (low — 멱등성 자체는 `count == len` / 이름별 `n == 1` 검사로 이미 증명됨)
- [x] [Review][Defer] **시드 충돌 안전성: 비-partial unique index** — ⚠️ Blind Hunter·Edge Case Hunter **둘 다 Critical/High로 평가**. `name` unique 인덱스가 전역(non-partial)인데 `get_by_name`은 `deleted_at IS NULL`로 필터 → 소프트삭제된 동명 카테고리 잔존 시 재시드가 IntegrityError→ValueError→`sys.exit(1)`로 영구 차단(AC2 멱등성 위배). 동시 실행 시에도 배치 단일 commit이 한 충돌에 전부 롤백(EH2)·멱등 대신 실패(EH3). [apps/api/app/seed.py:79-107, apps/api/alembic/versions/4b715631d65e_add_categories_table.py] — **deferred**: 스펙 Dev Notes(line 282)가 1.3 email-unique 선례와 동일하게 **명시적으로 보류**한 사항. `categories` 테이블은 이 마이그레이션에서 처음 생성되고 1.6 범위에 카테고리 소프트삭제 경로가 없어 **현재 도달 불가**. Epic 6(카테고리 삭제) 도입 시 partial unique 인덱스(`postgresql_where=text("deleted_at IS NULL")`) + 동시성은 ON CONFLICT DO NOTHING 검토.
- ~~[Review][Dismiss]~~ `app/models/__init__.py:1` 로드맵 주석이 미존재 모델(service_request/quote/chat_room/message) 나열 — 의도적 향후 모델 주석("Story 1.2~4")으로 무해. 노이즈로 기각.
