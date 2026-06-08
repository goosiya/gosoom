---
baseline_commit: NO_VCS
---
# Story 1.5: 역할 기반 접근 제어(RBAC)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 시스템,
I want 모든 보호된 엔드포인트에서 인증과 역할·소유권을 서버에서 검사하기를,
So that 각 역할이 자신에게 허용된 데이터·기능에만 접근하도록 일관되게 강제할 수 있다.

이 스토리는 **인가(authorization) 경계 프리미티브**를 확립한다. Story 1.4가 만든 JWT 발급/검증 규약(`{user_id, user_role, type:"access", exp}`, `decode_token`)을 **소비**하여, `deps.get_current_user`(JWT→현재 사용자)와 `require_role(...)`(역할 가드), 그리고 service 계층용 **소유권 검사 헬퍼**(`ensure_owner_or_admin`)를 만든다. 이 세 가지가 이후 모든 보호 엔드포인트(Epic 2 요청, Epic 3 견적, Epic 4 채팅, Epic 6 관리자)가 재사용할 단일 인가 도구다(NFR4, AR8).

> ⚠️ **범위의 본질(반드시 인지):** 이 시점에 **보호할 도메인 자원이 아직 없다** — `signup`/`login`/`refresh`는 모두 미인증 공개이고, `service_requests`(Epic 2)·`quotes`(Epic 3)·`chat_rooms`(Epic 4)는 미존재. 따라서 1.5는 인가 **프리미티브 + 패턴**을 확립·검증하고, 그 **첫 실사용**은 Epic 2 이후 각 도메인 service가 가져간다. `get_current_user`만 단독으로 증명할 **실 엔드포인트로 `GET /api/v1/users/me`를 신설**한다(1.7 프론트가 토큰만으로는 알 수 없는 `displayName`을 얻는 실수요자). `require_role`/소유권은 **가짜 프로덕션 엔드포인트를 만들지 않고** 격리 테스트 앱으로 검증한다(아래 Task 6).

## Acceptance Criteria

**AC1 — get_current_user: 유효 access 토큰으로 현재 사용자 해석, 무효/누락은 401(표준 envelope)**
**Given** 보호된 엔드포인트에 `Depends(get_current_user)`가 적용되었을 때
**When** 요청이 `Authorization: Bearer <access_jwt>`를 동반하면
**Then** JWT 서명·만료·`type=="access"`를 검증하고 `user_id`로 현재 사용자를 **재조회**해 반환한다. 토큰 누락은 401 `{code:"not_authenticated"}`, 만료·위조·`type` 불일치·payload 형식 오류·재조회 실패는 401 `{code:"invalid_token"}`로 표준 envelope 반환된다(FR4, AR8, NFR3).

**AC2 — get_current_user: 비활성/삭제 계정은 유효 토큰이어도 401(즉시 차단)**
**Given** 발급 시점엔 활성이었으나 이후 비활성화(`is_active=false`)되거나 소프트삭제(`deleted_at`)된 계정의 유효 access 토큰일 때
**When** 보호 엔드포인트에 접근하면
**Then** `get_current_user`가 매 요청 DB 재조회로 현재 상태를 확인해 401 `{code:"invalid_token"}`로 거부한다 — 비활성화가 **다음 인증 요청에서 즉시** 효력을 갖는다(FR19/20 중앙 시행). *(이는 1.4의 "비활성화는 다음 refresh 시점에 효력" 메모를 의도적으로 강화한다 — Dev Notes 결정 사항 참조.)*

**AC3 — require_role: 역할 불일치는 403, 일치는 통과**
**Given** 보호 엔드포인트에 `require_role(허용역할...)` 가드가 적용되었을 때
**When** 인증된 사용자의 `user_role`이 허용 집합에 포함되면 통과(200), 포함되지 않으면
**Then** 403 `{code:"forbidden"}`로 표준 envelope 반환된다. `require_role`은 `get_current_user`에 의존하므로 토큰 누락·무효는 그 전 단계에서 먼저 401이 된다(401→403 순서, FR4, AR8).

**AC4 — 소유권 검사 패턴(service 계층 단일 시행) 프리미티브 확립**
**Given** 권한 규칙이 라우터·클라이언트에 흩어질 위험이 있을 때
**When** 재사용 헬퍼 `ensure_owner_or_admin(resource_owner_id, current_user)`를 만들면
**Then** 고객/고수=본인 자원만, 관리자=전체 허용(불일치 시 403 `ForbiddenError`) 규칙이 **service 계층에서 단일 시행**되도록 한 곳에 캡슐화된다(NFR4, AR8). **첫 실사용은 Epic 2 이후** — 이 스토리는 헬퍼와 패턴만 확립하고 단위 테스트로 증명한다.

**AC5 — GET /api/v1/users/me: get_current_user를 소비하는 첫 실 보호 엔드포인트**
**Given** 인증된 사용자가
**When** `GET /api/v1/users/me`를 `Authorization: Bearer <access_jwt>`로 호출하면
**Then** 현재 사용자의 안전한 표현(`UserRead` — 비밀번호 제외, `displayName` 포함)이 200으로 반환되고, 미인증/무효 토큰은 AC1 규칙대로 401이 된다(1.7 user-web가 로그인 사용자 식별에 소비).

**AC6 — RBAC 검증 테스트(각 역할 허용/거부)**
**Given** RBAC 프리미티브가 구현되었을 때
**When** pytest로 각 역할의 허용/거부 경로를 실행하면
**Then** 허용 케이스는 200, 권한 외 케이스는 403, 미인증/무효 토큰은 401로 통과한다(가짜 프로덕션 엔드포인트 없이 격리 테스트 앱 + 실 `/users/me`로 검증).

## Tasks / Subtasks

