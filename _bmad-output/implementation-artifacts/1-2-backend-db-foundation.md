---
baseline_commit: NO_VCS
---
# Story 1.2: 백엔드 & DB 기반 (FastAPI + SQLAlchemy + Alembic)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 개발 에이전트,
I want FastAPI 앱과 비동기 DB 접근 계층(SQLAlchemy async + asyncpg), Alembic 마이그레이션, 공통 코어(설정·DB·에러 envelope)를 구축하기를,
So that 이후 도메인 기능(1.3 users부터)이 일관된 계층·규약 위에서 데이터에 접근할 수 있다.

## Acceptance Criteria

**AC1 — core 구성 + 앱 기동 + DB 포함 헬스**
**Given** apps/api 스켈레톤에서
**When** `app/core/db.py`에 async 엔진/세션(asyncpg)과 `get_db` 의존성을, `app/core/config.py`에 pydantic-settings 기반 설정(DATABASE_URL, JWT_SECRET, CORS_ORIGINS)을 구성하면
**Then** `/api/v1` 프리픽스와 `CORSMiddleware`(명시 오리진)가 등록된 FastAPI 앱이 기동되고, `GET /api/v1/health`가 DB 연결(`SELECT 1`)을 포함해 200을 반환한다.

**AC2 — Alembic 멱등 마이그레이션**
**Given** Alembic이 초기화될 때
**When** `alembic upgrade head`를 실행하면
**Then** 마이그레이션이 멱등하게 적용되어 동일 스키마가 재생성되고(NFR6), 스키마는 코드로 버전 관리된다.

**AC3 — 전역 예외 핸들러 + 에러 envelope**
**Given** API가 오류를 반환할 때
**When** service 계층이 도메인 예외를 던지면
**Then** 전역 예외 핸들러가 표준 envelope `{code, message, detail?}` + 적절한 HTTP status로 변환하고, `message`는 한국어로 노출 가능하다(AR12, NFR2).

**AC4 — UUIDv7 앱측 생성 정책**
**Given** PK 생성 정책(G4/AR4)에서
**When** 모델 PK를 정의하면
**Then** UUIDv7을 Python `uuid7` 라이브러리로 앱 측에서 생성하며 DB `DEFAULT uuidv7()`(server_default)을 사용하지 않는다(Supabase PG17 호환·이관 안전).

## Tasks / Subtasks

- [x] **Task 1 — core/config.py: pydantic-settings 설정** (AC: 1)
  - [x] `Settings(BaseSettings)` 정의: `database_url: str`, `jwt_secret: str`, `cors_origins: list[str]`, `access_token_expire_minutes: int = 30`, `refresh_token_expire_days: int = 14`. `model_config = SettingsConfigDict(env_file=".env", extra="ignore")`.
  - [x] ⚠️ **CORS_ORIGINS 파싱 함정 해결(필수):** pydantic-settings v2는 `list[str]` 필드에 대해 validator 실행 *전에* env 값을 `json.loads`로 파싱하려 시도 → 콤마 구분 문자열(`http://localhost:3000,http://localhost:3001`)에서 `SettingsError`로 크래시. `field_validator("cors_origins", mode="before")`로 str이면 `[s.strip() for s in v.split(",") if s.strip()]` 분리 처리(이미 list면 그대로). `.env`의 콤마 포맷을 바꾸지 말 것(.env.example 유지).
  - [x] 모듈 수준 `settings = Settings()` 싱글톤 export(또는 `@lru_cache` get_settings). `jwt_secret`은 1.4/1.5가 소비 — 이 스토리에선 필드 선언만, JWT 로직 구현 금지.
- [x] **Task 2 — core/db.py: async 엔진/세션 + get_db** (AC: 1)
  - [x] `create_async_engine(settings.database_url, ...)`, `async_sessionmaker(engine, expire_on_commit=False)`.
  - [x] `async def get_db() -> AsyncIterator[AsyncSession]:` — `async with SessionLocal() as session: yield session`(FastAPI Depends용).
  - [x] `Base = declarative_base()`(또는 `class Base(DeclarativeBase)`, SQLAlchemy 2.0 스타일). alembic env.py가 `Base.metadata`를 target으로 참조.
