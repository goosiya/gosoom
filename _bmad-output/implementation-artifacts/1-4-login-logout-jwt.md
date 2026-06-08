---
baseline_commit: NO_VCS
---
# Story 1.4: 로그인/로그아웃 & 세션 갱신 (JWT)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 사용자(고객·고수·관리자),
I want 이메일+비밀번호로 로그인하고 세션이 만료돼도 재인증 없이 갱신되기를,
So that 끊김 없이 서비스를 이용하고 안전하게 로그아웃할 수 있다.

이 스토리는 **인증 토큰 계층**을 확립한다. Story 1.3이 세운 router→service→repository·`CamelModel`·실 DB 롤백 테스트 선례를 그대로 복제하면서, JWT 발급/검증(HS256)과 `verify_password`를 추가한다. 여기서 만든 토큰 발급 규약(payload·`type` 클레임·만료)을 **Story 1.5(`get_current_user`/`require_role`)가 소비**하고, **Story 1.7(api-client 인터셉터)이 login/refresh를 호출**한다. 신규 도메인 테이블·마이그레이션은 없다 — `users`(1.3)를 재사용한다.

## Acceptance Criteria

**AC1 — 로그인 성공 시 access + refresh 토큰 발급(HS256)**
**Given** 활성 사용자가
**When** `POST /api/v1/auth/login`에 올바른 자격증명(email + password)을 보내면
**Then** access 토큰(설정 수명 = `access_token_expire_minutes`, 기본 30분)과 refresh 토큰(`refresh_token_expire_days`, 기본 14일)이 발급되고, access JWT payload는 `{user_id, user_role, type:"access", exp}`(HS256)이다(FR2, AR11).

**AC2 — 잘못된 자격증명 / 비활성 계정 거부(401, 토큰 미발급)**
**Given** 잘못된 자격증명(존재하지 않는 이메일 또는 비밀번호 불일치)이거나 비활성(`is_active=false`) 계정일 때
**When** 로그인을 시도하면
**Then** 인증 실패(401)가 표준 envelope `{code:"invalid_credentials", message}`로 반환되고 토큰은 발급되지 않는다(FR19/20 차단 규칙 정합, NFR3 anti-enumeration: 세 경우 모두 동일한 일반 401).

**AC3 — refresh로 새 access 재발급**
**Given** 유효한 refresh 토큰이 있을 때(access 만료 여부는 서버 무관 — 클라이언트 관심사)
**When** `POST /api/v1/auth/refresh`를 호출하면
**Then** refresh 토큰을 검증(서명·만료·`type=="refresh"`)하고 해당 사용자를 **재조회**해 현재 `is_active`·`user_role`을 반영한 **새 access 토큰만** 재발급한다(FR3). 비활성화된 계정·삭제된 계정·`type` 불일치·만료·위조 토큰은 401(`invalid_token`).

**AC4 — 로그아웃(클라이언트 토큰 폐기, 서버 무상태)**
**Given** 로그인 상태에서
**When** 로그아웃하면
**Then** 클라이언트가 보유 토큰을 폐기하여 세션이 종료된다. **백엔드 산출물 없음** — Bearer 무상태로 서버 토큰 무효화(블랙리스트/회전)는 MVP 범위 외(의도된 단순화, architecture line 194). `/logout` 엔드포인트를 만들지 않는다.

## Tasks / Subtasks

- [x] **Task 1 — core/security.py: verify_password + JWT 발급/검증** (AC: 1, 2, 3)
  - [x] `verify_password(plain: str, hashed: str) -> bool` 추가: `password_hasher.verify(plain, hashed)`. pwdlib `verify`는 불일치 시 `False` 반환(또는 예외 — 라이브러리 동작 확인 후 `try/except`로 `False` 정규화). **존재하지 않는 사용자도 일반 401**(아래 service Task 4).
  - [x] `create_access_token(user_id: UUID, user_role: UserRole) -> str`: payload `{"user_id": str(user_id), "user_role": user_role.value, "type": "access", "exp": <now+access_token_expire_minutes>}`, `jwt.encode(payload, settings.jwt_secret, algorithm="HS256")`.
  - [x] `create_refresh_token(user_id: UUID) -> str`: payload `{"user_id": str(user_id), "type": "refresh", "exp": <now+refresh_token_expire_days>}` — **user_role 미포함**(refresh 시 재조회). HS256.
  - [x] `decode_token(token: str) -> dict`: `jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])`. PyJWT가 서명·만료를 자동 검증 → 실패 시 `jwt.InvalidTokenError`(만료=`ExpiredSignatureError`, 위조=`DecodeError` 모두 이 베이스의 서브클래스, **사용 전 확인**). 호출자(service)가 잡아 도메인 예외로 변환.
  - [x] **exp는 timezone-aware UTC**: `datetime.now(timezone.utc) + timedelta(minutes=...)`. PyJWT는 `exp`를 datetime/int 모두 수용(epoch로 인코딩).
  - [x] **클레임 이름은 architecture 규약 유지**: `user_id`(JWT 표준 `sub` 대신), `user_role`. 1.5 `get_current_user`가 동일 키로 읽는다 — 변경 금지.
  - [x] ⚠️ **스코프 경계:** 만료 override가 필요한 곳은 테스트뿐(과거 exp 토큰). `create_*`에 선택적 만료 인자를 두거나, 테스트에서 `jwt.encode`를 직접 호출(Task 6). 프로덕션 시그니처는 설정 수명 고정.

