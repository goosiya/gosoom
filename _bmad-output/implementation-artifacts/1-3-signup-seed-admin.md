---
baseline_commit: NO_VCS
---
# Story 1.3: 역할 선택 회원가입 + 시드 관리자

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 신규 사용자(고객 또는 고수),
I want 역할을 선택해 이메일+비밀번호로 회원가입하기를,
So that gosoom에서 내 역할에 맞는 활동을 시작할 수 있다.

이 스토리는 **첫 도메인 슬라이스**다. router→service→repository 계층, 직렬화 경계 camelCase(`CamelModel`), 실 DB 트랜잭션-롤백 테스트의 **선례**를 여기서 확립하며, 이후 모든 도메인 스토리(2~6 에픽)가 이 패턴을 복제한다.

## Acceptance Criteria

**AC1 — users 테이블 + 회원가입 + Argon2 해싱 + 안전한 응답**
**Given** `users` 테이블(id UUIDv7, email, password_hash, **display_name**, user_role, is_active, created_at/updated_at/deleted_at)이 마이그레이션될 때
**When** `POST /api/v1/auth/signup`에 이메일·비밀번호·**표시명(displayName)**·역할(customer|pro)을 보내면
**Then** 비밀번호는 Argon2로 해싱 저장되고(평문 미보관, NFR3), `display_name`이 함께 저장되어 사용자가 생성되며 안전한 사용자 표현(비밀번호 제외, displayName 포함)이 반환된다(FR1).
> **표시명(display_name) 근거:** FR8 견적 비교의 "고수 정보"와 Story 4.5 채팅 목록의 "상대방 정보"가 이메일이 아닌 사람이 식별 가능한 이름으로 노출되도록 하는 최소 식별 필드. 고객·고수 공통 필수 입력이며, 시드 관리자도 표시명을 가진다.

**AC2 — 중복 이메일 거부**
**Given** 이미 등록된 이메일로
**When** 다시 가입을 시도하면
**Then** 중복 이메일 오류가 표준 envelope로 반환된다(409).

**AC3 — admin/허용 외 역할 거부**
**Given** 역할 값이 `admin`이거나 허용 외 값일 때
**When** 가입을 시도하면
**Then** 거부된다 — 관리자는 자가 가입 대상이 아니다(FR1). (요청 스키마가 `customer|pro`만 허용 → 422)

**AC4 — 시드 관리자 1개 + 잠금 방지 표식**
**Given** 초기 시스템 부트스트랩 시
**When** 시드(`uv run python -m app.seed`)가 실행되면
**Then** 시드 관리자 1개(FR1/FR21)가 생성되고, 이 시드 관리자는 비활성화 대상에서 제외되도록 표식된다(`is_seed=True`, 잠금 방지, FR21).

## Tasks / Subtasks

- [x] **Task 1 — User 모델 + UserRole enum** (AC: 1, 3, 4)
  - [x] `app/models/user.py`: `class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin)` — `__tablename__ = "users"`.
    - `email: Mapped[str]` = `mapped_column(String, unique=True, index=True, nullable=False)`
    - `password_hash: Mapped[str]` (nullable=False)
    - `display_name: Mapped[str]` (nullable=False)
    - `user_role: Mapped[UserRole]` = `mapped_column(Enum(UserRole, name="user_role"), nullable=False)`
    - `is_active: Mapped[bool]` = `mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))`
    - `is_seed: Mapped[bool]` = `mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))` — **AC4/FR21 잠금 방지 표식(의도적 추가, 아래 스코프 노트 참조)**
  - [x] `UserRole(str, enum.Enum)`: `CUSTOMER="customer"`, `PRO="pro"`, `ADMIN="admin"` — **DB enum은 3값**(admin은 시드 전용, signup 입력엔 불허). `app/models/user.py` 또는 `app/models/enums.py`에 정의.
  - [x] `app/models/__init__.py`에 `from app.models.user import User` 추가 + `__all__`. **alembic autogenerate가 모델을 감지하려면 반드시 여기서 import**(env.py가 `app.models`를 로드).

- [x] **Task 2 — core/security.py: Argon2 해싱(이 스토리 한정 범위)** (AC: 1)
  - [x] `app/core/security.py` **신규**: `from pwdlib import PasswordHash` → `password_hasher = PasswordHash.recommended()`(Argon2). `def hash_password(plain: str) -> str: return password_hasher.hash(plain)`.
  - [x] ⚠️ **스코프 경계:** 이 스토리는 `hash_password`만 만든다. `verify_password`(로그인 검증)와 JWT 발급/검증은 **Story 1.4**. `get_current_user`/`require_role`은 **Story 1.5**(`deps.py`). 1.2 노트가 security.py를 "1.4/1.5"로 표기했으나, AC1이 Argon2 해싱을 요구하므로 해싱 함수만 이 스토리에서 선반입한다.