- [x] **Task 1 — core/exceptions.py: 인가 도메인 예외 2종** (AC: 1, 3, 4)
  - [x] `class NotAuthenticatedError(AppError)`: `code="not_authenticated"`, `message="인증이 필요합니다."`, `status_code=401`. **토큰 누락**(Authorization 헤더 부재) 전용 — 토큰이 있으나 무효한 경우는 기존 `InvalidTokenError`(1.4) 재사용.
  - [x] `class ForbiddenError(AppError)`: `code="forbidden"`, `message="이 작업을 수행할 권한이 없습니다."`, `status_code=403`. 역할 불일치(`require_role`)·소유권 불일치(`ensure_owner_or_admin`) 공용.
  - [x] 기존 `DuplicateEmailError`/`InvalidCredentialsError`/`InvalidTokenError` 패턴 그대로 복제(AppError 서브클래스). **기존 예외 보존**(append만).
  - [x] ⚠️ 현재 envelope는 401/409만 존재 — 403은 이 스토리가 처음 도입. 전역 핸들러(`main.py`)는 `AppError.status_code`를 그대로 사용하므로 403도 자동으로 표준 envelope가 된다(핸들러 수정 불요).

- [x] **Task 2 — core/security.py: OAuth2PasswordBearer 토큰 추출기** (AC: 1)
  - [x] `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)` 추가. **`auto_error=False`가 핵심** — 기본 `auto_error=True`는 토큰 누락 시 FastAPI가 `HTTPException(401)`을 던져 `{code:"http_401"}`(envelope 핸들러의 HTTPException 분기)로 새어나가 우리 표준 `code`를 깬다. `False`로 두고 `deps.get_current_user`가 `None`을 받아 도메인 `NotAuthenticatedError`(안정 `code`)를 던진다.
  - [x] `tokenUrl`은 OpenAPI(Swagger Authorize) 표시용 상대 경로 — 실제 로그인은 1.4 `/login`(JSON). 런타임 동작엔 영향 없음.
  - [x] **위치 근거:** architecture 디렉터리 구조가 `security.py # ... OAuth2PasswordBearer`로 명시(line 419). 토큰 추출 스킴은 보안 유틸 계층에 둔다. **모듈 docstring 갱신**(현재 "get_current_user/require_role은 1.5"라 적힌 줄을 "추출 스킴은 여기, 가드는 deps.py"로 정정).
  - [x] ⚠️ **라이브러리 계층 유지:** security.py는 도메인 예외를 import하지 않는다(1.4 규약). `oauth2_scheme`은 스킴 인스턴스만 노출하고, 누락→예외 변환은 deps.py가 한다.

- [x] **Task 3 — deps.py: get_current_user + require_role + CurrentUser 타입** (AC: 1, 2, 3)
  - [x] 현재 `deps.py`는 **docstring만 있는 스텁** — 실제 구현으로 채운다(덮어쓰기 OK, 스텁이라 보존할 코드 없음). docstring은 유지·확장.
  - [x] `async def get_current_user(token: str | None = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User`:
    - ① `if token is None: raise NotAuthenticatedError()` (헤더 누락).
    - ② `try: payload = decode_token(token) except jwt.InvalidTokenError: raise InvalidTokenError()` (만료·위조·서명오류·exp부재 — 1.4 `decode_token`이 `options={"require":["exp"]}` 적용).
    - ③ `if payload.get("type") != "access": raise InvalidTokenError()` (**토큰 혼동 가드** — refresh 토큰을 access로 오용 차단. 1.4 refresh의 `type=="refresh"` 가드와 대칭).
    - ④ `try: user_id = UUID(payload["user_id"]) except (KeyError, ValueError, TypeError): raise InvalidTokenError()` (payload 형식 가드 — 500 방지, 1.4 refresh와 동일 패턴).
    - ⑤ `user = await UserRepository(db).get_by_id(user_id)`. `if user is None or not user.is_active: raise InvalidTokenError()` (재조회로 현재 상태 반영 — 비활성/삭제 즉시 차단, **AC2/FR19/20**). `get_by_id`는 `deleted_at IS NULL` 필터 내장(1.4 추가).
    - ⚠️ **이름 충돌(1.4 계승):** PyJWT 베이스 `jwt.InvalidTokenError`(except) vs 도메인 `InvalidTokenError`(raise) 동명. `import jwt`로 모듈 접근해 구분 — 1.4 `services/auth.py`와 동일 해법.
  - [x] `def require_role(*allowed: UserRole) -> Callable`: `get_current_user`에 의존하는 가드 의존성을 반환하는 팩토리.
    - 내부 `async def _guard(current_user: User = Depends(get_current_user)) -> User: if current_user.user_role not in allowed: raise ForbiddenError(); return current_user`.
    - 호출 예: `Depends(require_role(UserRole.ADMIN))`, `Depends(require_role(UserRole.CUSTOMER, UserRole.PRO))`. **`UserRole` enum으로 인자**(문자열 아님 — 타입 안전·오타 방지).
  - [x] `CurrentUser = Annotated[User, Depends(get_current_user)]` 타입 별칭 추가 — 이후 라우터가 `current_user: CurrentUser`로 간결히 주입(다운스트림 ergonomics). 보호 라우트는 이 별칭 또는 `require_role(...)` 결과를 주입.
  - [x] ❌ **소유권 검사를 deps.py에 두지 않는다** — get_current_user/require_role은 HTTP 의존성(요청 단위), 소유권은 자원을 받는 service 계층 관심사. 소유권 헬퍼는 Task 4(core/authz.py).

- [x] **Task 4 — core/authz.py(NEW): 소유권 검사 헬퍼** (AC: 4)
  - [x] `def ensure_owner_or_admin(resource_owner_id: UUID, current_user: User) -> None`:
    - `if current_user.user_role == UserRole.ADMIN: return` (관리자=전체 허용).
    - `if current_user.id != resource_owner_id: raise ForbiddenError()` (본인 자원만).
    - 일치 시 무반환(통과). **service 메서드 내부에서 호출**하는 순수 함수(DB·HTTP 무관).
  - [x] 모듈 docstring: "소유권 검사 단일 시행 지점(NFR4). Epic 2(요청)·3(견적)·4(채팅) service가 자원 소유자 id와 current_user를 넘겨 호출. 라우터/클라이언트에 권한 분산 금지(AR8, anti-pattern: architecture line 342)."
  - [x] ⚠️ **과설계 금지(architecture line 288):** 클래스·레지스트리 없이 함수 하나로 시작. 더 복잡한 정책(자원별 가시성 등)이 필요해지면 그때 확장. 이 스토리는 최소 프리미티브만.