- [x] **Task 3 — models 공통 mixin (UUIDv7 PK + 타임스탬프 + 소프트삭제)** (AC: 4)
  - [x] `app/models/base.py`: `Base` + 재사용 mixin. PK: `id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)` — **server_default 금지**(G4/AR4). 컬럼 타입은 PG `UUID(as_uuid=True)`.
  - [x] 타임스탬프 mixin: `created_at`(default=now, server_default 가능), `updated_at`(onupdate), `deleted_at: Mapped[datetime | None]`(소프트삭제, nullable).
  - [x] import는 반드시 `from uuid_extensions import uuid7`(아래 함정 참조). `uuid7()`이 `uuid.UUID`를 반환함을 확인 → 컬럼 callable default(`default=uuid7`)로 동작.
  - [x] ⚠️ 이 스토리는 **도메인 테이블을 만들지 않는다.** mixin/Base는 1.3(users)부터 소비할 기반만 확립.
- [x] **Task 4 — Alembic 초기화(async) + baseline 마이그레이션** (AC: 2)
  - [x] `uv run alembic init -t async alembic` — **반드시 async 템플릿**(기본 sync 템플릿은 asyncpg에서 실패).
  - [x] `alembic/env.py`: `target_metadata = Base.metadata`, DB URL은 `alembic.ini`의 리터럴 `sqlalchemy.url`이 아니라 `Settings.database_url`에서 주입(`config.set_main_option` 또는 직접 engine 사용).
  - [x] `alembic.ini`의 `sqlalchemy.url`은 비우거나 플레이스홀더(시크릿 커밋 금지).
  - [x] baseline revision 생성: 도메인 모델이 없으므로 **빈(또는 baseline-only) revision** — `users` 등 테이블을 지어내지 말 것. `alembic upgrade head`가 깨끗하게 통과하면 충족.
  - [x] 멱등 검증: `upgrade head` 두 번/`downgrade`+`upgrade` 재현 확인.
- [x] **Task 5 — main.py: /api/v1 라우터 + CORS + DB 헬스 + 전역 예외 핸들러** (AC: 1, 3)
  - [x] `APIRouter(prefix="/api/v1")` 구성, `app.include_router(...)`. 기존 `GET /api/v1/health` 경로 유지하되 `Depends(get_db)`로 `await session.execute(text("SELECT 1"))` 실행해 DB 연결 포함 200 반환.
  - [x] `CORSMiddleware` 등록 — `allow_origins=settings.cors_origins`(파싱된 list), 운영 `*` 금지(AR14).
  - [x] 도메인 예외 베이스(`app/core/exceptions.py`: `AppError(code, message, status_code, detail=None)`) + `@app.exception_handler(AppError)`가 `JSONResponse(status_code=..., content={"code","message","detail?"})`로 변환. `RequestValidationError`/`HTTPException`도 동일 envelope로 일관 변환(AR12). `message`는 한국어 노출 가능.
- [x] **Task 6 — 테스트(pytest + httpx AsyncClient)** (AC: 1, 3)
  - [x] `tests/test_health.py`: `GET /api/v1/health` 200, body 형식 검증.
  - [x] `tests/test_error_envelope.py`: 의도적 `AppError` 발생 라우트(테스트용) 또는 존재하지 않는 경로/검증 실패가 `{code, message}` envelope로 반환되는지 검증.
  - [x] httpx `ASGITransport` + `AsyncClient`로 앱 직접 호출. DB 의존 테스트는 `app.dependency_overrides[get_db]`로 격리(실 DB 없이 헬스 경로 검증 가능하도록 override 또는 테스트 DB 결정 — 과설계 금지, 헬스는 SELECT 1만).

## Dev Notes

### 🎯 스코프 경계 (가장 중요 — 범위 침범 금지)