- [x] **Task 2 — schemas/auth.py: Login/Token/Refresh 스키마** (AC: 1, 3)
  - [x] `LoginRequest(CamelModel)`: `email: EmailStr`, `password: str`. **email after-validator로 strip+lower 정규화**(SignupRequest와 동일 — `get_by_email`도 정규화하므로 대소문자 무관 조회 일관). password에 길이 제약 불요(검증이 아닌 대조).
  - [x] `TokenResponse(CamelModel)`: `access_token: str`, `refresh_token: str`, `token_type: str = "bearer"`. 직렬화 시 `accessToken`/`refreshToken`/`tokenType`(camel 경계). 로그인 응답.
  - [x] `RefreshRequest(CamelModel)`: `refresh_token: str`.
  - [x] `RefreshResponse(CamelModel)`: `access_token: str`, `token_type: str = "bearer"`. **refresh 토큰 미포함** — 회전 없음(Post-MVP)을 OpenAPI/Orval 계약에 명시(AR9 소비는 1.7).
  - [x] ⚠️ **로그인 입력은 JSON `LoginRequest`(camelCase)**: architecture의 `OAuth2PasswordBearer`는 **1.5 보호 라우트의 토큰 추출기**이지 로그인 입력 형식이 아니다. `OAuth2PasswordRequestForm`(form-data) 사용 금지 — camelCase·Orval 일관성을 깬다.

- [x] **Task 3 — core/exceptions.py: 인증 도메인 예외 2종** (AC: 2, 3)
  - [x] `class InvalidCredentialsError(AppError)`: `code="invalid_credentials"`, `message="이메일 또는 비밀번호가 올바르지 않습니다."`, `status_code=401`. **로그인 실패 전반(미존재·비번불일치·비활성)에 단일 사용** — anti-enumeration(NFR3). (대안: 비활성 계정에 별도 `code`로 프론트가 "비활성화됨" 안내 → Dev Notes 트레이드오프 참조. 기본은 일반 401.)
  - [x] `class InvalidTokenError(AppError)`: `code="invalid_token"`, `message="유효하지 않은 토큰입니다."`, `status_code=401`. refresh 디코드 실패·`type` 불일치·비활성/삭제 사용자에 사용.
  - [x] 1.3 `DuplicateEmailError` 패턴 그대로 복제(AppError 서브클래스).

- [x] **Task 4 — repositories/users.py: get_by_id 추가** (AC: 3)
  - [x] `async def get_by_id(self, user_id: UUID) -> User | None`: `select(User).where(User.id == user_id, User.deleted_at.is_(None))` → `scalar_one_or_none()`. **소프트삭제 공통 필터 유지**. refresh가 토큰의 user_id로 현재 사용자 상태를 재조회하는 데 사용.
  - [x] 기존 `get_by_email`/`create`는 보존(변경 없음).

- [x] **Task 5 — services/auth.py: login + refresh** (AC: 1, 2, 3)
  - [x] `async def login(self, data: LoginRequest) -> TokenResponse`:
    - ① `user = await self.users.get_by_email(data.email)`.
    - ② `if user is None or not verify_password(data.password, user.password_hash): raise InvalidCredentialsError()`.
    - ③ `if not user.is_active: raise InvalidCredentialsError()` (FR19/20 차단 — 동일 일반 401).
    - ④ `return TokenResponse(access_token=create_access_token(user.id, user.user_role), refresh_token=create_refresh_token(user.id))`.
    - **commit 불필요**(읽기만 — 상태 변경 없음). 1.3 signup과 달리 트랜잭션 쓰기 없음.
    - (선택, anti-timing) user가 None일 때도 더미 `verify_password`를 호출해 응답 시간 차로 인한 이메일 존재 추론을 줄일 수 있다 — 낮은 우선순위, Dev Notes 참조.
  - [x] `async def refresh(self, data: RefreshRequest) -> RefreshResponse`:
    - ① `try: payload = decode_token(data.refresh_token) except jwt.InvalidTokenError: raise InvalidTokenError()`.
    - ② `if payload.get("type") != "refresh": raise InvalidTokenError()` (**access 토큰을 refresh로 오용 차단 — 토큰 혼동 가드**).
    - ③ `user = await self.users.get_by_id(UUID(payload["user_id"]))`. `if user is None or not user.is_active: raise InvalidTokenError()` (**FR19/20 증명: 발급 후 비활성화된 계정은 새 access를 발급받지 못한다**).
    - ④ `return RefreshResponse(access_token=create_access_token(user.id, user.user_role))` — **재조회한 현재 role 반영**, 새 access만.
  - [x] **이 흐름의 보안 목적(부수적 조회 아님):** refresh가 단순 재서명이 아니라 재조회하는 이유는 FR19/20 — 비활성화된 계정이 새 access를 발급받지 못하게 하기 위함. 이것이 refresh 설계의 핵심 의도다.