- [x] **Task 3 — schemas: CamelModel 베이스 + Signup/UserRead** (AC: 1, 3)
  - [x] `app/schemas/base.py` **신규**(선례): `class CamelModel(BaseModel): model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)`. `from pydantic.alias_generators import to_camel`. 모든 도메인 스키마의 베이스(AR12/명명 패턴 line 268).
  - [x] `app/schemas/auth.py` **신규**:
    - `SignupRequest(CamelModel)`: `email: EmailStr`, `password: str = Field(min_length=8)`, `display_name: str = Field(min_length=1, max_length=50)`, `role: Literal["customer", "pro"]` — **admin/기타 값은 Pydantic이 422로 거부(AC3)**. (역직렬화 경계: 클라이언트는 `displayName` 전송 → `populate_by_name`으로 `display_name` 매핑.)
    - `UserRead(CamelModel)`: `id: UUID`, `email: str`, `display_name: str`, `user_role: UserRole`, `is_active: bool`, `created_at: datetime`, `updated_at: datetime`. **password_hash 절대 미포함**(안전한 표현). `from_attributes=True`로 ORM 객체에서 직접 직렬화.
  - [x] ⚠️ **의존성 추가(유일):** `EmailStr`는 `email-validator`가 필요 → `uv add email-validator`(또는 `uv add "pydantic[email]"`). 미설치 시 import 에러. 추가가 부담이면 `email: str`로 폴백 가능하나 EmailStr 권장.

- [x] **Task 4 — repository: UserRepository** (AC: 1, 2)
  - [x] `app/repositories/users.py` **신규**: `class UserRepository: def __init__(self, session: AsyncSession)`.
    - `async def get_by_email(self, email: str) -> User | None` — `select(User).where(User.email == email, User.deleted_at.is_(None))` (**소프트삭제 공통 필터**, architecture line 286).
    - `async def create(self, user: User) -> User` — `session.add(user); await session.flush(); await session.refresh(user); return user`. **commit은 하지 않음**(트랜잭션은 service 소유 — 1.2 dismissed 노트 정합).

- [x] **Task 5 — service: 회원가입 로직** (AC: 1, 2)
  - [x] `app/services/auth.py` **신규**: `class AuthService: def __init__(self, session: AsyncSession)` → 내부에서 `UserRepository(session)` 구성.
    - `async def signup(self, data: SignupRequest) -> User`: ① `get_by_email` 선검사 → 존재 시 `raise DuplicateEmailError`. ② `hash_password(data.password)`. ③ `User(email=..., password_hash=..., display_name=..., user_role=UserRole(data.role))` 생성 → `repo.create`. ④ `await session.commit()`. ⑤ 동시 가입 race로 unique 위반 시 `IntegrityError`를 잡아 `DuplicateEmailError`로 변환(rollback 후).
  - [x] **권한 검사 없음:** signup은 미인증 공개 엔드포인트(get_current_user 미적용). 소유권/역할 가드는 보호 엔드포인트(1.5+)에서.

- [x] **Task 6 — router: POST /api/v1/auth/signup + main 등록** (AC: 1, 2, 3)
  - [x] `app/routers/auth.py` **신규**: `router = APIRouter(prefix="/api/v1/auth", tags=["auth"])`. `@router.post("/signup", response_model=UserRead, status_code=201)` `async def signup(data: SignupRequest, db: AsyncSession = Depends(get_db)) -> User:` → `return await AuthService(db).signup(data)`. **operationId 안정화**를 위해 함수명 `signup` 유지(Orval 클라이언트 함수명 직결, AR9 — 소비는 1.7).
  - [x] `app/main.py` (UPDATE, **최소**): `from app.routers.auth import router as auth_router` → `app.include_router(auth_router)`. 기존 health/예외 핸들러/CORS는 보존(아래 "현재 코드 상태" 참조).

- [x] **Task 7 — core/exceptions.py: DuplicateEmailError** (AC: 2)
  - [x] 기존 `AppError` 베이스에 도메인 예외 추가: `class DuplicateEmailError(AppError): def __init__(self): super().__init__(code="email_already_exists", message="이미 가입된 이메일입니다.", status_code=409)`. (첫 도메인 예외 — 이후 도메인이 동일 패턴 복제.)

- [x] **Task 8 — Alembic 마이그레이션(users 테이블)** (AC: 1)
  - [x] Task 1(모델 + `__init__` import) 완료 후 `uv run alembic revision --autogenerate -m "add users table"`.
  - [x] **down_revision 확인:** `38c2a20deb69`(baseline)를 부모로 가져야 함. 자동 생성된 파일의 `down_revision = '38c2a20deb69'` 검증.
  - [x] **autogenerate 검수(사람 검수 필수, architecture line 173):**
    - PG enum 타입 `user_role` 생성/삭제가 포함됐는지. **함정:** alembic autogen이 `downgrade`에서 `sa.Enum(name="user_role").drop(op.get_bind())`를 누락하기 쉬움 → downgrade 후 enum 타입이 잔존해 재upgrade 실패. downgrade에 enum drop 명시.
    - `is_active`/`is_seed` `server_default`, `email` unique + index(`ix_users_email`)가 반영됐는지.
  - [x] **멱등/재현 검증(1.2 회귀가드 유지):** `upgrade head` → `downgrade base` → `upgrade head` 깨끗이 통과. **시드는 이 체인에 넣지 않는다**(Task 9 참조) — `upgrade head`는 순수 스키마만.