- [x] **Task 5 — routers/users.py(NEW) + main.py 등록: GET /api/v1/users/me** (AC: 5)
  - [x] `routers/users.py` 신규: `router = APIRouter(prefix="/api/v1/users", tags=["users"])`. architecture 태그 규약(users 도메인, line 422·450) 정합.
  - [x] `@router.get("/me", response_model=UserRead)` `async def read_me(current_user: CurrentUser) -> User: return current_user`. **함수명 `read_me`**(operationId 안정화, Orval 함수명 직결 — 소비는 1.7, AR9). 보호=`CurrentUser`(get_current_user) 주입만으로 충족 — 모든 역할 접근 가능(자기 정보).
  - [x] `main.py`: `from app.routers.users import router as users_router` + `app.include_router(users_router)` 추가. **기존 `auth_router`·`health` 라우터·예외 핸들러 등록 보존**(append만). import 순서·등록 위치는 `auth_router` 다음.
  - [x] `UserRead`(schemas/auth.py, 1.3) **재사용** — 신규 스키마 불요. `created_at`/`updated_at` 포함, `password_hash` 미포함(안전 표현). ⚠️ `UserRead`가 현재 `schemas/auth.py`에 있음 — 이동하지 말고 그대로 import(`from app.schemas.auth import UserRead`). (장기적으로 `schemas/user.py` 분리 여지는 있으나 이 스토리 범위 외 — 과설계 금지.)