이 스토리는 **인프라 전용. 도메인 테이블 0개.**
- ❌ `users` 등 어떤 도메인 테이블도 만들지 않는다 — `users`는 **Story 1.3**(epics.md Story 1.3). baseline 마이그레이션은 의도적으로 비어있다.
- ❌ Argon2/JWT **로직** 구현 안 함 — `config.py`는 `JWT_SECRET` 설정 *필드만* 선언. `core/security.py`(Argon2 해싱·JWT 발급/검증)와 `deps.py`(get_current_user/require_role)는 **Story 1.4/1.5** 범위(현재 `deps.py` 주석이 "Story 1.5"라고 명시).
- ✅ 1.3+가 소비할 **기반만** 확립: SQLAlchemy `Base` + UUIDv7 PK mixin + `created_at/updated_at/deleted_at` 타임스탬프 mixin, async 엔진/세션, Alembic 인프라, 에러 envelope, DB 헬스.

### 현재 코드 상태 (UPDATE 대상 — 보존할 것)

스토리 1.1이 디렉터리 골격 + 스텁을 생성함. 아래는 현재 실제 상태이며, 덮어쓰지 말고 확장한다:

- **`app/main.py`** (UPDATE): 현재 `FastAPI(title="gosoom API", version="0.0.0")` + `GET /api/v1/health`가 `{"status":"ok"}` 스텁 반환. 주석에 "Story 1.2에서 DB 연결 점검 포함하도록 확장"이라고 이미 예고됨. → CORS·예외 핸들러·DB 헬스로 확장하되 앱 title/version·헬스 경로는 유지.
- **`app/deps.py`** (그대로 둠): JWT/require_role은 Story 1.5. 이 스토리에서 건드리지 않는다.
- **`app/core/__init__.py`, `app/models/__init__.py`** 등: 빈 `__init__.py`만 존재 → config.py/db.py/exceptions.py, models/base.py를 **신규** 추가.
- **`pyproject.toml`** (검토만, 변경 최소): 필요한 의존성 이미 선언·설치·검증됨 — `sqlalchemy[asyncio]>=2.0.36`, `asyncpg>=0.30`, `alembic>=1.14`, `pydantic-settings>=2.7`, `pwdlib[argon2]`, `pyjwt`, `uuid7>=0.1.0`. dev: pytest, pytest-asyncio(`asyncio_mode=auto`), httpx, ruff. **새 패키지 추가는 원칙적으로 불필요**(SQLAlchemy의 `text` 등 표준 사용). 추가 시 `uv add`로.
- **`.env`** (이미 구성·검증됨): 실제 Supabase Session pooler asyncpg URL + 64자 JWT_SECRET 채워져 있음(2026-06-08 연결 SELECT 성공 확인). 커밋 금지. `.env.example`은 포맷 참조(콤마 구분 CORS_ORIGINS).
- **`alembic.ini` / `alembic/`**: **아직 없음** → Task 4에서 `alembic init -t async`로 생성.

### ⚠️ 알려진 함정 (런타임 디버깅 전에 미리 적용 — 고가치)

1. **pydantic-settings v2 리스트 파싱 (가장 흔한 실패):** `cors_origins: list[str]`은 validator 전에 env 문자열을 JSON으로 디코드 시도 → 콤마 구분 값에서 크래시. → `field_validator(mode="before")`로 str split 처리(Task 1).
2. **Alembic async 템플릿:** 기본(sync) 템플릿은 asyncpg URL에서 실패. 반드시 `alembic init -t async`(Task 4).
3. **uuid7 import 경로:** PyPI `uuid7` 패키지의 모듈명은 `uuid_extensions`. `import uuid7`이 아니라 **`from uuid_extensions import uuid7`**. `uuid7()` → `uuid.UUID` 반환이므로 `mapped_column(default=uuid7)` callable default로 동작. server_default 금지(G4/AR4).
4. **uv 실행:** 이 PC는 uv managed standalone 3.12 빌드 실행 불가(0xC0E90002) → `pyproject.toml [tool.uv] python-preference="only-system"`로 시스템 python.org 3.12 강제. `uv sync` / `uv run ...`으로 실행(README 참조).

### 아키텍처 준수 (반드시 따를 규약)