- [x] **Task 9 — 시드 스크립트(시드 관리자) — 마이그레이션 체인 분리** (AC: 4)
  - [x] `app/seed.py` **신규**: `uv run python -m app.seed`로 실행하는 **멱등** async 스크립트.
    - `settings.seed_admin_email/seed_admin_password/seed_admin_display_name` 읽기(Task 10). 미설정 시 명확한 한국어 에러 출력 후 비정상 종료(앱 크래시 아님 — 독립 스크립트).
    - 세션 열고 `get_by_email(seed_admin_email)` → 존재하면 "시드 관리자 이미 존재 — skip" 로그 후 종료(**멱등**). 없으면 `User(user_role=UserRole.ADMIN, is_seed=True, is_active=True, password_hash=hash_password(...))` 생성 + commit.
    - `if __name__ == "__main__": asyncio.run(main())`.
  - [x] **설계 근거(왜 마이그레이션이 아니라 스크립트인가):** 시드를 Alembic 체인에 넣고 admin 크리덴셜을 env에서 강제로 읽으면, 크리덴셜 없는 CI·fresh clone·1.2가 세운 `upgrade head` 멱등 회귀가드가 전부 깨진다. 시드를 별도 멱등 스크립트로 분리해 **스키마(`upgrade head`)와 데이터 시드를 직교**시킨다. Story 1.6 카테고리 시드도 동일 패턴 복제(일관성).
  - [x] ORM 모델 사용은 스크립트 내에서 허용(앱 런타임 컨텍스트). `is_seed=True`로 FR21 잠금 방지 표식.

- [x] **Task 10 — config.py: SEED_ADMIN_* 필드 추가** (AC: 4)
  - [x] 기존 `Settings`에 추가: `seed_admin_email: str | None = None`, `seed_admin_password: str | None = None`, `seed_admin_display_name: str = "관리자"`. (필수 아님 — 시드 스크립트 실행 시에만 소비. 미설정이어도 앱 기동/마이그레이션엔 영향 없음.)
  - [x] `.env.example`에 주석과 함께 추가: `SEED_ADMIN_EMAIL=`, `SEED_ADMIN_PASSWORD=`, `SEED_ADMIN_DISPLAY_NAME=관리자`. **시크릿(.env)은 커밋 금지.**

- [x] **Task 11 — 테스트(실 DB + 트랜잭션 롤백)** (AC: 1, 2, 3, 4)
  - [x] `tests/conftest.py` (UPDATE): 기존 `client`(가짜 세션, health용)는 **보존**하고, 도메인 테스트용 픽스처 추가:
    - `db_session` 픽스처 — 실 엔진 connection에서 외부 트랜잭션 시작 후 `AsyncSession(bind=connection, join_transaction_mode="create_savepoint")`로 세션 생성, 테스트 종료 시 외부 트랜잭션 rollback. **함정:** service가 `session.commit()`을 호출하므로 SAVEPOINT 조인이 없으면 실제 커밋되어 DB 오염 + 격리 깨짐. SQLAlchemy 2.0 `join_transaction_mode="create_savepoint"`가 commit을 savepoint에 가두고 바깥 트랜잭션을 롤백 가능하게 한다(이게 정답 패턴, 수동 event listener 불필요).
    - `client_db` 픽스처 — `app.dependency_overrides[get_db] = lambda: db_session`(또는 yield 래퍼)로 라우터가 롤백 세션을 쓰게 함 + `AsyncClient(ASGITransport)`.
  - [x] `tests/test_auth_signup.py` **신규**:
    - 성공: `POST /api/v1/auth/signup`(customer) → **201**, 응답 JSON에 `displayName` 존재·`userRole=="customer"`, `password`/`passwordHash` 키 **부재**(안전 표현, AC1).
    - 중복: 동일 이메일 2회 → 2번째 **409** + envelope `{code:"email_already_exists", message}`(AC2).
    - admin 거부: `role:"admin"` → **422**(AC3). 허용 외 값(`"superuser"`)도 422.
    - 검증 실패: `display_name` 누락/짧은 password → **422** + envelope(서버 검증 신뢰, NFR3).
    - (선택) 해싱 확인: 생성 후 DB의 `password_hash`가 평문이 아니고 Argon2 포맷(`$argon2`)인지(NFR3).
  - [x] `tests/test_seed.py` **신규**(선택, AC4): `SEED_ADMIN_*` 설정 하에 시드 로직 2회 실행 → 관리자 1개만 존재(멱등), `is_seed is True`, `user_role==admin`. (실 DB 미가용 환경 고려해 시드 함수를 import해 db_session으로 직접 호출하는 형태 권장.)

## Dev Notes

### 🎯 스코프 경계 (범위 침범 금지)

- ✅ **이 스토리:** `users` 테이블 1개, `POST /api/v1/auth/signup`(가입만), Argon2 `hash_password`, 시드 관리자 스크립트. **첫 도메인 슬라이스 — 계층/직렬화/테스트 선례 확립.**
- ❌ **로그인/로그아웃/refresh(JWT 발급·검증)는 Story 1.4.** 이 스토리는 토큰을 발급하지 않는다. `verify_password`도 1.4.
- ❌ **get_current_user/require_role(RBAC 가드)는 Story 1.5.** `deps.py`는 건드리지 않는다(현재 스텁 유지).
- ❌ **카테고리·고수 카테고리(pro_categories)·요청·견적·채팅 테이블 금지** — 각각 1.6/Epic 3·2·4. `users` 외 도메인 테이블 0개.
- ❌ **Orval/api-client/프론트 UI는 Story 1.7.** 이 스토리는 백엔드 + OpenAPI 노출까지(operationId 안정화만 신경).