- [x] **Task 6 — routers/auth.py: POST /login, POST /refresh** (AC: 1, 2, 3)
  - [x] `@router.post("/login", response_model=TokenResponse)` `async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse: return await AuthService(db).login(data)`. status 200(기본). **함수명 `login`**(operationId 안정화, Orval 함수명 직결, AR9).
  - [x] `@router.post("/refresh", response_model=RefreshResponse)` `async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> RefreshResponse: return await AuthService(db).refresh(data)`. 함수명 `refresh`.
  - [x] 둘 다 **미인증 공개**(`get_current_user` 미적용 — 애초에 1.5 전이라 없음). 기존 `signup` 라우트·`router` 인스턴스 보존(append만).
  - [x] **`/logout` 만들지 않음**(AC4 — 서버 무상태).

- [x] **Task 7 — 테스트(실 DB + 롤백): test_auth_login.py** (AC: 1, 2, 3)
  - [x] `tests/test_auth_login.py` **신규**. 사용자 시드는 savepoint 안에서: `client_db`로 `POST /signup` 후 `POST /login`(권장 — E2E 경로), 또는 `db_session`에 `User(... password_hash=hash_password(...))` 직접 insert. 둘 다 롤백 격리.
    - **로그인 성공(AC1):** 200, 응답에 `accessToken`/`refreshToken`/`tokenType=="bearer"`. access 디코드 → `user_id`/`user_role`/`type=="access"`/`exp` 존재, `user_role`이 가입 역할과 일치.
    - **비밀번호 불일치(AC2):** 401 `{code:"invalid_credentials"}`, 응답에 토큰 키 부재.
    - **미존재 이메일(AC2):** 401 동일 envelope(메시지·code가 비밀번호 불일치와 동일 — anti-enumeration 확인).
    - **비활성 계정(AC2):** 가입 후 `db_session`에서 `is_active=False`로 변경 → 로그인 401, 토큰 미발급.
    - **refresh 성공(AC3):** login으로 받은 refreshToken → `POST /refresh` → 200, 새 `accessToken`(+ `tokenType`), `refreshToken` 키 **부재**(회전 없음 확인).
    - **type 혼동(AC3):** login의 **accessToken**을 `/refresh`에 제출 → 401 `invalid_token`(type 가드).
    - **만료 refresh(AC3):** 과거 `exp`로 `jwt.encode` 직접 생성(또는 `create_*` 만료 override) → `/refresh` 401.
    - **위조/형식오류(AC3):** `"garbage.token"` → 401.
    - **발급 후 비활성화(AC3, FR19/20 증명):** login → `db_session`에서 해당 user `is_active=False` → 동일 refreshToken으로 `/refresh` → 401(`invalid_token`). **이 테스트가 refresh 재조회 설계의 핵심 근거.**
  - [x] (선택) `verify_password` 단위 테스트: 올바른 평문→True, 틀린 평문→False, 1.3 가입 사용자의 `$argon2` 해시와 호환.
  - [x] **기존 테스트 보존:** test_auth_signup / test_seed / test_health / test_error_envelope 회귀 없음 확인. `ruff check .` 통과.

## Dev Notes

### 🎯 스코프 경계 (범위 침범 금지)