- [x] **Task 6 — 테스트: RBAC 프리미티브 검증** (AC: 1, 2, 3, 5, 6)
  - [x] **`tests/test_users_me.py`(NEW) — 실 라우트 E2E(get_current_user, AC1/2/5):** 기존 `client_db`/`db_session` 픽스처 재사용(실 DB + SAVEPOINT 롤백). 토큰은 `create_access_token(user.id, user.user_role)`로 직접 생성(login 거치지 않아도 됨 — get_current_user만 검증).
    - **성공(AC5):** savepoint 내 사용자 시드(`/signup` 또는 `db_session` 직접 insert) → 유효 access로 `GET /users/me` → 200, `UserRead`(`displayName`/`email`/`userRole`/`isActive`, `passwordHash` 키 부재).
    - **토큰 누락(AC1):** Authorization 헤더 없이 → 401 `{code:"not_authenticated"}`.
    - **위조/형식오류(AC1):** `Bearer garbage.token` → 401 `{code:"invalid_token"}`.
    - **만료 access(AC1):** 과거 `exp`로 `jwt.encode` 직접 생성 → 401 `invalid_token`(대기 불가 → 직접 인코딩, 1.4 함정 #4 계승).
    - **type 혼동(AC1):** `create_refresh_token(user.id)`로 만든 refresh 토큰을 `/users/me`에 제출 → 401 `invalid_token`(type 가드).
    - **발급 후 비활성화(AC2, FR19/20 증명):** 유효 access 발급 → `db_session`에서 해당 user `is_active=False` → 동일 토큰으로 `/users/me` → 401 `invalid_token`. **이 테스트가 매-요청 재조회 설계의 핵심 근거.**
  - [x] **`tests/test_rbac_guards.py`(NEW) — 격리 테스트 앱(require_role, AC3/6):** **가짜 프로덕션 엔드포인트를 prod 앱에 만들지 않는다.** 테스트 모듈 안에서 최소 `FastAPI()` 앱을 만들고 더미 보호 라우트를 붙여 가드만 검증(`main.register_exception_handlers(test_app)`로 동일 envelope 적용 — main.py가 이 용도로 핸들러를 분리해 둠, conftest/main docstring 참조). `get_db`는 `test_app.dependency_overrides[get_db]`로 `db_session` 주입.
    - 더미 라우트 예: `@test_app.get("/admin-only")` → `Depends(require_role(UserRole.ADMIN))`; `@test_app.get("/pro-or-customer")` → `Depends(require_role(UserRole.CUSTOMER, UserRole.PRO))`.
    - **역할 허용(AC3):** admin 사용자 시드 + 토큰 → `/admin-only` 200. customer 토큰 → `/pro-or-customer` 200.
    - **역할 거부(AC3):** customer 토큰 → `/admin-only` 403 `{code:"forbidden"}`. admin 토큰 → `/pro-or-customer` 403.
    - **401→403 순서(AC3):** 토큰 누락으로 `/admin-only` → 403이 아니라 **401**(get_current_user가 먼저 차단). 가드 적용 전 인증이 선행됨을 증명.
  - [x] **`tests/test_authz_helper.py`(NEW) — 소유권 헬퍼 단위(AC4):** `ensure_owner_or_admin`를 직접 호출(DB·HTTP 불요, 순수 함수).
    - 본인 자원(`current_user.id == resource_owner_id`) → 예외 없음(통과).
    - 타인 자원 + customer/pro → `ForbiddenError`(pytest.raises).
    - 타인 자원 + admin → 통과(전체 허용). `User` 객체는 `id`/`user_role`만 채운 경량 인스턴스로 충분(DB 시드 불요).
  - [x] **기존 테스트 회귀 0 확인:** test_auth_signup / test_auth_login / test_seed / test_health / test_error_envelope. `uv run pytest -q` 전체 통과 + `uv run ruff check .` clean.

## Dev Notes

### 🎯 스코프 경계 (범위 침범 금지)

- ✅ **이 스토리:** `deps.get_current_user`/`require_role`/`CurrentUser` 별칭, `core/authz.ensure_owner_or_admin`, `core/security.oauth2_scheme`, 예외 `NotAuthenticatedError`(401)·`ForbiddenError`(403), `GET /api/v1/users/me`(+ users 라우터 등록), RBAC 테스트 3종. 신규 테이블·마이그레이션 **없음**(`users` 1.3 재사용).
- ❌ **소유권 헬퍼의 실 적용 금지** — `service_requests`·`quotes`·`chat_rooms` 도메인 service에서 `ensure_owner_or_admin`를 실제로 호출하는 것은 **Epic 2/3/4**. 1.5는 헬퍼 + 패턴 + 단위 테스트까지. 가짜 자원/도메인을 만들지 않는다.
- ❌ **가짜 프로덕션 보호 엔드포인트 금지** — `require_role`를 증명하려고 prod 앱에 인위적 라우트를 붙이지 않는다. **격리 테스트 앱**으로 검증(Task 6). prod에 추가되는 보호 엔드포인트는 `/users/me` **하나뿐**(실수요: 1.7).
- ❌ **프론트/Orval/api-client는 1.7.** 이 스토리는 백엔드 가드 + OpenAPI 계약(`/users/me`, `read_me` operationId)까지. App Router 라우트 가드(AR17, UX 보조)도 1.7/클라이언트 관심사.
- ❌ **토큰 회전·블랙리스트·`/logout` 금지**(1.4 AC4 — 무상태 유지). access 무효화는 여전히 없음 — 단, get_current_user의 매-요청 재조회가 **비활성/삭제**는 즉시 반영(아래 결정 사항).
- ❌ **service 계층의 기존 login/refresh 변경 금지.** 그들은 미인증 공개 행위로 유지. RBAC는 *새* 보호 엔드포인트(`/users/me`)와 *미래* 도메인에만 적용.

### ⚖️ 결정 사항 (Dev가 그대로 채택 — 1.4와의 정합 reconcile)

- **🔑 get_current_user는 매 요청 DB 재조회로 is_active를 확인한다(비활성화 즉시 효력).**
  - **무엇:** access 토큰이 유효해도 `get_by_id`로 현재 사용자를 재조회해 `is_active`(+ `deleted_at IS NULL`)를 검사 → 비활성/삭제면 401.
  - **왜:** FR19/20(비활성 계정 차단)을 **인증 경계 한 곳에서 중앙 시행** — 이후 Epic 2/3/4 각 도메인이 매번 is_active를 재검사할 필요가 없다(NFR4 권한 일관성). 비용은 PK 인덱스 조회 1회.
  - **1.4와의 reconcile(중요):** 1.4 story(line 123)는 "무상태 access라 비활성화는 **다음 refresh 시점**에 효력(최대 access 수명 지연)"이라 명시했다. 1.5는 이를 **의도적으로 강화** — 비활성화가 이제 **다음 인증 요청에서 즉시** 효력을 갖는다(strictly stronger, 보안상 더 안전). 1.4 메모는 "refresh만 재조회"를 전제했고, 1.5가 보호 엔드포인트 진입 지점에도 재조회를 추가하면서 그 한계가 해소된다. **리뷰어가 1.4 메모와의 불일치를 결함으로 오인하지 않도록 명시.** (refresh의 재조회는 그대로 유지 — 중복 아님: refresh는 토큰 재발급 시점, get_current_user는 자원 접근 시점.)
  - **트레이드오프:** 보호 요청마다 DB 조회 1회 추가. MVP 트래픽·인덱스 PK 조회 비용 무시 가능. 캐싱·세션 저장은 과설계(Post-MVP) — 도입하지 않는다.
- **401 두 종류 분리(누락 vs 무효):** 토큰 **누락**=`not_authenticated`, 토큰은 있으나 **무효**(만료/위조/type/형식/비활성)=`invalid_token`(1.4 재사용). 둘 다 401이나 `code`로 클라이언트가 "로그인 필요" vs "세션 만료→refresh 시도"를 구분 가능(1.7 인터셉터 로직에 유용). anti-enumeration 우려 없음 — 사용자 식별 정보 미노출.
- **require_role는 `get_current_user` 위에 합성(401이 403보다 선행):** 미인증이면 역할을 따질 것도 없이 401. 가드가 인증을 내포하므로 보호 라우트는 `require_role(...)` **하나만** 붙여도 인증+인가가 동시 적용된다(이중 의존성 불요).

### ⚠️ 알려진 함정 (런타임 디버깅 전 미리 적용 — 고가치)

1. **`OAuth2PasswordBearer(auto_error=False)` 필수:** 기본값 `True`면 토큰 누락 시 FastAPI가 자체 `HTTPException(401, headers={"WWW-Authenticate":"Bearer"})`를 던진다 → 우리 envelope 핸들러의 **HTTPException 분기**로 가서 `{code:"http_401"}`가 된다(우리 표준 `not_authenticated` 아님). `False`로 두고 `None`을 받아 도메인 예외를 던져야 안정 `code`가 보장된다. **이 한 줄이 envelope 일관성의 핵심.**
2. **이름 충돌 `InvalidTokenError`(1.4 계승):** 도메인 예외 vs PyJWT 베이스가 동명. deps.py에서 `import jwt` 후 `except jwt.InvalidTokenError`로 잡고 `raise InvalidTokenError()`(도메인)로 변환. 1.4 `services/auth.py`가 같은 해법 — 그대로 복제.
3. **`type=="access"` 가드 누락 시 토큰 혼동:** 가드가 없으면 장수명 refresh 토큰을 access처럼 써서 보호 자원에 접근 가능. 1.4 refresh가 `type=="refresh"`를 강제하듯, get_current_user는 `type=="access"`를 강제 — 대칭 유지.
4. **payload 형식 가드(KeyError/ValueError/TypeError → 401):** 서명은 유효하나 `user_id` 누락·비-UUID인 변조 토큰은 `UUID(payload["user_id"])`에서 던져 **500**으로 샐 수 있다. try/except로 감싸 동일 401(`invalid_token`)로 정규화 — 1.4 refresh의 동일 패치(Review Patch) 계승.
5. **격리 테스트 앱에 핸들러 등록 필수:** 테스트용 `FastAPI()`에 `register_exception_handlers(test_app)`를 호출하지 않으면 `AppError`(403/401)가 envelope로 변환되지 않고 500이 된다. main.py가 핸들러를 함수로 분리해 둔 이유가 이것(main.py docstring·conftest 주석 참조). `get_db`도 `test_app.dependency_overrides`로 별도 주입.
6. **만료 토큰 테스트는 대기 불가:** 과거 `exp`로 `jwt.encode({...,"type":"access","exp": <past>}, settings.jwt_secret, "HS256")` 직접 생성해 401 검증(1.4 함정 #4). `create_access_token` 시그니처를 더럽히지 않는다.
7. **`require_role` 인자는 `UserRole` enum:** 문자열(`"admin"`)이 아니라 `UserRole.ADMIN`. `current_user.user_role`이 `UserRole` 멤버(`str` 혼합 enum)라 `in` 비교가 enum끼리 일관. 문자열 혼용은 미묘한 불일치 위험.
8. **get_current_user의 DB 의존성:** `db: AsyncSession = Depends(get_db)`를 주입해 재조회. 테스트(prod 라우트)는 `client_db`가 이미 `get_db`를 롤백 세션으로 override하므로 추가 설정 불요. 격리 앱만 직접 override.

### 현재 코드 상태 (UPDATE/NEW 대상 — 보존할 것)

Story 1.3(가입)·1.4(로그인/refresh)가 auth 슬라이스를 완성. 아래는 현재 실제 상태이며 **덮어쓰지 말고 확장/추가**한다:

- **`app/deps.py`** (UPDATE — 스텁→구현): 현재 **docstring만** 존재("Story 1.5에서 get_current_user/require_role 구현"). → 실제 구현으로 채움. 보존할 코드 없음(스텁), docstring은 갱신·확장.
- **`app/core/security.py`** (UPDATE): `hash_password`/`verify_password`/`dummy_verify_password`/`create_access_token`/`create_refresh_token`/`decode_token` 존재(1.3/1.4). → `oauth2_scheme = OAuth2PasswordBearer(...)` **추가**. 모듈 docstring의 "get_current_user/require_role은 1.5" 문구를 "가드는 deps.py, 추출 스킴은 여기"로 정정. **기존 함수 보존.**
- **`app/core/exceptions.py`** (UPDATE): `AppError` + `DuplicateEmailError`(409)·`InvalidCredentialsError`(401)·`InvalidTokenError`(401) 존재. → `NotAuthenticatedError`(401)·`ForbiddenError`(403) **추가**(동일 패턴). **기존 보존.**
- **`app/core/authz.py`** (NEW): `ensure_owner_or_admin` 신규 파일.
- **`app/repositories/users.py`** (그대로 — 소비만): `get_by_id`(`deleted_at IS NULL`)·`get_by_email`·`create` 존재(1.4 `get_by_id` 추가됨). get_current_user가 `get_by_id` **재사용** — 신규 메서드 불요.
- **`app/routers/users.py`** (NEW): `/users/me` 라우터. **`routers/auth.py`(signup/login/refresh) 패턴 복제**(prefix·tags·함수명 operationId).
- **`app/main.py`** (UPDATE, append): `auth_router`·`health`·예외 핸들러 등록 존재. → `users_router` include **추가**. **기존 등록·핸들러 분리 구조 보존.**
- **`app/schemas/auth.py`** (그대로 — 재사용): `UserRead`(id/email/displayName/userRole/isActive/createdAt/updatedAt, passwordHash 제외) 존재. `/users/me` 응답에 **그대로 재사용**(이동·복제 금지).
- **`app/models/user.py`** (그대로): `User`(+`is_active`/`is_seed`)·`UserRole`(customer/pro/admin, str 혼합 enum, values_callable 소문자). require_role/authz가 `UserRole`·`is_active` 소비. 변경 없음.
- **`tests/conftest.py`** (그대로 — 재사용): `client`(가짜 세션), `db_session`/`client_db`(실 DB SAVEPOINT 롤백, NullPool, `expire_on_commit=False`). RBAC 테스트가 `client_db`/`db_session` **그대로 사용**. 격리 앱 테스트는 `db_session`만 받아 자체 `test_app`에 override.
- **`pyproject.toml`** (검토만): `pyjwt`·`pwdlib`·`fastapi`(OAuth2PasswordBearer 내장) 모두 설치됨. → **신규 의존성 0건.**
- **`alembic/`** (변경 없음): 신규 마이그레이션 **없음** — `users` 재사용.

### 아키텍처 준수 (반드시 따를 규약)

- **인가 경계:** `deps.get_current_user`(JWT 검증) + `require_role`(역할 가드). 권한은 **service 계층 소유권 검사**(고객=본인, 고수=본인, 관리자=전체).
  [Source: architecture.md#Architectural Boundaries (line 442, 449-452), AR8]
- **권한 단일 시행:** 모든 권한·소유권 검사는 service 계층, 라우터/클라이언트 분산 금지. (라우터 직접 권한 검사 = anti-pattern.)
  [Source: architecture.md#Coherence Rules (line 327), Anti-Patterns (line 342), NFR4]
- **인증 방식:** FastAPI `OAuth2PasswordBearer` + `Depends` 가드, `user_role`로 역할 분기. Bearer 헤더 통일.
  [Source: architecture.md#Authentication & Security (line 186, 191), AR8/AR10]
- **계층:** router(HTTP·검증·Depends) → service(비즈니스·권한·트랜잭션) → repository(DB·`deleted_at IS NULL`). 역방향 금지.
  [Source: architecture.md#Structure Patterns (line 284-289, 443)]
- **에러 envelope:** `{code, message, detail?}` + HTTP status. `code`=기계 판독 안정 식별자, `message`=한국어. 403=forbidden, 401=인증.
  [Source: architecture.md#Format Patterns (line 298-299), API Patterns (line 203)]
- **API 패턴:** `/api/v1` 프리픽스, 태그=도메인(users), operationId=함수명 안정화(`read_me`). 성공 응답=리소스 직접 반환(불필요 래핑 금지).
  [Source: architecture.md#API & Communication Patterns (line 199-202), Format (line 297), AR9]
- **명명:** Python snake_case 함수, PascalCase 클래스, 스키마 PascalCase+접미사. JSON 경계 camelCase(`CamelModel`). PK=`id`(UUIDv7).
  [Source: architecture.md#Naming Patterns (line 256-275)]
- **소프트삭제/비활성:** 계정=`is_active`, 삭제=`deleted_at`. 조회 공통 필터 `deleted_at IS NULL`. 물리삭제 금지.
  [Source: architecture.md#Data Architecture (line 176-177), NFR7]
- **검증:** Pydantic v2, 서버 검증 신뢰(클라이언트 검증만 신뢰 금지, NFR3).
  [Source: architecture.md#Data Architecture (line 182), Anti-Patterns (line 344)]

### 라이브러리/버전 (검증 완료 — 그대로 사용)

- FastAPI 0.136.x(`OAuth2PasswordBearer` 내장 `fastapi.security`) · SQLAlchemy 2.0.36(async+asyncpg) · Pydantic 2.10 · **PyJWT 2.13**(1.4 검증: `ExpiredSignatureError`/`DecodeError`/`InvalidSignatureError` 모두 `jwt.InvalidTokenError` 서브클래스) · pwdlib[argon2] 0.2.1+ · uuid7 0.1.0+ · Python 3.12.8. 모두 `.venv` 설치·검증(2026-06-08, Supabase PG17.6 연결 OK).
- **신규 의존성: 없음.** `OAuth2PasswordBearer`는 FastAPI 표준 — 추가 설치 불요.
- **uv 실행(1.2~1.4 계승):** 이 PC는 uv managed standalone 3.12 실행 불가 → `[tool.uv] python-preference="only-system"` 유지, `uv sync`/`uv run pytest`/`uv run ruff check .` 사용.
  [Source: 1-4 story 라이브러리 섹션, backend-env-setup 메모, architecture.md#Coherence Validation]

### 파일 구조 (생성/수정 위치)

```
apps/api/
  app/
    deps.py              (UPDATE 스텁→구현) get_current_user, require_role, CurrentUser
    core/
      security.py        (UPDATE) oauth2_scheme = OAuth2PasswordBearer(auto_error=False)
      exceptions.py      (UPDATE) NotAuthenticatedError(401), ForbiddenError(403)
      authz.py           (NEW) ensure_owner_or_admin(resource_owner_id, current_user)
    routers/
      users.py           (NEW) GET /api/v1/users/me (read_me)
    main.py              (UPDATE, append) users_router include
    schemas/auth.py      (그대로 — UserRead 재사용)
    repositories/users.py(그대로 — get_by_id 재사용)
    models/user.py       (그대로 — UserRole/is_active 소비)
  tests/
    test_users_me.py     (NEW) get_current_user 실 라우트 E2E(성공/누락/위조/만료/type/발급후비활성화)
    test_rbac_guards.py  (NEW) require_role 격리 앱(허용/거부/401선행)
    test_authz_helper.py (NEW) ensure_owner_or_admin 단위(본인/타인/관리자)
    conftest.py          (그대로 — db_session/client_db 재사용)
  # alembic: 신규 마이그레이션 없음
  # pyproject.toml: 신규 의존성 없음
```
[Source: architecture.md#Complete Project Directory Structure (line 414-426), 1-4 story 파일 구조]

### 테스트 표준

- pytest + `pytest-asyncio`(`asyncio_mode=auto`) + httpx `AsyncClient`(`ASGITransport`) + `dependency_overrides`. **도메인/보호 라우트 테스트는 실 DB + SAVEPOINT 롤백**(`db_session`/`client_db` 재사용 — fake repo 금지: is_active 즉시차단·재조회를 실 DB로 증명).
- **격리 테스트 앱 패턴(핵심):** require_role 검증은 prod 라우트 오염 없이 테스트 모듈 내 `FastAPI()` + `register_exception_handlers` + `get_db` override로(main.py가 이 용도로 핸들러 분리). 가짜 prod 엔드포인트 금지.
- 토큰은 `create_access_token`/`create_refresh_token`(1.4) 직접 호출 또는 과거 exp `jwt.encode`(만료 케이스)로 생성. 핵심 경로 우선(성공/누락/무효/만료/type/발급후비활성화/역할허용·거부/소유권). CI(`pytest`)는 Story 1.8에서 GitHub Actions + `DATABASE_URL` 시크릿 연결.
  [Source: architecture.md#Structure Patterns (line 289), 1-4 story 테스트 표준, main.py/conftest.py docstring]

### Project Structure Notes

- 정합: `get_current_user`/`require_role`가 `deps.py`에, 소유권 헬퍼가 `core/authz.py`에, 보호 엔드포인트가 도메인 라우터(`users`)에 사는 것은 architecture 디렉터리 구조(line 414-426)·경계(line 442) 그대로.
- 변이 없음: 신규 패턴 도입(403 envelope, OAuth2 스킴)은 architecture가 이미 예고한 것(line 191, 442)의 구현. 새 아키텍처 결정 없음.
- `apps/api`는 Turborepo 그래프 외부(uv/uvicorn 별도 파이프라인) — 1.2~1.4 계승.

### 이전 스토리(1.4) 학습 / 정합

- **1.4 토큰 규약 직접 소비:** access payload `{user_id, user_role, type:"access", exp}`를 get_current_user가 동일 키로 읽는다. 1.4가 "1.5가 동일 키로 읽으니 변경 금지"라 명시한 계약을 이행. `user_role`은 소문자 값(`"customer"/"pro"/"admin"`) → `UserRole(payload값)` 또는 재조회한 `user.user_role`(enum) 사용. **재조회 user의 enum을 쓰는 게 더 안전**(토큰 stale 무관).
- **1.4 refresh 재조회 설계 계승·확장:** refresh가 FR19/20 위해 재조회하듯, get_current_user도 재조회로 비활성/삭제 즉시 차단. 같은 보안 원칙을 인증 경계로 확장(결정 사항 참조).
- **1.4 Review Patch 패턴 사전 적용:** payload 형식 가드(try/except → 401), exp 필수(`decode_token`이 이미 `require:["exp"]`), DoS 상한(이 스토리 신규 입력 없음 — 해당 없음). 1.4가 겪은 "500 누수" 함정을 get_current_user에서 처음부터 막는다.
- **1.4 무관 defer 항목 확인:** deferred-work.md(소프트삭제 이메일 재가입·IntegrityError 매핑·CORS wildcard·enum drop)는 가입/마이그레이션/CORS 경로 — RBAC와 무관. 단, get_current_user의 `get_by_id`도 `deleted_at IS NULL`을 지켜 삭제 계정이 토큰으로 부활하지 못하게 한다(소프트삭제 일관성 원칙 공유).
  [Source: 1-4-login-logout-jwt.md, deferred-work.md]

### References

- [Source: epics.md#Story 1.5: 역할 기반 접근 제어(RBAC) (line 275-293)] — 3개 AC 원본(BDD): get_current_user/require_role 가드(401/403), service 소유권 단일 시행, pytest 허용/거부
- [Source: epics.md#Story 1.4 (line 251-273), Story 1.6 (line 295-313), Story 1.7 (line 315-337)] — 1.4 토큰 규약 소비, 1.6 카테고리(첫 require_role 미적용 읽기), 1.7 Orval/api-client/`/users/me` 소비
- [Source: architecture.md#Authentication & Security (line 184-195)] — OAuth2PasswordBearer+Depends 가드, user_role 분기, service 소유권 검사
- [Source: architecture.md#Architectural Boundaries (line 438-457)] — 인증 경계 deps.get_current_user+require_role, service 단일 소유 소유권/상태/소프트삭제
- [Source: architecture.md#API & Communication Patterns (line 197-207), Format Patterns (line 297-302)] — `/api/v1`, users 태그, operationId, 에러 envelope({code,message}), 403 status
- [Source: architecture.md#Coherence Rules (line 325-329), Anti-Patterns (line 341-345)] — 권한 service 단일 시행, 라우터 직접 권한 검사 금지
- [Source: architecture.md#Complete Project Directory Structure (line 414-426)] — deps.py(get_current_user/require_role), security.py(OAuth2PasswordBearer), users 라우터 위치
- [Source: AR8 (epics.md line 84)] — REST 단일 경유, RLS 미사용, 앱 레벨 권한 일원화 / [Source: FR4, FR19/20, NFR3/NFR4] — 역할 접근 제어·비활성 차단·권한 일관성
- [Source: 1-4-login-logout-jwt.md] — 토큰 규약·이름충돌·payload가드·재조회 설계·테스트 선례(security/exceptions/deps 현재 상태, is_active 결정 reconcile 대상)
- [Source: backend-env-setup 메모, manual-setup-checkpoints 메모] — uv only-system, JWT_SECRET 검증됨, AR23 수동 체크포인트 선안내 원칙

## ⚡ 수동 설정 체크포인트 (AR23 — dev-story 진입 전 KTH 확인)

- **신규 외부 설정 없음.** RBAC는 기존 `apps/api/.env`의 `JWT_SECRET`(1.2 설정·검증)과 `users` 테이블(1.3)만 사용한다. Supabase/Railway/Expo 추가 작업 불요(1.4와 동일).
- **검증용(선택):** `/users/me`를 실 계정으로 확인하려면 1.3 시드 관리자 또는 `/signup`→`/login`으로 받은 access 토큰을 `Authorization: Bearer`로 `GET /api/v1/users/me`에 보내면 된다. 테스트는 savepoint 내 자체 시드로 동작하므로 별도 계정 없이 통과한다.
- **확인 요청:** 위 "신규 설정 없음"이 맞는지(=`.env`의 `JWT_SECRET`이 여전히 유효한지) KTH가 확인하면 dev-story 진입. 시크릿 회전이 있었다면 `.env` 갱신 필요.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Claude Opus 4.8, 1M context) — BMad dev-story 워크플로우

### Debug Log References

- `uv run ruff check .` → All checks passed (clean)
- `uv run pytest -q` → 52 passed (기존 35 회귀 0 + 신규 17)

### Completion Notes List

- **Task 1 (exceptions):** `NotAuthenticatedError`(401, `not_authenticated`)·`ForbiddenError`(403, `forbidden`)를 기존 `AppError` 서브클래스 패턴 그대로 append. 403은 이 스토리가 처음 도입 — 전역 핸들러가 `AppError.status_code`를 그대로 쓰므로 핸들러 수정 불요(자동 envelope). 기존 예외 전부 보존.
- **Task 2 (security):** `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)` 추가. `auto_error=False`로 토큰 누락 시 `None`을 넘겨 deps가 도메인 예외로 변환(envelope code 일관성의 핵심). 모듈 docstring 정정(추출 스킴=여기, 가드=deps.py). 라이브러리 계층 유지(도메인 예외 import 없음).
- **Task 3 (deps):** 스텁→구현. `get_current_user`(누락→401 not_authenticated / 디코드·type·형식·재조회 실패→401 invalid_token, 매 요청 `get_by_id` 재조회로 비활성·삭제 즉시 차단), `require_role(*UserRole)` 팩토리(get_current_user 합성 → 401 선행), `CurrentUser` 타입 별칭. PyJWT `jwt.InvalidTokenError` vs 도메인 `InvalidTokenError` 이름 충돌은 `import jwt`로 해소(1.4 해법 계승).
- **Task 4 (authz):** `core/authz.py`(NEW) `ensure_owner_or_admin(resource_owner_id, current_user)` 순수 함수 — admin 전체 허용, 그 외 본인 자원만, 불일치 `ForbiddenError`. 과설계 금지(함수 하나). 첫 실사용은 Epic 2 이후.
- **Task 5 (users router):** `routers/users.py`(NEW) `GET /api/v1/users/me`(`read_me`, `CurrentUser` 주입, `UserRead` 재사용). `main.py`에 `users_router` include append(기존 라우터·핸들러 보존).
- **Task 6 (tests):** 신규 17 테스트 전부 통과 + 기존 35 회귀 0.
  - `test_users_me.py`(8): 성공(passwordHash 부재)·토큰누락(not_authenticated)·위조·만료·**유효서명+비-UUID payload(단계④ 형식가드)**·type혼동·**발급후비활성화**·**소프트삭제(deleted_at)**(AC2/FR19/20 키스톤·즉시차단 양 경로).
  - `test_rbac_guards.py`(5): 격리 `FastAPI()` 앱 + `register_exception_handlers` + `get_db` override. 역할 허용/거부 + **401→403 순서**(토큰 누락 시 403이 아닌 401 — 인증 선행 증명).
  - `test_authz_helper.py`(4): `ensure_owner_or_admin` 본인/타인(customer·pro)/admin 단위.
- **신규 의존성 0건, 신규 마이그레이션 0건**(`users` 1.3 재사용). 수동 외부 설정 없음(AR23 — JWT_SECRET·users 재사용).
- **1.4와의 reconcile 이행:** 1.4 "비활성화는 다음 refresh 시점 효력" 메모를 의도적으로 강화 — get_current_user 매-요청 재조회로 **다음 인증 요청에서 즉시** 효력(strictly stronger). 리뷰어 오인 방지 명시.

### File List

- `apps/api/app/core/exceptions.py` (UPDATE) — NotAuthenticatedError(401), ForbiddenError(403) 추가
- `apps/api/app/core/security.py` (UPDATE) — oauth2_scheme 추가, docstring 정정
- `apps/api/app/deps.py` (UPDATE, 스텁→구현) — get_current_user, require_role, CurrentUser
- `apps/api/app/core/authz.py` (NEW) — ensure_owner_or_admin
- `apps/api/app/routers/users.py` (NEW) — GET /api/v1/users/me (read_me)
- `apps/api/app/main.py` (UPDATE, append) — users_router include
- `apps/api/tests/test_users_me.py` (NEW) — get_current_user 실 라우트 E2E
- `apps/api/tests/test_rbac_guards.py` (NEW) — require_role 격리 앱
- `apps/api/tests/test_authz_helper.py` (NEW) — ensure_owner_or_admin 단위

### Change Log

| 날짜 | 변경 | 작성자 |
|------|------|--------|
| 2026-06-08 | Story 1.5 RBAC 구현 완료 — 인가 프리미티브(get_current_user/require_role/ensure_owner_or_admin) + GET /users/me + 테스트 17종. 전체 52 passed, ruff clean. Status → review | dev-story (Opus 4.8) |

## Review Findings (2026-06-08, bmad-code-review)

적대적 3-레이어 병렬 리뷰(Blind Hunter / Edge Case Hunter / Acceptance Auditor). 인수 기준 AC1–AC6 전부 SATISFIED, 차단 위반 0건. 아래는 트리아지 결과 — patch 5 / defer 3 / dismiss 1.

### Patch (수정 권장)

- [x] [Review][Patch] get_current_user: 비문자열 user_id(int/list/dict/float/bool) → AttributeError 미포착 → HTTP 500 누수 [apps/api/app/deps.py:67] — 단계④ `except (KeyError, ValueError, TypeError)`가 `UUID(int)` 등이 던지는 `AttributeError`('... no attribute replace')를 못 잡는다. None만 TypeError로 잡히고 그 외 비문자열은 모두 AttributeError → 전역 Exception 핸들러 → 500. docstring의 "비문자열(TypeError) 정규화" 주장과 모순(venv 경험적 검증 완료). 서명된 토큰(시크릿 보유) 필요라 방어심층 성격이나, 문서가 보장한 케이스가 실제 500을 낸다. **수정: except 튜플에 `AttributeError` 추가**(또는 `Exception`으로 광역화).
- [x] [Review][Patch] payload 형식 가드 테스트 보강: KeyError(user_id 누락)·비문자열 경로 미검증 [apps/api/tests/test_users_me.py:108] — `test_read_me_malformed_payload_401`이 `user_id="not-a-uuid"`(ValueError·문자열)만 커버. 위 500 누수 경로(비문자열)와 user_id 키 누락은 테스트 없음 → 회귀 미포착. **위 패치 검증용 케이스(int user_id, user_id 누락) 추가.** (blind+edge+auditor 합의)
- [x] [Review][Patch] /me 성공 테스트가 토큰-신원 바인딩 미증명 [apps/api/tests/test_users_me.py:49] — 사용자 1명만 시드해, `read_me`가 토큰 subject가 아닌 임의 사용자를 반환해도 통과. 두 번째 사용자 시드 후 A의 토큰 → A 반환 검증 추가 권장. (Low)
- [x] [Review][Patch] require_role() 빈 인자 풋건: 모든 사용자 403, 정의 시점 오류 없음 [apps/api/app/deps.py:77] — `require_role()`(allowed=())는 admin 포함 전원 403으로 라우트 영구 차단되나 등록 시점 경고 없음. deny-by-default라 보안 구멍은 아님. fail-fast 가드(`if not allowed: raise ValueError`) 추가 권장. (Low·선제적)
- [x] [Review][Patch] 빈 문자열 Bearer 토큰 → invalid_token (not_authenticated 아님) [apps/api/app/deps.py:50] — `Authorization: Bearer `(값 빈) 시 oauth2_scheme가 `None`이 아닌 `""` 반환 → 단계① 우회 → decode 실패 → invalid_token. 사실상 토큰 미전송이므로 not_authenticated가 의도(1.7 인터셉터가 두 code로 "로그인 필요" vs "refresh"를 분기). 빈/공백 토큰을 None처럼 처리 권장. (Low·의미론적)

### Defer (기존/범위 외 — 연기)

- [x] [Review][Defer] health 엔드포인트가 SQLAlchemyError만 포착 → 그 외 DB 장애는 500(문서상 503 아님) [apps/api/app/main.py:109] — deferred, pre-existing (Story 1.1)
- [x] [Review][Defer] verify_password가 모든 예외를 False로 흡수 → 해싱 파이프라인 버그 은폐 가능 [apps/api/app/core/security.py:53] — deferred, pre-existing (Story 1.3/1.4, 의도적 fail-closed)
- [x] [Review][Defer] ensure_owner_or_admin str-vs-UUID 호출 계약 잠재 위험(현재 호출자 없음) [apps/api/app/core/authz.py:28] — deferred, Epic 2-4 배선 시 타입 강제 필요

### Dismiss (오탐)

- 테스트 `db_session.commit()`이 롤백 격리를 깬다는 우려 → conftest가 `join_transaction_mode="create_savepoint"` 사용으로 commit을 SAVEPOINT에 가두고 teardown에서 전체 롤백, 격리 유지됨. Blind Hunter는 conftest 미접근(diff only)으로 추정만 했고 검증 결과 오탐.