### 의도적 추가(epic AC 리터럴 초과 — 근거 명시, scope creep 아님)

1. **`is_seed` 컬럼:** AC1의 컬럼 리터럴 목록엔 없으나 **AC4/FR21**("시드 관리자는 비활성화 대상 제외 표식")을 충족하려면 필요. 마커 컬럼이 가장 명확. → 의도적.
2. **`core/security.py`(hash_password):** 1.2 노트는 security.py를 "1.4/1.5"로 표기했으나 **AC1이 Argon2 해싱을 요구** → 해싱 함수만 선반입, JWT·verify는 1.4 연기. 경계 위 Task 2 참조.
3. **`schemas/base.py`의 `CamelModel`:** 단일 스토리만 보면 인라인 config로 충분하나, 첫 슬라이스가 **직렬화 경계 camelCase 선례**(architecture line 268)를 세워 2~6 에픽이 복제하도록 베이스로 추출.

### 현재 코드 상태 (UPDATE 대상 — 보존할 것)

Story 1.2가 인프라를 완성함. 아래는 현재 실제 상태이며 **덮어쓰지 말고 확장**한다:

- **`app/main.py`** (UPDATE, 최소): `APIRouter(prefix="/api/v1")` + health(DB 포함 200/503) + `register_exception_handlers(app)`(AppError/RequestValidationError/HTTPException/Exception 4종) + `CORSMiddleware`가 이미 구성됨. → **auth 라우터 include만 추가.** 예외 핸들러·CORS·health 경로 보존.
- **`app/core/config.py`** (UPDATE): `Settings`에 `database_url`, `jwt_secret`, `access_token_expire_minutes=30`, `refresh_token_expire_days=14`, `cors_origins`(NoDecode+validator) 존재. → **`seed_admin_*` 필드만 추가**(Task 10). CORS 파싱 로직 보존.
- **`app/core/db.py`** (그대로): `engine`(asyncpg, pool_pre_ping), `SessionLocal`(async_sessionmaker, expire_on_commit=False), `class Base(DeclarativeBase)`, `get_db()`. User 모델은 이 `Base` 상속.
- **`app/core/exceptions.py`** (UPDATE): `AppError(code, message, status_code=400, detail=None)` + `to_envelope()` 베이스만 존재(도메인 서브클래스 0개). → `DuplicateEmailError` 추가(Task 7).
- **`app/models/base.py`** (그대로 — 상속만): `UUIDPrimaryKeyMixin`(`id` UUIDv7, `default=uuid7`, **server_default 없음**), `TimestampMixin`(`created_at`/`updated_at`, server_default=func.now()), `SoftDeleteMixin`(`deleted_at` nullable). **User는 이 셋을 상속.**
- **`app/models/__init__.py`** (UPDATE): 현재 주석만. → `from app.models.user import User` 추가(autogenerate 감지 필수).
- **`app/deps.py`** (그대로 — 건드리지 않음): "Story 1.5에서 get_current_user/require_role" 주석 스텁. signup은 미인증이라 불필요.
- **`app/{routers,services,repositories,schemas}/__init__.py`** (그대로): 모두 빈 주석 패키지. → 각 도메인 파일 **신규** 추가. **참고 구현 없음 — 이 스토리가 첫 예시.**
- **`alembic/versions/38c2a20deb69_baseline.py`** (그대로): `revision='38c2a20deb69'`, `down_revision=None`, upgrade/downgrade 모두 `pass`. → **새 마이그레이션의 `down_revision`이 이 id**.
- **`tests/conftest.py`** (UPDATE): 현재 `_FakeSession`(execute(SELECT 1)만 스텁) + `client` 픽스처(get_db override). → health 테스트 유지 위해 **보존**하고 `db_session`/`client_db`(실 DB 롤백) 추가(Task 11).
- **`pyproject.toml`** (검토만): `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic`, `pydantic-settings`, **`pwdlib[argon2]`**, `pyjwt`, **`uuid7`** 이미 설치·검증됨. dev: pytest, pytest-asyncio(`asyncio_mode=auto`), httpx, ruff. **유일한 신규 의존성 후보 = `email-validator`**(EmailStr 사용 시, Task 3). `uv add`로.
- **`.env`** (이미 구성·검증됨, 2026-06-08 Supabase 연결 OK): DATABASE_URL + JWT_SECRET 채워짐. **커밋 금지.** → `SEED_ADMIN_*` 추가 필요(수동 체크포인트 참조).

### ⚠️ 알려진 함정 (런타임 디버깅 전 미리 적용 — 고가치)