- ✅ **이 스토리:** `verify_password` + JWT 발급(access/refresh)/검증(`decode_token`), `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `get_by_id` 리포지토리 추가. 신규 테이블·마이그레이션 **없음**.
- ❌ **`get_current_user`/`require_role`(보호 라우트 가드)는 Story 1.5.** `deps.py`는 현재 스텁(주석만) 그대로 — **건드리지 않는다.** refresh의 토큰 디코드는 `security.decode_token` + service에 있지, `get_current_user` 의존성으로 만들지 않는다.
- ❌ **`/logout` 서버 엔드포인트·토큰 블랙리스트·refresh 회전 금지**(AC4 — 무상태, architecture line 194 Post-MVP). 클라이언트 토큰 폐기로 로그아웃(1.7).
- ❌ **Orval/api-client/프론트 UI는 Story 1.7.** access=메모리·refresh=웹 저장소/Expo SecureStore 보관과 401→refresh 1회 인터셉터는 1.7/5.1 관심사 — 이 스토리는 **백엔드 + OpenAPI 계약**까지(operationId 안정화만).
- ❌ **신규 도메인 테이블 금지.** `users`(1.3) 재사용. `is_active`(이미 존재)로 비활성 차단.

### 의도적 추가(epic AC 리터럴 초과 — 근거 명시, scope creep 아님)

1. **JWT `type` 클레임(access/refresh):** architecture 리터럴 payload는 `{user_id, user_role, exp}`지만, refresh 엔드포인트가 access 토큰을 refresh로 오용하는 **토큰 혼동 공격**을 막으려면 토큰 종류 식별이 필요. `type` 추가 + `/refresh`에서 `type=="refresh"` 강제. → 의도적 보안 강화.
2. **refresh payload에서 `user_role` 제외:** refresh는 재발급 시 사용자를 재조회해 **현재** role을 읽으므로 토큰에 role을 박아둘 필요가 없다(오히려 stale role 위험). refresh=`{user_id, type, exp}`만.
3. **`RefreshResponse`(refresh_token 미포함) 별도 스키마:** "회전 없음(새 access만)" 계약을 OpenAPI/Orval에 명시적으로 드러내기 위해 `TokenResponse`와 분리. 단일 스토리만 보면 과할 수 있으나 1.7 클라이언트가 응답 형태를 정확히 알게 한다.
4. **`get_by_id` 리포지토리 메서드:** refresh가 토큰 user_id로 현재 상태(is_active/role)를 재조회하는 데 필요. `deleted_at IS NULL` 공통 필터 유지.

### ⚖️ 결정 사항 (Dev가 그대로 채택, 트레이드오프 인지)

- **AC2 단일 일반 401(anti-enumeration):** 미존재 이메일·비밀번호 불일치·비활성 계정 **모두** `invalid_credentials` 동일 메시지/code. 공격자가 응답으로 이메일 존재·계정 상태를 추론하지 못하게 함(NFR3).
  - **트레이드오프:** 비활성화된 정상 사용자가 "이메일/비밀번호 오류"라는 혼동 메시지를 받는다. 만약 프론트가 "비활성화된 계정입니다" 안내를 줘야 한다면 비활성 케이스에 별도 `code`(예: `account_inactive`)가 필요 — 그 경우 enumeration 노출을 감수. **기본 결정 = 일반 401(보안 우선).** 운영 정책상 안내가 필요해지면 후속에서 분리.
- **refresh 비활성화 반영 지연(의도된 MVP 동작):** 무상태 access는 발급 후 수명(≤30분) 동안 무효화 불가. 따라서 계정 비활성화(FR19/20)는 **다음 refresh 시점**에 효력 발생(최대 access 수명만큼 지연). 버그 아님 — architecture line 189/194의 의도된 단순화. 리뷰어가 결함으로 보지 않도록 명시.

### ⚠️ 알려진 함정 (런타임 디버깅 전 미리 적용 — 고가치)

1. **PyJWT 예외 계층 확인:** `jwt.ExpiredSignatureError`·`jwt.DecodeError`·`jwt.InvalidSignatureError`는 모두 `jwt.InvalidTokenError`의 서브클래스 — service는 `except jwt.InvalidTokenError`로 한 번에 잡아 `InvalidTokenError`(우리 도메인 예외, **이름 충돌 주의** — `from app.core.exceptions import InvalidTokenError as ...` 또는 jwt를 모듈로 import)로 변환. 사용 전 설치된 PyJWT(>=2.10) 동작 1회 확인.
2. **UUID JSON 직렬화:** JWT payload에 `UUID`를 그대로 넣으면 인코딩 실패 → `str(user_id)`로 저장, 디코드 후 `UUID(payload["user_id"])`로 파싱해 `get_by_id` 조회.
3. **timezone-aware exp:** `datetime.now(timezone.utc)` 사용(naive `datetime.utcnow()` 금지 — PyJWT 만료 비교가 어긋날 수 있음). `timedelta`로 가산.
4. **만료 토큰 테스트는 대기 불가:** 과거 `exp`로 토큰을 직접 만들어 401을 검증(`jwt.encode({...,"exp": now-1d}, secret, "HS256")`). `create_*` 시그니처를 더럽히지 않으려면 테스트에서 직접 인코딩 권장.
5. **로그인은 commit 없음:** signup(1.3)과 달리 login/refresh는 읽기 전용 — `session.commit()` 호출 금지(불필요한 쓰기·롤백 픽스처 혼선 방지). 단, `client_db`로 signup→login E2E를 한 테스트에서 할 경우 signup의 commit은 SAVEPOINT에 갇혀 롤백됨(정상).
6. **이름 충돌(`InvalidTokenError`):** 우리 도메인 예외와 PyJWT 베이스 예외가 동명. `import jwt` 후 `jwt.InvalidTokenError`로 구분하거나, 도메인 예외를 `TokenError`로 명명하는 대안 고려(일관성 위해 `InvalidTokenError` 유지 + jwt는 모듈 접근 권장).
7. **verify_password 동작:** pwdlib `PasswordHash.verify(plain, hash)`가 불일치 시 `False`를 반환하는지 예외를 던지는지 확인 후 `bool`로 정규화(예외면 `try/except → False`).

### 현재 코드 상태 (UPDATE 대상 — 보존할 것)

Story 1.3이 첫 도메인 슬라이스를 완성함. 아래는 현재 실제 상태이며 **덮어쓰지 말고 확장**한다:

- **`app/core/security.py`** (UPDATE): 현재 `password_hasher = PasswordHash.recommended()` + `hash_password(plain)`만 존재. 모듈 docstring이 "verify_password·JWT는 1.4"로 명시 → **이 스토리가 그 함수들을 추가.** docstring도 갱신.
- **`app/core/config.py`** (그대로 — 소비만): `jwt_secret`, `access_token_expire_minutes=30`, `refresh_token_expire_days=14` **이미 선언됨**(주석: "1.4/1.5 소비"). → **새 설정 추가 불요**, import해서 사용만.
- **`app/schemas/auth.py`** (UPDATE): 현재 `SignupRequest`(email 정규화·display_name strip·Literal role)/`UserRead` 존재. `CamelModel` 베이스(`schemas/base.py`) 재사용. → Login/Token/Refresh 스키마 **append**.
- **`app/services/auth.py`** (UPDATE): 현재 `AuthService.signup`만. `__init__`이 `UserRepository(session)`를 `self.users`로 구성. → `login`/`refresh` 메서드 **append**(동일 `self.users` 재사용).
- **`app/repositories/users.py`** (UPDATE): `get_by_email`(정규화+`deleted_at IS NULL`)/`create` 존재. → `get_by_id` **추가**.
- **`app/routers/auth.py`** (UPDATE, append): `router = APIRouter(prefix="/api/v1/auth", tags=["auth"])` + `POST /signup` 존재. → `/login`·`/refresh` 라우트 추가. **prefix·tags·signup 보존.**
- **`app/core/exceptions.py`** (UPDATE): `AppError` 베이스 + `DuplicateEmailError`(409). → `InvalidCredentialsError`(401)·`InvalidTokenError`(401) 추가(동일 패턴).
- **`app/models/user.py`** (그대로): `User`(email/password_hash/display_name/user_role/is_active/is_seed) + `UserRole`(customer/pro/admin, values_callable 소문자). **`is_active`가 비활성 차단의 키.** 변경 없음.
- **`app/deps.py`** (그대로 — 건드리지 않음): "Story 1.5에서 get_current_user/require_role" 스텁 docstring. login/refresh는 미인증이라 불필요.
- **`tests/conftest.py`** (그대로 — 재사용): `client`(가짜 세션, health), `db_session`/`client_db`(실 DB + SAVEPOINT 롤백, NullPool 전용 엔진, `expire_on_commit=False`). → 로그인 테스트가 이 픽스처 **그대로 사용**, 추가 픽스처 불요 가능성 높음.
- **`pyproject.toml`** (검토만): `pyjwt>=2.10` **이미 설치·검증됨**. → **신규 의존성 0건.**
- **`alembic/`** (변경 없음): 신규 마이그레이션 **없음** — `users` 스키마 재사용(`is_active` 이미 존재).

### 아키텍처 준수 (반드시 따를 규약)

- **계층:** router(HTTP·검증·Depends) → service(비즈니스·토큰 발급/검증·권한) → repository(DB·`deleted_at IS NULL`). 역방향 호출 금지.
  [Source: architecture.md#Structure Patterns (line 284-288)]
- **JWT/인증:** HS256, payload `{user_id, user_role, exp}`(+ 의도적 `type`), access 15~30분 + refresh 7~30일, 시크릿=서버 환경변수 전용. Argon2(pwdlib) `verify_password`.
  [Source: architecture.md#Authentication & Security (line 184-195), AR11]
- **refresh 전략(MVP):** refresh로 access 재발급 엔드포인트. 회전·블랙리스트는 Post-MVP.
  [Source: architecture.md#Authentication & Security (line 194)]
- **로그아웃 의미:** Bearer 무상태 → 서버 토큰 무효화 없음, 로그아웃=클라이언트 토큰 폐기.
  [Source: architecture.md#Open Questions/Decisions (line 534-535)]
- **명명:** Python snake_case 함수, PascalCase 단수 클래스, 스키마 PascalCase+접미사(`LoginRequest`/`TokenResponse`/`RefreshResponse`). PK=`id`(UUIDv7).
  [Source: architecture.md#Naming Patterns (line 256-275)]
- **JSON 경계 camelCase:** `CamelModel`(alias_generator=to_camel, populate_by_name) — 요청 `accessToken` 등, 내부 속성 snake_case.
  [Source: architecture.md#Naming Patterns API (line 268-269), 1-3 story]
- **에러 envelope:** `{code, message, detail?}` + HTTP status. `code`=기계 판독, `message`=한국어. 401 인증 실패.
  [Source: architecture.md#API & Communication Patterns (line 203), 1-3 story]
- **API 패턴:** `/api/v1` 프리픽스, 태그=도메인(auth), OpenAPI operationId 안정화(라우트 함수명).
  [Source: architecture.md#API & Communication Patterns (line 197-202), AR9]
- **인가는 1.5:** `OAuth2PasswordBearer` + `Depends` 가드는 보호 라우트(1.5)용. 로그인 입력은 JSON(form-data 아님).
  [Source: architecture.md#Authentication & Security (line 191)]
- **검증/직렬화:** Pydantic v2, 서버 검증 신뢰(클라이언트 검증만 신뢰 금지, NFR3).
  [Source: architecture.md#Data Architecture (line 182)]

### 라이브러리/버전 (검증 완료 — 그대로 사용)

- FastAPI 0.136.x · SQLAlchemy 2.0.36(async+asyncpg) · Pydantic 2.10 / pydantic-settings 2.7+ · **PyJWT 2.10+** · **pwdlib[argon2] 0.2.1+** · uuid7 0.1.0+ · Python 3.12.8. 모두 `.venv` 설치·검증(2026-06-08, Supabase PG17.6 연결 OK).
- **신규 의존성: 없음.** PyJWT·pwdlib 모두 1.2/1.3에서 설치 완료. 새 버전 탐색/업그레이드 불필요.
- **uv 실행(1.2/1.3 계승):** 이 PC는 uv managed standalone 3.12 실행 불가 → `[tool.uv] python-preference="only-system"` 유지, `uv sync`/`uv run pytest`/`uv run ruff check .` 사용.
  [Source: 1-3 story 라이브러리 섹션, backend-env-setup 메모, architecture.md#Coherence Validation]

### 파일 구조 (생성/수정 위치)

```
apps/api/
  app/
    core/
      security.py        (UPDATE) verify_password, create_access_token, create_refresh_token, decode_token
      exceptions.py      (UPDATE) InvalidCredentialsError(401), InvalidTokenError(401)
      config.py          (그대로) jwt_secret/expire 필드 이미 존재 — 소비만
    schemas/
      auth.py            (UPDATE) LoginRequest, TokenResponse, RefreshRequest, RefreshResponse
    repositories/
      users.py           (UPDATE) get_by_id 추가
    services/
      auth.py            (UPDATE) AuthService.login, AuthService.refresh
    routers/
      auth.py            (UPDATE) POST /login, POST /refresh (signup 보존, /logout 없음)
    deps.py              (그대로 — 1.5)
    models/user.py       (그대로 — is_active 재사용)
  tests/
    test_auth_login.py   (NEW) 로그인/refresh/비활성/type혼동/만료/위조/발급후비활성화
    conftest.py          (그대로 — db_session/client_db 재사용)
  # alembic: 신규 마이그레이션 없음
  # pyproject.toml: 신규 의존성 없음