- **계층:** router(HTTP) → service(비즈니스/권한/트랜잭션) → repository(DB). 역방향 호출 금지. 이 스토리는 router(health)·core까지만; service/repository는 도메인 스토리에서.
  [Source: architecture.md#Structure Patterns]
- **명명:** DB=snake_case 복수 테이블, 컬럼 snake_case(`created_at`/`deleted_at`/`is_active`). Python=snake_case 함수/변수, PascalCase 클래스. PK=`id`(UUIDv7).
  [Source: architecture.md#Naming Patterns]
- **에러 envelope:** `{code, message, detail?}` + HTTP status. `code`=기계 판독 안정 식별자, `message`=한국어 노출 가능. 성공 응답은 리소스 직접 반환(불필요 래핑 금지), 목록은 `{items, nextCursor}`(이 스토리엔 목록 없음).
  [Source: architecture.md#Format Patterns]
- **소프트삭제:** 모든 조회는 `deleted_at IS NULL` 공통 필터(repository 계층) — 도메인 스토리에서 적용. 여기선 mixin에 `deleted_at` 컬럼만 마련.
  [Source: architecture.md#Data Boundaries]
- **DB 이식성(NFR6):** repository + Alembic로 Phase1(Supabase)→Phase2(Railway) 코드 변경 없이 이관. `DATABASE_URL`만 상이. 확장 의존(`pg_uuidv7` 등) 회피 위해 UUIDv7 앱측 생성.
  [Source: architecture.md#Data Architecture, #Decision Impact Analysis]
- **검증/직렬화 경계:** Pydantic v2. 내부 속성 snake_case, 직렬화 경계에서만 camelCase(`alias_generator=to_camel`, `populate_by_name=True`) — 도메인 스키마 등장 시 적용. 이 스토리엔 응답 스키마 거의 없음.
  [Source: architecture.md#Naming Patterns (API)]

### 라이브러리/버전 (검증 완료 — 그대로 사용)

- FastAPI 0.136.x · SQLAlchemy 2.0.36(async+asyncpg) · Pydantic 2.10 / pydantic-settings 2.7+ · Alembic 1.14+ · asyncpg 0.30+ · Python 3.12.8.
- 모두 `.venv`에 설치·검증됨(2026-06-08, Supabase PG17.6 async 연결 SELECT 성공). 새 버전 탐색/업그레이드 불필요.
  [Source: architecture.md#Coherence Validation, backend-env-setup 메모]

### 파일 구조 (생성 위치)

```
apps/api/
  app/
    main.py            (UPDATE) /api/v1 라우터, CORSMiddleware, 예외 핸들러, DB 헬스
    core/
      config.py        (NEW) pydantic-settings Settings
      db.py            (NEW) async engine/session, get_db, Base
      exceptions.py    (NEW) AppError 베이스 + (선택) 도메인 예외 골격
    models/
      base.py          (NEW) Base + UUIDv7 PK mixin + 타임스탬프/소프트삭제 mixin
  alembic.ini          (NEW, init -t async)
  alembic/
    env.py             (NEW) target_metadata=Base.metadata, URL=Settings 주입
    versions/          (NEW) baseline revision(빈/baseline-only)
  tests/
    test_health.py         (NEW)
    test_error_envelope.py (NEW)
```
[Source: architecture.md#Complete Project Directory Structure]

### 테스트 표준

- pytest + `pytest-asyncio`(`asyncio_mode=auto`, 이미 설정) + httpx `AsyncClient`(`ASGITransport`로 앱 직접 호출) + `dependency_overrides`로 의존성 격리.
- 핵심 경로 우선(헬스·에러 envelope). 커버리지 점진(AR20). CI(`pytest`)는 Story 1.8에서 GitHub Actions로 연결.
  [Source: architecture.md#Structure Patterns (Backend tests), #Infrastructure & Deployment]

### Project Structure Notes

- 정합: 위 파일 배치는 architecture.md의 `apps/api` 트리와 일치(core/config·db·security, models, alembic). 단 `core/security.py`는 의도적으로 이 스토리에서 제외(1.4/1.5).
- 변이: 없음. 1.1에서 만든 골격을 그대로 채우는 방향.
- `apps/api`는 Turborepo 태스크 그래프 **외부** — JS 앱과 별도 파이프라인(`uv`/`uvicorn`). 루트 `pnpm turbo`와 무관.

### References

- [Source: epics.md#Story 1.2: 백엔드 & DB 기반 (FastAPI + SQLAlchemy + Alembic)] — 4개 AC 원본(BDD)
- [Source: architecture.md#Data Architecture] — SQLAlchemy async/asyncpg, Alembic, UUIDv7, 소프트삭제, 상태기계 service 시행
- [Source: architecture.md#Authentication & Security] — JWT_SECRET 설정 근거(로직은 1.4/1.5)
- [Source: architecture.md#API & Communication Patterns] — `/api/v1`, 에러 envelope, OpenAPI
- [Source: architecture.md#Implementation Patterns & Consistency Rules] — 명명·구조·포맷·통신·프로세스 패턴
- [Source: architecture.md#Project Structure & Boundaries] — 디렉터리 트리, 계층/데이터 경계
- [Source: architecture.md#Gap Analysis Results (G4 UUIDv7)] — PG17 server_default 금지, 앱측 생성 근거
- [Source: AR3, AR4, AR8, AR12, AR14 (epics.md#Additional Requirements)] — DB 접근 계층·UUIDv7·패턴 A·에러 envelope·CORS
- [Source: backend-env-setup 메모] — uv only-system, uuid_extensions import, .env 검증 사실

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — BMad dev-story 워크플로우

### Debug Log References

- **CORS 파싱 함정 #1 선제 검증:** config.py 작성 직후 `uv run python -c "from app.core.config import settings; print(settings.cors_origins)"` → `['http://localhost:3000', 'http://localhost:3001']` 정상 출력. `field_validator(mode="before")` 단독으론 pydantic-settings v2의 소스 레벨 JSON 선디코드를 막지 못할 수 있어 `Annotated[list[str], NoDecode]` 병행 적용으로 확실히 회피.
- **alembic.ini cp949 인코딩 이슈:** alembic.ini에 한국어 주석을 넣자 configparser가 시스템 인코딩(cp949)으로 읽어 `UnicodeDecodeError` 발생 → ini 주석을 ASCII(영문)로 교체해 해결. (.py 파일은 UTF-8이라 한국어 주석 유지)
- **AC2 멱등 검증:** `upgrade head`(적용) → `current`(head 확인) → `upgrade head`(2회차 no-op) → `downgrade base` → `upgrade head`(재현) 모두 깨끗이 통과(실 Supabase PG17).
- **AC1 라이브 증명:** get_db override 없이 실제 Supabase로 헬스 호출 → `200 {'status':'ok','db':'ok'}`. 가짜 세션 단위테스트는 라우팅만 증명하므로 실 DB 연결을 별도 라이브 점검으로 보강.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- ✅ **AC1** core/config(pydantic-settings)·core/db(async 엔진/세션·get_db·Base) 구성, `/api/v1` + CORSMiddleware(명시 오리진) 등록, `GET /api/v1/health`가 실 DB `SELECT 1` 포함 200 반환(라이브 확인).
- ✅ **AC2** Alembic async 템플릿(`init -t async`) 초기화, env.py가 `Settings.database_url` 주입·`Base.metadata` target, 빈 baseline revision로 `upgrade head` 멱등·재현 통과. alembic.ini의 `sqlalchemy.url`은 비움(시크릿 커밋 금지).
- ✅ **AC3** `AppError(code,message,status_code,detail)` 베이스 + 전역 핸들러 3종(AppError/RequestValidationError/HTTPException)이 모두 `{code, message, detail?}` envelope로 일관 변환. message 한국어 노출 가능. 핸들러 등록을 `register_exception_handlers(app)`로 추출해 테스트가 격리 앱에서 검증(prod 라우트 무오염).
- ✅ **AC4** UUIDv7 PK는 `from uuid_extensions import uuid7` + `mapped_column(default=uuid7)` 앱 측 생성, **server_default 미사용**(G4/AR4). 타임스탬프/소프트삭제 mixin 동봉. 도메인 테이블은 0개(스코프 준수, users는 1.3).
- 검증: `uv run pytest` 5 passed, `uv run ruff check` All checks passed(alembic 생성 마이그레이션은 per-file-ignore F401).
- 스코프 준수: deps.py(1.5)·security(1.4/1.5) 미구현, JWT는 설정 필드만 선언.

### File List

**신규(NEW)**
- `apps/api/app/core/config.py` — pydantic-settings Settings(+CORS NoDecode/validator)
- `apps/api/app/core/db.py` — async engine/session, get_db, Base
- `apps/api/app/core/exceptions.py` — AppError 베이스 + envelope 직렬화
- `apps/api/app/models/base.py` — Base 재export + UUIDv7 PK/타임스탬프/소프트삭제 mixin
- `apps/api/alembic.ini` — Alembic 설정(sqlalchemy.url 비움)
- `apps/api/alembic/env.py` — Settings URL 주입, Base.metadata target (생성 후 수정)
- `apps/api/alembic/README`, `apps/api/alembic/script.py.mako` — alembic init 생성물
- `apps/api/alembic/versions/38c2a20deb69_baseline.py` — 빈 baseline revision
- `apps/api/tests/conftest.py` — httpx AsyncClient + get_db override 픽스처
- `apps/api/tests/test_health.py` — 헬스 200·형식 검증
- `apps/api/tests/test_error_envelope.py` — AppError/검증/HTTPException envelope 검증

**수정(UPDATE)**
- `apps/api/app/main.py` — /api/v1 라우터·CORS·예외 핸들러·DB 헬스로 확장
- `apps/api/pyproject.toml` — ruff per-file-ignores(alembic/versions F401)
- `_bmad-output/implementation-artifacts/1-2-backend-db-foundation.md` — 진행/완료 기록

## Change Log

- 2026-06-08: Story 1.2 구현 완료 — FastAPI core(config/db/exceptions), UUIDv7 PK mixin, Alembic async + 빈 baseline(멱등), 전역 에러 envelope, DB 포함 헬스. 테스트 5 passed, ruff clean. Status → review.

### Review Findings (code review 2026-06-08)

3-레이어 적대적 리뷰(Blind Hunter / Edge Case Hunter / Acceptance Auditor) 결과. 4개 AC 모두 코드 레벨 충족·스코프 준수 확인. AC를 깨는 위반은 없으며 아래는 견고성/일관성 개선 항목.

**Patch (적용 완료 — pytest 5 passed · ruff clean · alembic current OK)**
- [x] [Review][Patch] (Decision 해결: 옵션1) 미등록 예외 envelope 일관성 — generic `Exception` 핸들러 추가로 모든 미처리 예외를 `{code:"internal_error", message}`(500) envelope로 변환하고, 헬스 DB 실패는 `503 {db:"fail"}` 명시 반환(AR12 완전 일관) [apps/api/app/main.py]
- [x] [Review][Patch] AppError 핸들러가 detail을 jsonable_encode하지 않아 UUID/datetime detail에서 렌더 시 500 → `jsonable_encoder(exc.to_envelope())`로 수정 [apps/api/app/main.py]
- [x] [Review][Patch] Alembic env.py가 `set_main_option`으로 URL 주입 → DB URL `%` 보간 크래시 → ini 우회, settings에서 직접 URL 주입(offline/online 모두)으로 수정 [apps/api/alembic/env.py]
- [x] [Review][Patch] HTTPException 핸들러: `str(exc.detail)` 깨짐 + `exc.headers` 누락 → str 여부 분기(구조화 detail 보존)·`headers=exc.headers` 전달로 수정 [apps/api/app/main.py]
- [x] [Review][Patch] `/api/v1`를 APIRouter(prefix) 패턴으로 분리(스펙 Task 5) → `APIRouter(prefix="/api/v1")` + `include_router`로 리팩터 [apps/api/app/main.py]

**Dismissed (노이즈/사양 허용, 8건):** 필수 env/잘못된 URL 미설정 시 import 크래시(의도된 fail-fast), CORS `*`+credentials 반영·빈 문자열→`[]`(기본값 안전·AR14 정책으로 와일드카드 이미 금지·스캐폴드 YAGNI), 헬스 테스트 가짜 세션(스펙 Task 6 명시 허용), get_db 미커밋(트랜잭션은 service 계층 책임), 빈 baseline 마이그레이션(스코프상 의도), TimestampMixin `server_default=func.now()`(스펙 허용·PG 이식성 OK).