1. **테스트 롤백 + service commit 충돌(가장 중요):** signup service가 `session.commit()`을 호출 → 단순 트랜잭션 롤백 픽스처는 commit이 실제 반영되어 DB 오염·격리 붕괴. **반드시** `AsyncSession(bind=connection, join_transaction_mode="create_savepoint")`(SQLAlchemy 2.0)로 commit을 SAVEPOINT에 가두고 외부 트랜잭션을 롤백. (수동 `after_transaction_end` event listener 재시작 방식은 구식 — 2.0 옵션으로 충분.)
2. **Alembic enum downgrade 누락:** autogen이 `user_role` PG enum 타입을 upgrade에서 생성하나 downgrade에서 `drop` 누락하기 쉬움 → downgrade 후 타입 잔존, 재upgrade 시 "type already exists" 실패. downgrade에 `sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=False)` 명시(멱등 검증으로 포착).
3. **autogenerate 전 모델 import 필수:** `app/models/__init__.py`에 `User` import가 없으면 autogen이 빈 마이그레이션 생성(테이블 누락). Task 1 → Task 8 순서 엄수.
4. **camelCase 직렬화 경계:** 요청은 `displayName`(camel)로 들어와 `populate_by_name`으로 `display_name`에 매핑, 응답도 `displayName`로 나감. `UserRead`가 `from_attributes=True`라야 ORM `User` 객체를 직접 `response_model`로 직렬화(서비스가 dict 변환 불필요).
5. **uuid7 / uv 실행(1.2 계승):** import는 `from uuid_extensions import uuid7`(패키지명 `uuid7`, 모듈명 `uuid_extensions`). 이 PC는 uv managed standalone 3.12 실행 불가 → `[tool.uv] python-preference="only-system"` 유지, `uv sync`/`uv run ...` 사용.
6. **시드는 `upgrade head` 체인 밖:** 시드를 data migration으로 넣지 말 것 — `upgrade head`의 멱등·무크리덴셜 통과(1.2 회귀가드) 보존. 시드는 `uv run python -m app.seed` 별도 실행.

### 아키텍처 준수 (반드시 따를 규약)