```
[Source: architecture.md#Complete Project Directory Structure (line 407-425), 1-3 story 파일 구조]

### 테스트 표준

- pytest + `pytest-asyncio`(`asyncio_mode=auto`) + httpx `AsyncClient`(`ASGITransport`) + `dependency_overrides`. **도메인 테스트는 실 DB + SAVEPOINT 롤백**(`db_session`/`client_db` 재사용 — architecture line 289, fake repo 금지: 실제 해시 대조·is_active 차단을 DB로 검증).
- 사용자 시드는 savepoint 내부에서: `client_db`로 `/signup`→`/login` E2E(권장) 또는 `db_session`에 `User(password_hash=hash_password(...))` 직접 insert. 둘 다 롤백 격리.
- 핵심 경로 우선(로그인 성공/실패 3종/refresh 성공/type혼동/만료/발급후비활성화). CI(`pytest`)는 Story 1.8에서 GitHub Actions + `DATABASE_URL` 시크릿 연결.
  [Source: architecture.md#Structure Patterns (line 289), 1-3 story 테스트 표준]

### Project Structure Notes

- 정합: login/refresh가 `auth` 라우터·`AuthService`·`UserRepository`에 사는 것은 1.3 signup과 동일 배치(중복 방지) — architecture 태그 규약(auth) + epic AC 경로(`/api/v1/auth/login|refresh`) 정합.
- 변이: 데이터는 `user`지만 행위는 `auth`(로그인은 인증 행위). 1.3에서 확립된 의도된 배치 계승.
- `apps/api`는 Turborepo 그래프 외부(uv/uvicorn 별도 파이프라인).

### 이전 스토리(1.3) 학습 / 정합

- **1.3 코드 리뷰 defer 중 1.4 무관 확인:** "소프트삭제 이메일 재가입 불가(HIGH)"·"과도한 IntegrityError 매핑"·"CORS wildcard"·"enum drop checkfirst"는 모두 삭제/가입/CORS/마이그레이션 경로 — 로그인/refresh와 무관. 단, refresh의 `get_by_id`도 `deleted_at IS NULL`을 지켜 삭제 계정이 토큰으로 부활하지 못하게 한다(defer 항목과 동일한 소프트삭제 일관성 원칙).
  [Source: deferred-work.md, 1-3 story Review Findings]
- **camelCase 직렬화 경계 재확인:** `TokenResponse`가 `accessToken`/`refreshToken`/`tokenType`로 나가도록 `CamelModel` 상속. 1.3 `UserRead`와 동일 패턴(클라이언트가 camel 소비).
- **enum 값 소문자:** `user_role.value`는 `"customer"`/`"pro"`/`"admin"`(1.3 values_callable). JWT에 `user_role.value` 문자열로 넣어 1.5가 동일 문자열로 읽도록.

### References

- [Source: epics.md#Story 1.4: 로그인/로그아웃 & 세션 갱신 (JWT) (line 251-273)] — 4개 AC 원본(BDD), HS256 payload, access/refresh 수명, 무상태 로그아웃
- [Source: epics.md#Story 1.5 (line 275-293)] — get_current_user/require_role 범위(이 스토리에서 제외 확인)
- [Source: epics.md#Story 1.7 (line 315-337)] — Orval/api-client/인터셉터/토큰 저장(1.7 범위, 이 스토리는 백엔드 계약까지)
- [Source: architecture.md#Authentication & Security (line 184-195)] — Bearer 통일, JWT HS256 payload, access/refresh 수명, refresh 전략 MVP, Argon2
- [Source: architecture.md#API & Communication Patterns (line 197-207)] — `/api/v1`, auth 태그, 에러 envelope, operationId, Orval
- [Source: architecture.md#Open Questions/Decisions (line 534-535)] — 로그아웃=클라이언트 토큰 폐기(무상태)
- [Source: architecture.md#Naming Patterns (line 256-275)] — 명명·camelCase 경계
- [Source: AR9, AR10, AR11, AR12 (epics.md#Additional Requirements line 85-88)] — Orval/operationId, Bearer/인터셉터, JWT/Argon2, 에러 envelope
- [Source: 1-3-signup-seed-admin.md] — 계층/직렬화/롤백 테스트 선례, security.py·config.py·schemas/services/repositories/routers/exceptions 현재 상태, CamelModel, is_active/is_seed, uv/PyJWT 함정
- [Source: deferred-work.md] — 1.3 리뷰 이월(1.4 무관 확인 + 소프트삭제 일관성 원칙)
- [Source: backend-env-setup 메모] — uv only-system, .env(JWT_SECRET 채워짐·검증) 사실

## ⚡ 수동 설정 체크포인트 (AR23 — dev-story 진입 전 KTH 확인)

- **신규 외부 설정 없음.** 로그인/refresh는 기존 `apps/api/.env`의 `JWT_SECRET`(1.2에서 설정·검증됨)과 `users` 테이블(1.3)만 사용한다. Supabase/Railway/Expo 추가 작업 불요.
- **검증용 권장(선택):** 로그인 E2E를 실 계정으로 확인하려면 1.3 시드 관리자(`uv run python -m app.seed`, `SEED_ADMIN_*` 설정 시) 또는 `/signup`으로 만든 고객/고수 계정으로 `/login`을 호출해볼 수 있다. 테스트(test_auth_login.py)는 savepoint 내 자체 시드로 동작하므로 별도 계정 없이 통과한다.
- **확인 요청:** 위 "신규 설정 없음"이 맞는지(=`.env`의 `JWT_SECRET`이 여전히 유효한지) KTH가 확인하면 dev-story 진입. 시크릿 회전이 있었다면 `.env` 갱신 필요.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code, BMad dev-story 워크플로우)

### Debug Log References

- **라이브러리 동작 사전 검증(런타임 디버깅 전 적용, 함정 #1/#7):** `uv run python`으로 확인 — PyJWT 2.13: `ExpiredSignatureError`·`DecodeError`·`InvalidSignatureError` 모두 `jwt.InvalidTokenError` 서브클래스(→ 단일 except로 포착). pwdlib `verify`: 틀린 비번 → `False`, 손상된 해시 → `UnknownHashError` 예외(→ `verify_password`에서 `try/except`로 `False` 정규화).
- **환경 확인(수동 설정 체크포인트):** `.env`의 `JWT_SECRET` 유효(64자), 설정 로드·Supabase DB 연결 정상 → 신규 외부 설정 없음.
- `uv run ruff check .` 통과, `uv run pytest -q` → 35 passed(기존 22 + 신규 13, 회귀 0).

### Completion Notes List

- **Task 1 — security.py(UPDATE):** `verify_password`(예외→False 정규화), `create_access_token`(payload `{user_id, user_role, type:"access", exp}`), `create_refresh_token`(`{user_id, type:"refresh", exp}` — role 미포함), `decode_token`(HS256 검증, `jwt.InvalidTokenError` 전파) 추가. exp는 timezone-aware UTC. **라이브러리 계층 유지** — 도메인 예외 미import.
- **Task 2 — schemas/auth.py(UPDATE):** `LoginRequest`(email strip+lower 정규화), `TokenResponse`(access+refresh), `RefreshRequest`, `RefreshResponse`(access만 — 회전 없음 명시) append. 모두 `CamelModel` 상속(camel 경계).
- **Task 3 — exceptions.py(UPDATE):** `InvalidCredentialsError`(401, anti-enumeration 단일 사용), `InvalidTokenError`(401) 추가 — `DuplicateEmailError` 패턴 복제.
- **Task 4 — repositories/users.py(UPDATE):** `get_by_id`(`deleted_at IS NULL`) 추가, `get_by_email`/`create` 보존.
- **Task 5 — services/auth.py(UPDATE):** `login`(미존재·비번불일치·비활성 모두 동일 401, 읽기 전용 commit 없음), `refresh`(서명·만료·`type=="refresh"` 가드 → 재조회로 현재 `is_active`/role 반영) append. **이름 충돌 해소:** `import jwt`로 `jwt.InvalidTokenError`(except) vs 도메인 `InvalidTokenError`(raise) 구분.
- **Task 6 — routers/auth.py(UPDATE):** `POST /login`(200), `POST /refresh`(200) append. signup·router 인스턴스 보존. `/logout` 미생성(AC4 무상태).
- **Task 7 — tests/test_auth_login.py(NEW):** 13개 테스트(로그인 성공/payload/대소문자 3종, 실패 3종 + **anti-enumeration 세 응답 동일성** 1종, refresh 성공/type혼동/만료/위조/발급후비활성화 5종, verify_password 단위 1종). 실 DB + SAVEPOINT 롤백 픽스처 재사용. `asyncio_mode=auto`라 모듈 asyncio 마커 제거(동기 단위 테스트 경고 해소).
- **AC 충족:** AC1(✅ login 200+토큰+payload), AC2(✅ 401 단일 일반 envelope·세 응답 동일), AC3(✅ refresh 재조회·회전없음·각종 거부), AC4(✅ `/logout` 미생성, 무상태).
- **신규 의존성·마이그레이션 0건.** `users`(1.3) 재사용.

### File List

- `apps/api/app/core/security.py` (수정) — verify_password, create_access_token, create_refresh_token, decode_token
- `apps/api/app/core/exceptions.py` (수정) — InvalidCredentialsError(401), InvalidTokenError(401)
- `apps/api/app/schemas/auth.py` (수정) — LoginRequest, TokenResponse, RefreshRequest, RefreshResponse
- `apps/api/app/repositories/users.py` (수정) — get_by_id
- `apps/api/app/services/auth.py` (수정) — AuthService.login, AuthService.refresh
- `apps/api/app/routers/auth.py` (수정) — POST /login, POST /refresh
- `apps/api/tests/test_auth_login.py` (신규) — 로그인/refresh 테스트 11종

### Change Log

| 날짜 | 변경 | 비고 |
| --- | --- | --- |
| 2026-06-08 | Story 1.4 구현 — JWT 로그인/세션갱신(login·refresh), verify_password, 인증 예외 2종, get_by_id, 테스트 13종 | 35 tests pass, ruff clean, 신규 의존성/마이그레이션 0 |

## Review Findings

**코드 리뷰 (2026-06-08) — 3중 적대적 리뷰(Blind Hunter / Edge Case Hunter / Acceptance Auditor).** Acceptance Auditor: AC1~AC4 및 핵심 제약 전부 **충족** 확인. 아래는 잔여 품질/보안 항목. (오탐 3건 제외: signup `expire_on_commit=False` 반증 / `CamelModel.from_attributes` 반증 / 무회전·무로그아웃은 AC4 의도된 설계.)

### Patch

- [x] [Review][Patch] 로그인 타이밍 사이드채널 → 사용자 열거 가능성(NFR3 잔여 리스크) [services/auth.py:83] — (decision-needed → 사용자가 "지금 패치" 선택, 2026-06-08) `if user is None or not verify_password(...)`가 단락 평가로 **미존재 이메일일 때 Argon2 `verify_password`를 호출하지 않는다.** 미존재 이메일(즉시 응답) vs 존재+비번오류(Argon2 수십 ms) 간 응답 시간 차로 이메일 존재를 원격 측정 추론 가능. envelope는 동일하므로 AC2는 충족이나 NFR3 anti-enumeration 정신에는 잔여 리스크. ⚠️ `test_login_failures_are_indistinguishable`는 JSON 본문 동일성만 검증 → 타이밍 차를 못 잡음. 수정안: `user is None`일 때 고정 더미 Argon2 해시로 `verify_password`를 호출해 시간 균등화.
- [x] [Review][Patch] refresh 토큰 payload 파싱 미가드 → 500(401 아님) [services/auth.py:108] — `UUID(payload["user_id"])`가 `try/except jwt.InvalidTokenError` 블록 밖. 서명은 유효하나 `user_id` 누락(`KeyError`)·비-UUID(`ValueError`)·비문자열(`TypeError`) payload는 잡히지 않아 전역 핸들러의 500으로 떨어진다. security.py 모듈 docstring이 명시한 "모든 토큰 실패 → 단일 도메인 401" 계약 위반. (시크릿 보유자만 트리거 가능 → 원격 악용 불가, 방어적 견고성 갭. 코드가 스펙 그대로라 스펙 위반 아님.) 수정안: 추출·파싱을 try로 감싸 `KeyError/ValueError/TypeError` → `InvalidTokenError`.
- [x] [Review][Patch] LoginRequest.password max_length 누락 → Argon2 DoS 비대칭 [schemas/auth.py:66] — `SignupRequest.password`는 `max_length=128`로 DoS 상한(명시 주석)을 두는데 `LoginRequest.password`는 무제한. 유효 이메일 + 초장문 password를 공개 `/login`에 보내면 Argon2 자원 소진. **원격 트리거 가능**, 422 format 거부라 계정 존재 노출 없음. 수정안: `password: str = Field(max_length=128)`.
- [x] [Review][Patch] decode_token이 exp 클레임 필수화 안 함 [security.py:91] — PyJWT 기본은 `exp` 부재를 허용 → exp 없는 토큰은 영구 유효. 발급자는 항상 exp를 넣으므로 시크릿 보유자만 트리거 가능(방어적). 수정안: `jwt.decode(..., options={"require": ["exp"]})`.