- **계층:** router(HTTP·검증·Depends) → service(비즈니스·권한·트랜잭션/commit) → repository(DB·`deleted_at IS NULL` 필터). 역방향 호출 금지.
  [Source: architecture.md#Structure Patterns (line 284-288)]
- **명명:** DB 테이블 복수 snake_case(`users`), 컬럼 snake_case(`user_role`, `is_active`, `display_name`, `created_at`/`deleted_at`). Python 함수 snake_case, 클래스 PascalCase 단수(`User`), 스키마 PascalCase+접미사(`SignupRequest`/`UserRead`). PK=`id`(UUIDv7).
  [Source: architecture.md#Naming Patterns (line 256-275)]
- **JSON 경계 camelCase:** Pydantic `alias_generator=to_camel` + `populate_by_name=True`. 내부 속성 snake_case 유지, 직렬화/역직렬화 경계에서만 camel.
  [Source: architecture.md#Naming Patterns API (line 268-269)]
- **인증/보안:** Argon2(pwdlib) 해싱, 평문 미보관. JWT/Bearer/OAuth2PasswordBearer는 1.4/1.5(이 스토리 범위 밖).
  [Source: architecture.md#Authentication & Security (line 184-195)]
- **에러 envelope:** `{code, message, detail?}` + HTTP status. `code`=기계 판독 안정 식별자, `message`=한국어 노출 가능. 성공 응답은 리소스 직접 반환(불필요 래핑 금지).
  [Source: architecture.md#API & Communication Patterns (line 203), 1-2 story Format Patterns]
- **소프트삭제:** repository 조회에 `deleted_at IS NULL` 공통 필터. users의 비활성화는 `is_active`(1.4 로그인 차단·Epic 6 관리), `deleted_at`은 mixin으로 마련만.
  [Source: architecture.md#Data Architecture (line 176-177), line 286]
- **DB 이식성(NFR6):** repository + Alembic로 Phase1(Supabase)→Phase2 코드 변경 없이 이관. UUIDv7 앱측 생성(확장 의존 회피).
  [Source: architecture.md#Data Architecture (line 168-182)]
- **검증/직렬화:** Pydantic v2 `from_attributes=True`. 서버 검증 신뢰(클라이언트 검증만 신뢰 금지, NFR3).
  [Source: architecture.md#Data Architecture (line 182)]

### 라이브러리/버전 (검증 완료 — 그대로 사용)

- FastAPI 0.136.x · SQLAlchemy 2.0.36(async+asyncpg) · Pydantic 2.10 / pydantic-settings 2.7+ · Alembic 1.14+ · asyncpg 0.30+ · **pwdlib[argon2] 0.2.1+** · **uuid7 0.1.0+** · Python 3.12.8. 모두 `.venv` 설치·검증(2026-06-08, Supabase PG17.6 연결 OK).
- **신규 후보:** `email-validator`(EmailStr 사용 시). 그 외 새 버전 탐색/업그레이드 불필요.
  [Source: architecture.md#Coherence Validation, 1-2 story 라이브러리 섹션, backend-env-setup 메모]

### 파일 구조 (생성/수정 위치)

```
apps/api/
  app/
    main.py              (UPDATE) auth 라우터 include만 추가
    core/
      config.py          (UPDATE) SEED_ADMIN_* 필드 추가
      security.py        (NEW) password_hasher + hash_password (Argon2)
      exceptions.py      (UPDATE) DuplicateEmailError 추가
    models/
      __init__.py        (UPDATE) from app.models.user import User
      user.py            (NEW) User 모델 + UserRole enum
    schemas/
      base.py            (NEW) CamelModel 베이스
      auth.py            (NEW) SignupRequest, UserRead
    repositories/
      users.py           (NEW) UserRepository(get_by_email, create)
    services/
      auth.py            (NEW) AuthService.signup
    routers/
      auth.py            (NEW) POST /api/v1/auth/signup
    seed.py              (NEW) 시드 관리자 멱등 스크립트(python -m app.seed)
  alembic/
    versions/
      <new>_add_users_table.py  (NEW, autogenerate, down_revision=38c2a20deb69)
  tests/
    conftest.py          (UPDATE) db_session/client_db(실 DB 롤백) 추가
    test_auth_signup.py  (NEW) 201/409/422/해싱
    test_seed.py         (NEW, 선택) 시드 멱등
  .env.example           (UPDATE) SEED_ADMIN_* 추가
  pyproject.toml         (UPDATE, 조건부) email-validator 추가
```
[Source: architecture.md#Complete Project Directory Structure (line 407-425), 1-2 story 파일 구조]

### 테스트 표준

- pytest + `pytest-asyncio`(`asyncio_mode=auto`) + httpx `AsyncClient`(`ASGITransport`) + `dependency_overrides`. **도메인 테스트는 실 DB + 트랜잭션 롤백**(architecture line 289 규정 — fake repo 금지: 이메일 unique 제약 등 DB 레벨 보장을 실제로 검증해야 함).
- 핵심 경로 우선(가입 성공/중복/역할거부/검증실패). 커버리지 점진(AR20). CI(`pytest`)는 Story 1.8에서 GitHub Actions + `DATABASE_URL` 시크릿으로 연결.
  [Source: architecture.md#Structure Patterns (line 289), 1-2 story 테스트 표준]

### Project Structure Notes

- 정합: 위 배치는 architecture.md `apps/api` 트리(routers/services/repositories/models/schemas/core/security)와 일치. signup이 `auth` 라우터에 사는 것은 architecture 태그 규약(auth/users/...)·epic AC(`/api/v1/auth/signup`) 정합.
- 변이: `users` 모델·repository를 `auth` 라우터/서비스가 사용(가입은 auth 행위, 데이터는 user). 1.4 로그인도 동일 auth 라우터 + users repository 재사용 → 의도된 배치(중복 방지).
- `apps/api`는 Turborepo 그래프 외부(uv/uvicorn 별도 파이프라인).

### References

- [Source: epics.md#Story 1.3: 역할 선택 회원가입 + 시드 관리자 (line 226-249)] — 4개 AC 원본(BDD), display_name 근거
- [Source: epics.md#Story 1.4/1.5 (line 251-293)] — 로그인/JWT/RBAC 범위 경계(이 스토리에서 제외 확인)
- [Source: architecture.md#Authentication & Security (line 184-195)] — Argon2(pwdlib), JWT(1.4), 비밀번호 평문 미보관
- [Source: architecture.md#Data Architecture (line 168-182)] — SQLAlchemy async, Alembic, UUIDv7, 소프트삭제, 시드(관리자) data migration/seed 스크립트
- [Source: architecture.md#Naming Patterns (line 256-275)] — DB/API/Python 명명, camelCase 경계, user_role enum
- [Source: architecture.md#Structure Patterns (line 284-289)] — router→service→repository, 테스트 트랜잭션 롤백
- [Source: architecture.md#API & Communication Patterns (line 197-207)] — `/api/v1`, 에러 envelope, 도메인 태그, operationId
- [Source: AR4, AR5, AR11, AR12 (epics.md#Additional Requirements line 78-88)] — UUIDv7 앱측, 시드, JWT/Argon2, 에러 envelope
- [Source: 1-2-backend-db-foundation.md] — 인프라 현황, UUIDv7 mixin, 에러 핸들러, uv/uuid_extensions 함정, `upgrade head` 멱등 회귀가드
- [Source: backend-env-setup 메모] — uv only-system, uuid_extensions import, .env 검증 사실
- [Source: manual-setup-checkpoints 메모, AR23] — 기능 구현 전 수동 외부 설정 선안내

## ⚡ 수동 설정 체크포인트 (AR23 — dev-story 진입 전 KTH에게 먼저 안내)

dev-story 구현에 들어가기 **전에**, 사용자(KTH)가 직접 `apps/api/.env`에 아래를 추가해야 시드 관리자(Task 9)가 동작한다:

```
SEED_ADMIN_EMAIL=admin@gosoom.local        # 시드 관리자 로그인 이메일
SEED_ADMIN_PASSWORD=<강한 비밀번호 8자+>     # 평문 미보관 — 시드 시 Argon2 해싱됨
SEED_ADMIN_DISPLAY_NAME=관리자              # 표시명(선택, 기본 "관리자")
```

- `.env`는 커밋 금지(`.env.example`엔 빈 키만). 운영(Railway)에선 환경변수로 주입(NFR3).
- 회원가입(AC1-3)·테이블 마이그레이션(Task 8)은 이 값 없이도 동작 — 시드 스크립트 실행 시에만 필요.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context)

### Debug Log References

- `alembic upgrade head → downgrade base → upgrade head` 멱등/재현 체인 통과(Task 8). downgrade에 PG enum 타입 명시 drop 추가로 재upgrade "type already exists" 회피.
- DB enum 라벨 직접 확인: `SELECT enumlabel ... WHERE typname='user_role'` → `['customer','pro','admin']`(소문자 저장 확정, `values_callable` 효과).
- `pytest` 전체 18 passed(2회 연속 동일 — 롤백 격리 확인). `ruff check .` All checks passed.

### Completion Notes List

- **첫 도메인 슬라이스 선례 확립:** router→service→repository 계층, `CamelModel`(camelCase 직렬화 경계), 실 DB+SAVEPOINT 롤백 테스트 패턴을 모두 이 스토리에서 처음 구현 — 2~6 에픽이 복제할 기준.
- **AC1:** `users` 테이블(UUIDv7 PK + display_name + is_seed 포함) 마이그레이션, `POST /api/v1/auth/signup`가 Argon2 해싱 저장 후 안전 표현(UserRead, password 미포함) 201 반환. DB의 `password_hash`가 `$argon2`로 시작함을 테스트로 검증.
- **AC2:** 중복 이메일 선검사 409 + 동시 가입 race 대비 IntegrityError→DuplicateEmailError 변환. envelope `{code:"email_already_exists"}`.
- **AC3:** 요청 스키마 `role: Literal["customer","pro"]` → admin/허용 외 값은 Pydantic 422. (story 초안 `UserRole` 사용 시 admin 통과 버그를 Literal로 교정.)
- **AC4:** `app/seed.py` 멱등 시드 관리자(`is_seed=True`, `user_role=admin`). 마이그레이션 체인과 분리(스키마/데이터 직교) — `upgrade head` 무크리덴셜 회귀가드 보존.
- **어드바이저 검토 반영(3건):** ① enum `values_callable`로 DB 소문자 저장 강제(미적용 시 DB엔 대문자 저장되나 API는 통과하는 잠복 버그). ② 단일 격리 테스트 선행 → 픽스처가 `expire_on_commit=False` 누락으로 `MissingGreenlet` 내는 것을 전체 스위트 작성 전에 포착. ③ migration up/down/up 게이트로 enum drop 누락 검증.
- **추가 함정 해결:** pytest-asyncio 함수 스코프 루프 + 모듈 엔진 풀 재사용 → "Event loop is closed". 테스트마다 NullPool 전용 엔진 생성/dispose로 해결.
- **의존성:** `email-validator`(EmailStr)만 추가(`uv add`, story 사전 승인됨).
- **⚠️ 수동 설정 미완(KTH):** `apps/api/.env`에 `SEED_ADMIN_EMAIL/PASSWORD/DISPLAY_NAME` 추가 필요. 시드 *로직*은 롤백 세션 + monkeypatch로 검증 완료(test_seed.py)이나, 실제 `uv run python -m app.seed` 실행은 env 설정 후 가능. 회원가입/마이그레이션은 이 값 없이 동작.

### File List

**신규(NEW)**
- `apps/api/app/models/user.py` — User 모델 + UserRole enum(values_callable 소문자)
- `apps/api/app/core/security.py` — Argon2 `hash_password`
- `apps/api/app/schemas/base.py` — `CamelModel` 베이스
- `apps/api/app/schemas/auth.py` — `SignupRequest`(Literal role) / `UserRead`
- `apps/api/app/repositories/users.py` — `UserRepository`(get_by_email, create)
- `apps/api/app/services/auth.py` — `AuthService.signup`
- `apps/api/app/routers/auth.py` — `POST /api/v1/auth/signup`
- `apps/api/app/seed.py` — 시드 관리자 멱등 스크립트
- `apps/api/alembic/versions/04c24a1c717d_add_users_table.py` — users 테이블 마이그레이션(enum drop 보정)
- `apps/api/tests/test_auth_signup.py` — 201/409/422/해싱 테스트
- `apps/api/tests/test_seed.py` — 시드 멱등 테스트

**수정(UPDATE)**
- `apps/api/app/core/config.py` — `seed_admin_*` 필드 추가
- `apps/api/app/core/exceptions.py` — `DuplicateEmailError` 추가
- `apps/api/app/models/__init__.py` — `User`/`UserRole` import(autogenerate 감지)
- `apps/api/app/main.py` — auth 라우터 include
- `apps/api/tests/conftest.py` — `db_session`/`client_db`(실 DB + SAVEPOINT 롤백, NullPool 엔진)
- `apps/api/.env.example` — `SEED_ADMIN_*` 추가
- `apps/api/pyproject.toml` / `uv.lock` — `email-validator` 의존성 추가

### Change Log

| 날짜 | 변경 | 비고 |
| --- | --- | --- |
| 2026-06-08 | Story 1.3 구현 완료 — 역할 선택 회원가입 + 시드 관리자, 첫 도메인 슬라이스 | 18 tests pass, ruff pass. 수동 SEED_ADMIN_* env 설정만 사용자 대기 |
| 2026-06-08 | 코드 리뷰(3-레이어 적대적) — patch 5건 적용 + 회귀 테스트 4건 추가, 22 tests pass, ruff pass. defer 4건(HIGH 1 포함)은 `deferred-work.md` 기록. Status→done | 이메일 정규화/password 상한/시드 충돌·가드/공백 display_name |

### Review Findings

코드 리뷰(2026-06-08, 3-레이어 적대적 리뷰: Blind Hunter / Edge Case Hunter / Acceptance Auditor). 요약: decision-needed 0 · patch 5 · defer 4 · dismissed 3. AC1~4 모두 충족·스코프 경계 준수 확인됨. 발견 항목은 대부분 강건성/엣지케이스(현 스토리 차단 동작엔 영향 없음).

#### Patch (적용 대상)

- [x] [Review][Patch] 이메일 정규화 누락 — 대소문자 구분으로 동일 사용자 중복 가입 가능 [apps/api/app/schemas/auth.py, services/auth.py, repositories/users.py] — ✅ 적용: `SignupRequest`에 `email` after-validator(strip+lower) 추가, `get_by_email`이 조회 이메일을 동일 정규화, `seed_admin`도 저장 이메일 정규화 — 세 경계 일관.
- [x] [Review][Patch] password 최대 길이 부재 — Argon2 해싱 리소스 소진(DoS) 벡터 [apps/api/app/schemas/auth.py] — ✅ 적용: `password: str = Field(min_length=8, max_length=128)`.
- [x] [Review][Patch] 시드 관리자 이메일이 일반 가입 계정과 충돌 시 조용히 skip [apps/api/app/seed.py] — ✅ 적용: 발견 행이 `is_seed`·admin이 아니면 명확한 `ValueError`(다른 주소 사용 안내), 시드 관리자면 기존대로 skip.
- [x] [Review][Patch] `seed_admin`에 IntegrityError 가드 없음 — 삽입 실패 시 스크립트 비정상 크래시 [apps/api/app/seed.py] — ✅ 적용: create+commit을 try/except로 감싸 IntegrityError→rollback→명확한 한국어 `ValueError`(service 패턴 미러링).
- [x] [Review][Patch] 공백만으로 이루어진 display_name 통과 [apps/api/app/schemas/auth.py] — ✅ 적용: `display_name` after-validator로 strip 후 비어있으면 422.

#### Defer (이번 변경 범위 밖 / 현재 비활성)

- [x] [Review][Defer] 소프트삭제 이메일 재가입 불가 — 비-partial 유니크 인덱스 vs `deleted_at IS NULL` 읽기 필터 불일치 (**HIGH**, 2개 레이어) [apps/api/app/models/user.py:39, repositories/users.py:get_by_email, alembic/.../04c24a1c717d] — `get_by_email`은 `deleted_at IS NULL`로 거르지만 `ix_users_email` 유니크 인덱스는 삭제행 포함 전체. 소프트삭제된 이메일은 선검사 통과(None)→insert가 유니크 위반→오해 소지 있는 409로 영영 재가입 불가. **deferred:** Story 1.3엔 삭제 경로가 없어 현재 도달 불가능. 삭제 플로우(Epic 6 계정관리)가 들어올 때 partial 유니크 인덱스(`WHERE deleted_at IS NULL`) 채택 여부를 함께 결정.
- [x] [Review][Defer] 과도한 IntegrityError→DuplicateEmailError 매핑 [apps/api/app/services/auth.py:234] — 모든 IntegrityError를 409 중복 이메일로 변환. 현재 users의 유일 제약이 email 유니크라 정상 동작이나, 향후 제약 추가 시 다른 위반이 잘못된 409로 가려짐. **deferred:** 두 번째 제약 추가 시 제약명 검사로 분기.
- [x] [Review][Defer] CORS credentialed-wildcard 풋건 [apps/api/app/main.py] — `allow_credentials=True` + `allow_methods/headers=["*"]`. 기본 오리진은 안전하나 `CORS_ORIGINS`에 `*`가 들어가면 자격증명+와일드카드 오설정. **deferred:** CORS는 Story 1.2에서 확립(본 스토리 미도입). 자격증명 활성 시 `*` 거부 validator는 후속 보안 정비로.
- [x] [Review][Defer] downgrade enum drop `checkfirst=False` [apps/api/alembic/versions/04c24a1c717d:393] — 타입이 이미 없는 부분 다운그레이드 상태에서 다운그레이드 실패. **deferred:** up→down→up 체인은 검증 통과(정상 경로 안전), 손상 상태 전용 엣지. 낮은 우선순위.

#### Dismissed (오탐/노이즈 — 3건)

- commit 후 ORM 만료→직렬화 시 MissingGreenlet/500 (Blind, HIGH) — **오탐.** `db.py:25` `SessionLocal = async_sessionmaker(engine, expire_on_commit=False)` 확인. Blind Hunter는 프로젝트 컨텍스트 미보유로 추정. 성공 테스트도 동일 prod-equivalent 설정(`client_db`)으로 전체 직렬화 경로를 통과.
- email 컬럼 길이 상한 부재 (Edge, Low) — email-validator가 RFC 길이(local≤64/domain≤255/total≤254)를 강제하므로 btree 인덱스 한계 훨씬 이하. 실 위험 아님.
- `.env.example`의 `SEED_ADMIN_EMAIL=admin@gosoom.local` (Auditor, Low) — 예시 파일의 일러스트레이션 값(password는 공백, 시크릿 누출 없음)이며 본 스토리 수동 체크포인트(line 247)와 일치. 결함 아님.
