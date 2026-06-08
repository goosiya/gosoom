---
baseline_commit: NO_VCS
---
# Story 1.8: CI 파이프라인 + 워킹 스켈레톤 배포

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 개발팀,
I want CI(테스트·린트·빌드)와 워킹 스켈레톤의 배포 파이프라인을 갖추기를,
So that 가입/로그인이 실제 배포 환경에서 동작함을 검증하고 데모 안정성(NFR8)을 확보할 수 있다.

이 스토리는 **Epic 1의 마지막 스토리이자 "기반→배포 골격" 완결**이다. 1.1~1.7이 만든 코드(모노레포 4앱 + 백엔드 auth/users/categories + user-web 인증 UI)를 **자동 검증(CI)** 하고 **실 배포 환경(Railway + Supabase)** 에서 가입→로그인이 동작함을 증명한다. 이후 Epic 2~6의 모든 기능이 이 CI 게이트와 배포 파이프라인 위에서 검증·전달된다.

> ⚠️ **이 스토리의 본질(반드시 인지) — dev 코드 산출물 vs KTH 콘솔 작업의 경계:**
> 1.8은 **코드로 작성 가능한 부분**과 **외부 콘솔(Railway/Supabase/GitHub)에서만 가능한 수동 작업**이 섞여 있다. dev가 직접 검증(Definition of Done)할 수 있는 산출물은 **`.github/workflows/ci.yml` + Dockerfile 마무리 + 배포 설정 파일 + 배포 런북**의 *정확성*이다. **"배포 URL에서 가입→로그인이 동작한다"(AC2)는 dev 단독으로 검증 불가** — KTH의 Railway/Supabase 콘솔 배선이 선행돼야 하는 **KTH+dev 공동 검증**이다. 따라서 dev는 (a) 파이프라인·설정 파일을 정확히 작성하고, (b) KTH 체크포인트(맨 아래)를 먼저 안내한 뒤, (c) KTH 배선 완료 후 함께 배포 동작을 확인한다.

> 🔴 **CRITICAL — 현재 git 저장소가 아니다(NO_VCS):** 이 워크스페이스는 아직 git 저장소가 아니다(이전 스토리들도 `baseline_commit: NO_VCS`). GitHub Actions와 Railway GitHub 연동은 **GitHub 원격 저장소가 선결 조건**이다. 따라서 **`git init` → GitHub 레포 생성 → 최초 push**가 이 스토리에서 검증 가능한 *모든 것*의 게이트다. `ci.yml`을 작성해도 GitHub에 push되기 전엔 실행되지 않는다(KTH 체크포인트 #1).

> 🔴 **CRITICAL — 배포된 API에는 스키마가 없다(가장 자주 누락되는 항목):** `apps/api/Dockerfile`의 `CMD`는 `uvicorn`만 기동한다 — **어디서도 `alembic upgrade head`가 실행되지 않는다.** 마이그레이션 메커니즘이 없으면 배포된 API가 빈 Supabase DB를 바라봐 **가입/로그인이 실패하고 AC2가 깨진다.** 배포 시 마이그레이션 실행(Railway **release/pre-deploy command** = `alembic upgrade head`)을 반드시 설계한다(결정 #3). 시드(관리자/카테고리)는 별도 1회 수동 실행.

## Acceptance Criteria

**AC1 — GitHub Actions CI: PR마다 api(pytest+ruff) + JS(lint/typecheck/build) 검증**
**Given** `.github/workflows/ci.yml` 워크플로우가 구성되고 코드가 GitHub에 push되었을 때
**When** PR이 생성되거나 main에 push되면
**Then** 두 잡이 실행되어 ① **api 잡** — Postgres 서비스 컨테이너에 `alembic upgrade head` 후 `uv run ruff check` + `uv run pytest`(실 DB 통합 테스트 포함)가 통과하고, ② **JS 잡** — `pnpm install --frozen-lockfile` 후 `pnpm lint`/`pnpm typecheck`/`pnpm build`(turbo 워크스페이스 전역: user-web·admin-web·mobile·packages)가 통과한다(AR20). 어느 게이트라도 실패하면 워크플로우가 적색 처리된다.

**AC2 — main 병합 시 Railway 자동 배포 + 배포 URL에서 가입→로그인 E2E 동작**
**Given** Railway에 `api`(FastAPI/Dockerfile) · `user-web`(Next 빌드) 서비스와 Supabase PostgreSQL(Phase 1) 연결이 구성되고, **api 배포 시 `alembic upgrade head`가 실행(release command)** 되도록 설정될 때
**When** main 브랜치에 병합되면
**Then** GitHub 연동으로 두 서비스가 자동 배포되고, **배포된 user-web URL에서 회원가입→로그인→인증 후 홈(displayName 표시)이 E2E로 동작**한다(AR19, SM4 데모 무중단 기반). *(이 AC는 KTH의 Railway/Supabase 콘솔 배선 완료 후 KTH+dev가 공동 검증한다 — dev 단독 검증 불가, 본질 콜아웃 참조.)*

**AC3 — 시크릿은 Railway 환경변수로만 주입, 클라이언트엔 공개 변수만**
**Given** 시크릿(`JWT_SECRET`, `DATABASE_URL`)과 클라이언트 설정(`NEXT_PUBLIC_API_URL`)이 필요할 때
**When** Railway 환경변수로 주입하면
**Then** 시크릿은 **클라이언트 번들·로그·코드·레포에 노출되지 않고**(`.env`류는 `.gitignore`로 추적 제외), user-web에는 **빌드타임 공개 변수 `NEXT_PUBLIC_API_URL`(=배포된 api의 공개 URL)만** 주입된다(NFR3, AR18). `NEXT_PUBLIC_*`는 Next 빌드 시점에 인라인되므로 **api 배포 → api 도메인 확보 → user-web에 주입 → user-web 빌드** 순서를 따른다.

**AC4 — ⚡수동 설정 체크포인트(AR23)를 dev-story 진입 전 선안내**
**Given** AR23 수동 설정 체크포인트 원칙에 따라
**When** 이 스토리(및 배포) 구현에 진입하기 전
**Then** KTH가 직접 할 외부 설정 — **git init·GitHub 레포 생성·push**, Supabase `DATABASE_URL` 확인(배포 대상 확정), `JWT_SECRET` 생성, Railway 가입·GitHub 연동·서비스(api/user-web) 생성·환경변수 등록·release command 설정 — 을 **구체적 단계와 함께 먼저 안내**한다(맨 아래 체크포인트 섹션).

## Tasks / Subtasks

- [x] **Task 1 — `.github/workflows/ci.yml` 작성: api 잡 + JS 잡** (AC: 1)
  - [x] **`.github/workflows/ci.yml`** (NEW): 트리거 `on: { pull_request: {}, push: { branches: [main] } }`. 동일 ref 중복 실행 취소(`concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }`). 두 잡 병렬.
  - [x] **api 잡** (`runs-on: ubuntu-latest`, `defaults.run.working-directory: apps/api`):
    - **Postgres 서비스 컨테이너:** `services.postgres` = `postgres:17`(Supabase PG17 정합) + `env`(POSTGRES_USER/PASSWORD/DB) + `ports: 5432:5432` + `options` 헬스체크(`pg_isready`). 잡 레벨 `env`: `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/gosoom_test`, `JWT_SECRET=ci-test-secret-not-for-prod`. (`config.py`가 `database_url`·`jwt_secret`을 **필수**로 요구 — 둘 다 없으면 `import app.main`이 ValidationError로 크래시, 함정 #1.)
    - 스텝: `actions/checkout` → `actions/setup-python@v5`(python-version 3.12) → `astral-sh/setup-uv@v6` → `uv sync`(dev 그룹 설치: pytest/pytest-asyncio/httpx/ruff) → `uv run alembic upgrade head`(Postgres 서비스에 스키마 생성 — 통합 테스트 `db_session`/`client_db`가 실 DB·실 제약을 사용, conftest 참조) → `uv run ruff check .` → `uv run pytest`.
    - **⚠️ `python-preference = "only-system"`(pyproject 라인 36):** uv가 standalone Python을 다운로드하지 않으므로 `setup-python@v5`로 **시스템 3.12를 먼저 공급**해야 `uv sync`가 그 인터프리터를 잡는다(공급 안 하면 "no system python" 실패, 함정 #5).
  - [x] **JS 잡** (`runs-on: ubuntu-latest`):
    - 스텝: `actions/checkout` → `pnpm/action-setup`(version 11.5.2, packageManager 정합) → `actions/setup-node@v4`(node-version 20, `cache: pnpm`) → `pnpm install --frozen-lockfile` → `pnpm lint` → `pnpm typecheck` → `pnpm build` → **`pnpm --filter @gosoom/api-client test`**(Vitest 15+ 인터셉터/토큰스토어 단위 테스트 — KTH 확정 "CI 포함"). esbuild(Vitest 네이티브 의존) 빌드 승인은 `pnpm-workspace.yaml` `onlyBuiltDependencies`/`allowBuilds`에 이미 등재됨(1.7) → CI `--frozen-lockfile` install로 재현.
    - **생성물(`packages/api-client/src/generated/`)은 커밋되어 있음**(`.gitignore` 라인 41 주석 "생성물은 추적" 확인) → CI는 **orval 재생성 없이** 커밋된 훅으로 빌드한다(openapi.json은 `.gitignore`로 제외 — 재생성 아티팩트, 1.7 결정 #1). `pnpm build`는 `NEXT_PUBLIC_API_URL` 미설정 시 `resolveBaseUrl()` 폴백(`http://localhost:8000/api/v1`)으로 빌드 성공(검증 목적엔 충분, 함정 #4) — CI 빌드에 실 URL 불요.
  - [x] **로컬 검증 한계 명시:** dev는 git 저장소가 아니므로 **GitHub Actions를 실제로 돌릴 수 없다.** 검증은 (a) YAML 문법/구조 정합, (b) 각 명령이 로컬에서 동작함(`apps/api`에서 `uv run pytest`·`uv run ruff check`, 루트에서 `pnpm lint`/`typecheck`/`build` — 1.7에서 이미 그린)으로 한다. 실제 CI 그린은 KTH push 후 공동 확인.

- [x] **Task 2 — api Dockerfile 마무리(재현성 + 마이그레이션)** (AC: 2, 3) — **🔴 배포 정확성 핵심**
  - [x] **`apps/api/Dockerfile`** (UPDATE — 현재 "최종 확정은 Story 1.8" 주석): `uv.lock`을 COPY에 포함해 **재현 가능한 설치**로 전환. 현재 `COPY pyproject.toml ./` → `COPY pyproject.toml uv.lock ./`, `RUN uv sync --no-dev --no-install-project` → `RUN uv sync --frozen --no-dev --no-install-project`, 두 번째 `uv sync --no-dev` → `uv sync --frozen --no-dev`. (`apps/api/uv.lock` 존재 확인됨.) **빌드 컨텍스트 = `apps/api`** 전제(Railway 루트 디렉터리 = `apps/api`) — `COPY . .`가 apps/api 트리를 복사.
  - [x] **마이그레이션은 CMD에 넣지 않는다(결정 #3):** Dockerfile `CMD`는 `uvicorn` 기동만 유지. `alembic upgrade head`는 **Railway release/pre-deploy command**로 분리한다(여러 레플리카가 동시에 마이그레이션하는 것을 피하고, 배포 1회만 실행). KTH 체크포인트에 release command 설정 안내.
    - 대안(런북에 기록): release command 미지원/미사용 시 `entrypoint.sh`(`alembic upgrade head && exec uvicorn ...`)로 대체 — 단 단일 인스턴스 가정. MVP는 release command 권장.
  - [x] **`.dockerignore`** (NEW, `apps/api/.dockerignore`): `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.env`, `tests/` 제외(이미지 슬림화·시크릿 유출 방지). `.env`는 절대 이미지에 포함 금지(시크릿은 Railway env로만, AC3).
  - [x] **헬스체크 경로:** `GET /api/v1/health`(Story 1.2 구현, DB 연결 포함 200/503)를 Railway 헬스체크 경로로 사용하도록 런북·설정에 기록.

- [x] **Task 3 — user-web Railway 배포 설정(모노레포 Next 빌드)** (AC: 2, 3)
  - [x] **결정(아래 #4) — 1차 경로 = Railway 빌더(Nixpacks/Railpack) + 루트=레포 루트 + pnpm 필터 명령:** user-web은 pnpm 워크스페이스 일부라 **빌드 컨텍스트가 레포 루트**여야 공유 패키지(`@gosoom/api-client`, `@gosoom/ui`)가 해소된다. Railway user-web 서비스 설정(런북에 명시): root directory = **레포 루트**, install = `pnpm install --frozen-lockfile`, build = `pnpm --filter user-web build`, start = `pnpm --filter user-web start`. **빌드타임 env `NEXT_PUBLIC_API_URL` = 배포된 api 공개 URL**(AC3, 순서: api 먼저 배포→도메인 확보→주입→user-web 빌드).
  - [x] **KTH 확정 — `railway.json` 커밋하지 않음, 런북 문서만:** dev는 **배포 런북(`docs/deploy.md`)에 위 설정값을 문서화**하고 Railway 콘솔 설정으로 적용한다(설정 파일을 레포에 커밋하지 않음). 과설계 금지: user-web 전용 Dockerfile은 1차 경로(Railway 빌더)가 막힐 때만(모노레포 Next standalone Dockerfile은 dev가 테스트 불가 → 우선 Railway 빌더 경로).
  - [x] **admin-web·mobile 배포는 범위 밖**(admin=Epic 6, mobile=Epic 5). 1.8은 **api + user-web만** 배포(AC2 정합).

- [x] **Task 4 — 배포 런북 + 환경변수 문서화** (AC: 2, 3, 4)
  - [x] **`docs/deploy.md`**(NEW, 또는 README 섹션): Phase 1 배포 절차를 **순서대로** 기록 — ① git init·GitHub push, ② Supabase `DATABASE_URL` 확인(asyncpg 형식), ③ `JWT_SECRET` 생성, ④ Railway: GitHub 연동 → api 서비스(루트=`apps/api`, Docker, env: `DATABASE_URL`·`JWT_SECRET`·`CORS_ORIGINS`, **release command=`alembic upgrade head`**, 헬스체크=`/api/v1/health`) → api 도메인 확보 → user-web 서비스(루트=레포 루트, build/start=pnpm 필터, env: `NEXT_PUBLIC_API_URL`=api 도메인) → user-web의 도메인을 api `CORS_ORIGINS`에 추가·재배포, ⑤ 시드 1회 실행(관리자/카테고리), ⑥ 배포 URL 가입→로그인 확인.
  - [x] **시드 전략 기록:** 마이그레이션은 매 배포 release command로 멱등 실행되지만, **시드(`python -m app.seed`)는 1회만** — Railway one-off 명령 또는 로컬에서 배포 DB 대상 실행으로 안내(관리자/카테고리 없으면 Epic 2/3 빈 의존성). `SEED_ADMIN_PASSWORD`는 시드 시에만 필요한 시크릿(`.env.example` 라인 17-21).
  - [x] **CORS 순환 의존 주의:** api의 `CORS_ORIGINS`는 배포된 user-web 오리진을 포함해야 브라우저 가입/로그인이 동작(1.7 함정 #8과 동일). user-web 도메인은 user-web 배포 후 확정되므로, api env를 그때 갱신·재배포(런북 ④에 명시).

- [x] **Task 5 — `.gitignore`/생성물 정합 확인(회귀 0)** (AC: 1, 3)
  - [x] **`.gitignore`** (검토 — 변경 최소): `openapi.json` 무시 유지(라인 42), `generated/`는 추적 유지(무시 추가 금지 — CI 빌드가 의존). `.env`/`apps/api/.env`/`.env.local` 무시 유지(시크릿, AC3). **`.github/`는 무시하지 않는다**(워크플로우는 추적 대상).
  - [x] 시크릿이 레포에 들어가지 않음을 확인: `apps/api/.env`·`apps/user-web/.env.local`은 `.gitignore` 대상(이미 그러함), example 파일만 커밋.

- [x] **Task 6 — 검증: 로컬 게이트 그린 + 런북 정합** (AC: 전체)
  - [x] **로컬 재현(CI 명령과 동일):** `apps/api`에서 `uv run ruff check .` + `uv run pytest`(KTH의 로컬 DB로 — 1.7까지 그린), 루트에서 `pnpm lint`/`pnpm typecheck`/`pnpm build`(1.7에서 6/6·빌드 그린) 통과 확인. ci.yml의 명령이 이와 1:1 대응하는지 대조.
  - [x] **YAML 정합:** `ci.yml`이 유효한 워크플로우 문법인지(들여쓰기·키) 검토. (act/실 실행은 불가 — push 후 KTH 공동 확인.)
  - [x] **회귀 0:** 이 스토리는 **CI/배포 설정 추가** 중심 — 1.1~1.7 코드(api·프론트) 변경 없음. Dockerfile/.gitignore 외 앱 코드 미변경. 기존 pytest/JS 게이트 그린 유지.

## Dev Notes

### 🎯 스코프 경계 (범위 침범 금지)

- ✅ **이 스토리:** `.github/workflows/ci.yml`(api pytest+ruff / JS lint+typecheck+build), api `Dockerfile` 마무리(uv.lock·재현성)+`.dockerignore`, **배포 시 마이그레이션 메커니즘(Railway release command=`alembic upgrade head`)**, user-web Railway 빌드 설정 문서화, 배포 런북(`docs/deploy.md`), `.gitignore` 정합 확인, AR23 KTH 체크포인트 선안내.
- ❌ **앱 기능 코드 변경 금지:** api 라우터/서비스/모델, user-web 화면/훅, api-client 등 **기능 코드는 손대지 않는다**(1.1~1.7 동결). 1.8은 인프라/파이프라인/설정만.
- ❌ **admin-web·mobile 배포 금지:** admin=Epic 6, mobile(Expo Go/EAS)=Epic 5. 1.8 배포는 **api + user-web만**. (단, JS CI 게이트는 워크스페이스 전역이라 admin-web·mobile의 lint/typecheck도 *검증*은 한다 — 배포만 제외.)
- ❌ **Phase 2 이관(Railway PG) 금지(Post-MVP, AR21):** 1.8은 Phase 1(Supabase 외부 PG)만. 이관 절차는 별도(에픽 Overview "Deferred").
- ❌ **모니터링·자동계측 고도화 금지(Post-MVP, R4):** 구조적 로깅(기본)은 이미 1.2. APM/대시보드 등은 범위 밖.
- ❌ **풀 E2E(Playwright) 자동화 금지(과설계):** 1.7에서 thin slice로 결정. 1.8 CI는 pytest(api 실DB 통합) + JS 빌드 게이트까지. 배포 E2E는 KTH+dev 수동 확인. *(KTH가 Playwright E2E를 원하면 dev-story 전 알려주세요 — 범위 확대.)*
- ❌ **refresh 회전·시크릿 매니저·OIDC 등 보안 고도화 금지(Post-MVP):** MVP는 Railway env var로 시크릿 주입까지.

### ⚖️ 결정 사항 (Dev가 그대로 채택)

- **🔑 #1 — git/GitHub가 모든 검증의 선결 조건(NO_VCS):** 현재 워크스페이스는 git 저장소가 아니다. `ci.yml`·Railway 연동 전부 **GitHub 원격이 있어야** 동작. 따라서 **`git init`+레포 생성+push는 KTH 체크포인트 #1**이고, dev의 코드 산출물(ci.yml 등)은 push 전까지 "작성됐으나 미실행" 상태다. dev는 이를 정직하게 보고하고, 실제 CI 그린은 push 후 공동 확인한다.
- **🔑 #2 — pytest는 실 Postgres 필요 → CI에 서비스 컨테이너 + `alembic upgrade head`:** `tests/conftest.py`의 `db_session`/`client_db`가 `settings.database_url`로 **실 DB에 연결**하고 트랜잭션 롤백으로 격리한다(이메일 unique 등 DB 제약을 실제로 검증 — fake repo 금지). 따라서 CI api 잡은 ① Postgres 서비스 컨테이너, ② `DATABASE_URL`/`JWT_SECRET` env(둘 다 `config.py` 필수), ③ 테스트 전 `alembic upgrade head`로 스키마 생성이 모두 필요하다. `pg_isready` 헬스체크로 컨테이너 준비 대기.
- **🔑 #3 — 배포 마이그레이션은 release command, CMD엔 넣지 않음:** Dockerfile `CMD`는 `uvicorn`만. `alembic upgrade head`를 CMD/entrypoint에 넣으면 레플리카마다 중복 실행. Railway **release/pre-deploy command**(배포당 1회)로 분리한다. 이게 없으면 **배포된 API가 빈 스키마 → 가입/로그인 500 → AC2 실패**(가장 흔한 누락). 시드는 마이그레이션과 별개로 1회 수동.
- **🔑 #4 — user-web는 모노레포 루트 컨텍스트로 빌드:** Next user-web이 `@gosoom/api-client`·`@gosoom/ui`(workspace:*)를 의존 → **빌드 컨텍스트=레포 루트**여야 해소. Railway 빌더(Nixpacks/Railpack) + 루트=레포 루트 + `pnpm --filter user-web build/start`가 1차 경로. `NEXT_PUBLIC_API_URL`은 **빌드타임 인라인**이라 api 도메인 확정 후 주입→빌드(순서 의존). 전용 Dockerfile은 1차 경로 실패 시에만(dev 테스트 불가하므로 후순위).
- **🔑 #5 — CI 산출물의 dev 검증 한계:** dev는 GitHub Actions를 로컬에서 실행할 수 없다(NO_VCS + 클라우드 러너). dev의 DoD는 **(a) ci.yml 구조/문법 정합, (b) CI가 부르는 명령이 로컬에서 그린**(1.7까지 검증됨)이다. "CI가 GitHub에서 그린"·"배포 URL 동작"은 KTH 배선 후 공동 검증 — 스토리 완료 보고에 이 경계를 명시한다(거짓 완료 금지).
- **#6 — Postgres 버전 17로 정합:** Supabase가 PG17(아키텍처/Addendum). CI 서비스 컨테이너도 `postgres:17`로 맞춰 버전 차로 인한 미세 차이를 줄인다(UUIDv7 앱측 생성이라 확장 의존은 없음 — AR4).
- **#7 — JS CI 게이트는 워크스페이스 전역:** 루트 `pnpm lint`/`typecheck`/`build`(turbo)가 user-web·admin-web·mobile·packages 전체에 팬아웃. 1.7 시점 `pnpm typecheck`(6/6)·`build`·`lint` 그린이므로 전역 게이트도 그린 전제. 신규 적색 시 원인은 스캐폴드 변경 — 최소 수정(앱 기능 변경 아님).

### ⚠️ 알려진 함정 (런타임/CI 디버깅 전 미리 적용 — 고가치)

1. **🔴 `config.py` 필수 env 누락 → import 크래시:** `database_url`·`jwt_secret`은 기본값 없는 필수 필드(`config.py` 라인 20·23). CI api 잡은 `import app.main`(pytest collection·alembic env) 시점에 이미 둘이 필요 → 잡 레벨 `env`에 **둘 다 설정**. 없으면 pydantic ValidationError로 잡 전체 실패.
2. **🔴 배포 DB 스키마 부재:** Dockerfile CMD는 uvicorn만 → 마이그레이션 안 됨. release command `alembic upgrade head` 누락 시 배포 가입/로그인 500. (결정 #3.)
3. **`python-preference="only-system"`(pyproject 라인 36) + CI:** uv가 managed Python을 다운로드하지 않음 → CI에서 `setup-python@v5`(3.12)로 **시스템 인터프리터를 먼저 공급**해야 `uv sync` 성공. 안 하면 "no interpreter found". (KTH 로컬 PC가 uv standalone 3.12 실행 불가(0xC0E90002)라 둔 설정 — CI는 Linux지만 동일 설정이 적용되므로 시스템 python 공급 필수.)
4. **`NEXT_PUBLIC_*`는 빌드타임 인라인:** 런타임 주입 아님. user-web 빌드 전에 `NEXT_PUBLIC_API_URL`이 결정돼야 함 → api 먼저 배포·도메인 확보 후 user-web 빌드(순서 의존, 결정 #4/AC3).
5. **CORS 순환 의존:** api `CORS_ORIGINS`에 배포된 user-web 오리진이 있어야 브라우저 가입/로그인 동작(`allow_credentials=True`라 `*` 금지 — deferred-work "CORS credentialed-wildcard" 영역). user-web 도메인은 배포 후 확정 → 그때 api env 갱신·재배포(런북 ④).
6. **Dockerfile 재현성:** 현재 `uv.lock` 미COPY → `uv sync`가 lock 무시. `uv.lock` COPY + `uv sync --frozen`으로 고정(Task 2).
7. **PowerShell `>` UTF-16 함정(승계):** CI는 Linux라 무관하나, 로컬에서 openapi 덤프 등 파일 기록 시 1.7 함정(BOM) 주의 — 1.8은 openapi 재생성 불요(생성물 커밋됨)라 해당 경로 없음.
8. **`.gitignore` 생성물 제외 사고:** `packages/api-client/src/generated`를 실수로 무시에 추가하면 CI 빌드가 `@gosoom/api-client` 해소 실패. `openapi.json`만 무시(라인 42), 생성물은 추적 유지(Task 5).
9. **frozen-lockfile 드리프트:** `pnpm install --frozen-lockfile`은 `pnpm-lock.yaml`과 `package.json` 불일치 시 실패 → 1.7에서 락파일이 최신화됐는지 확인(추가 의존 없으면 안전). Dockerfile은 JS 무관(api 전용).
10. **Supabase 무료 티어 일시정지(NFR8):** 1주 비활성 시 자동 정지 → 데모/CI 직전 깨우기. CI pytest는 **자체 Postgres 서비스 컨테이너**를 쓰므로 Supabase 의존 없음(CI는 Supabase를 건드리지 않음). 배포 동작 확인 시에만 Supabase 활성 필요.

### 현재 코드 상태 (UPDATE/NEW 대상 — 보존할 것)

1.1~1.7이 모노레포 4앱 + 백엔드 auth/users/categories + user-web 인증 UI를 완성. 인프라는 **Dockerfile 스텁만 존재(미완), CI·배포 설정 전무**. 아래는 실제 현재 상태:

- **`.github/`** (없음 → NEW): 워크플로우 디렉터리 자체가 없다. `ci.yml` 신규 생성.
- **`apps/api/Dockerfile`** (UPDATE — "최종 확정은 Story 1.8" 주석): `python:3.12-slim` + uv + `uv sync`(현재 `pyproject.toml`만 COPY) + `CMD uvicorn`. → `uv.lock` COPY + `--frozen` + `.dockerignore` 추가. CMD는 uvicorn 유지(마이그레이션은 release command).
- **`apps/api/uv.lock`** (존재 — Dockerfile에서 활용): 재현 설치용. COPY 대상.
- **`apps/api/pyproject.toml`** (그대로 — 참조): dev 그룹(pytest/pytest-asyncio/httpx/ruff), `python-preference="only-system"`(라인 36), `[tool.pytest.ini_options] testpaths=["tests"]`. CI api 잡이 이 설정대로 `uv run pytest`·`uv run ruff check`.
- **`apps/api/tests/conftest.py`** (그대로 — CI 설계 근거): `db_session`/`client_db`가 실 DB 연결+트랜잭션 롤백. CI에 Postgres 서비스+alembic 필요한 이유.
- **`apps/api/app/core/config.py`** (그대로 — env 계약): `database_url`·`jwt_secret` 필수, `cors_origins`(콤마분리, 기본 localhost:3000), seed_* 선택. CI/배포 env 주입 기준.
- **`apps/api/app/main.py`** (그대로 — 헬스/CORS): `GET /api/v1/health`(DB 연결 200/503), `CORSMiddleware`. Railway 헬스체크·CORS 대상.
- **`apps/api/.env.example`**(그대로) / **`.env.example`**(루트, 그대로): env 키 목록 소스(런북 정합). 실 `.env`는 gitignore.
- **루트 `package.json`** (그대로 — CI 명령 소스): `build/lint/typecheck`=turbo, `packageManager=pnpm@11.5.2`, `engines.node>=20`. CI가 이 스크립트 호출.
- **`turbo.json`** (그대로): build/lint/typecheck 태스크 그래프. api는 워크스페이스 외부(package.json 없음)라 turbo 미포함 — CI에서 별도 잡으로 pytest/ruff.
- **`pnpm-workspace.yaml`**(그대로) / **`pnpm-lock.yaml`**(존재): `--frozen-lockfile` 기준.
- **`.gitignore`** (검토): `openapi.json` 무시(라인 42)·생성물 추적·`.env`류 무시 유지. `.github/`는 추적.
- **`apps/admin-web`·`apps/mobile`** (그대로 — CI 게이트 대상, 배포 제외): bare 스캐폴드. lint/typecheck(+admin build) 게이트만.
- **`packages/api-client/src/generated/`** (그대로 — 커밋됨): CI JS 빌드가 의존. 재생성 불요.

### 아키텍처 준수 (반드시 따를 규약)

- **CI/CD:** GitHub Actions — PR마다 `pytest`(api) + lint/typecheck/build(JS). 핵심 경로 우선, 커버리지 점진. Railway=GitHub 연동 자동 배포.
  [Source: architecture.md#Infrastructure & Deployment (line 224-225), AR20, epics.md#Story 1.8]
- **Railway 서비스 토폴로지:** `api`(FastAPI/Dockerfile) · `user-web` · (`admin-web` Epic 6) · `postgres`(Phase1=Supabase 외부). 모바일=Expo Go.
  [Source: architecture.md#Infrastructure & Deployment (line 221-222), AR19, Directory (line 409 Dockerfile)]
- **시크릿/환경:** 시크릿(JWT·DATABASE_URL)=Railway 환경변수. 클라이언트엔 `*_PUBLIC_API_URL`만. 시크릿은 클라이언트·로그·코드 비노출.
  [Source: architecture.md#Infrastructure & Deployment (line 223), Enforcement (line 329), AR18, NFR3]
- **이식성(NFR6):** Phase1 Supabase / Phase2 Railway = `DATABASE_URL`만 상이, 코드 동일. 마이그레이션은 `alembic upgrade head`로 멱등.
  [Source: architecture.md (line 227-228·457), NFR6]
- **시연 안정(NFR8):** Supabase 무료 1주 비활성 일시정지 → 시연 직전 깨우기. 배포 API가 데모 무중단 기반(SM4).
  [Source: architecture.md (line 229), Addendum (line 70), NFR8]
- **빌드/배포 매핑:** JS=Turbo 빌드→Railway, api=Dockerfile→Railway, mobile=Expo Go/EAS. PG=Phase별 호스팅.
  [Source: architecture.md (line 486)]
- **테스트 표준:** Python=`apps/api/tests/`(pytest + httpx.AsyncClient + dependency_overrides + 트랜잭션 롤백). JS=co-located. lint/typecheck+pytest CI로 1차 검증.
  [Source: architecture.md#Structure Patterns (line 289), Enforcement (line 332), Test (line 484)]

### 라이브러리/도구 (CI/배포)

- **GitHub Actions:** `actions/checkout@v4`, `actions/setup-python@v5`(3.12), `astral-sh/setup-uv@v6`, `pnpm/action-setup`(11.5.2), `actions/setup-node@v4`(node 20, cache pnpm). 정확한 메이저 태그는 작성 시점 최신 안정으로 핀(예시는 가이드 — action 레지스트리에서 확인).
- **uv** (api 의존성/실행): `uv sync`(dev 그룹) → `uv run pytest`/`uv run ruff check`/`uv run alembic upgrade head`. `python-preference="only-system"`라 setup-python 선행.
- **Postgres 서비스 컨테이너:** `postgres:17`(Supabase PG17 정합). `pg_isready` 헬스체크.
- **pnpm 11.5.2 / turbo 2.9.16 / Node ≥20**: 루트 `package.json` 정합. CI JS 잡.
- **Docker(api):** `python:3.12-slim` + `ghcr.io/astral-sh/uv:latest`. Railway가 Dockerfile 빌드.
- **Railway:** GitHub 연동 자동 배포. api=Docker(루트 `apps/api`), user-web=Nixpacks/Railpack(루트 레포). release command=`alembic upgrade head`. 헬스체크=`/api/v1/health`.
  [Source: architecture.md (line 221-229·409·486), Addendum (line 42·52·87), pyproject.toml, package.json]

### 파일 구조 (생성/수정 위치)

```
gosoom/
  .github/
    workflows/
      ci.yml                         (NEW) api 잡(pytest+ruff, Postgres 서비스+alembic) + JS 잡(lint/typecheck/build)
  apps/api/
    Dockerfile                       (UPDATE) uv.lock COPY + --frozen, CMD=uvicorn 유지(마이그레이션은 release command)
    .dockerignore                    (NEW) .venv/.env/tests 등 제외(슬림·시크릿 보호)
    uv.lock                          (그대로 — Dockerfile에서 COPY)
    pyproject.toml / tests/ / app/   (그대로 — 변경 없음)
  docs/
    deploy.md                        (NEW) Phase 1 배포 런북(순서·env·release command·시드·CORS)
  .gitignore                         (검토) openapi.json 무시·생성물 추적·.env 무시·.github 추적 유지
  package.json / turbo.json /
  pnpm-workspace.yaml / pnpm-lock.yaml (그대로 — CI 명령/락 소스)
  # apps/user-web: Railway 빌드는 콘솔/런북 설정(전용 코드 파일 최소). NEXT_PUBLIC_API_URL=빌드타임.
  # apps/admin-web · apps/mobile: CI 게이트만, 배포 범위 밖.
  # railway.json/nixpacks.toml: 커밋 안 함(KTH 확정) — 런북(docs/deploy.md) 문서화 + 콘솔 설정.
```
[Source: architecture.md#Complete Project Directory Structure (line 351-435), 현재 레포 상태]

### 테스트 표준

- **api CI 잡 = 기존 pytest 그대로 클라우드에서 재현.** `tests/`는 실 DB 통합(conftest `db_session`/`client_db`) → CI는 Postgres 서비스 컨테이너 + `alembic upgrade head` + `DATABASE_URL`/`JWT_SECRET` env로 동일 환경 구성. `uv run pytest`(asyncio auto) + `uv run ruff check`.
- **JS CI 잡 = 기존 게이트 + api-client Vitest(KTH 확정 포함).** `pnpm lint`/`typecheck`/`build`(turbo 전역) + `pnpm --filter @gosoom/api-client test`(Vitest 15+ 인터셉터/토큰스토어). turbo.json에 `test` 태스크가 없으므로 **루트 turbo 경유가 아니라 `--filter`로 패키지 직접 호출**(턴키 CI 스텝). 인증 인터셉터=최고위험 코드라 회귀 방지 가치 높음.
- **배포 동작 = 수동(KTH+dev).** 배포 URL 가입→로그인은 자동 E2E 아님(Playwright 범위 밖). 런북 마지막 단계로 사람 검증.
- **회귀 0:** 앱 기능 코드 미변경 → 기존 pytest/JS 게이트 그린 유지가 통합 기준.
  [Source: conftest.py, architecture.md#Test (line 484·332), 1.7 결정 #6]

### Project Structure Notes

- 정합: `.github/workflows/ci.yml`은 아키텍처 디렉터리(line 361-363)가 예고한 위치. `apps/api/Dockerfile`(line 409)도 예고됨 — 1.8이 마무리. Railway 토폴로지(api/user-web/postgres)는 line 221 정합.
- 변이/신규 결정: ① **배포 마이그레이션을 release command로 분리**(아키텍처 미명시 — Dockerfile CMD가 uvicorn만이라는 사실에서 도출한 필연, 결정 #3). ② **user-web 모노레포 빌드 = 루트 컨텍스트 + pnpm 필터**(아키텍처가 구체 빌더를 미지정 — Nixpacks 1차, 결정 #4). ③ **CI pytest용 Postgres 서비스 컨테이너**(아키텍처는 "pytest CI"만 명시 — 실 DB 의존 테스트라는 conftest 사실에서 도출, 결정 #2). 모두 새 아키텍처가 아니라 기존 코드 사실의 운영적 귀결.
- 이 스토리가 확립하는 선례: **CI 게이트(Epic 2~6 모든 PR이 통과) + 배포 파이프라인(이후 기능이 같은 경로로 배포)**. Epic 1 완결 = "가입/로그인이 실 환경에서 동작".

### 이전 스토리 학습 / 정합

- **1.2 health/CORS:** `/api/v1/health`(DB 포함)·`CORSMiddleware` 확립 → Railway 헬스체크·CORS 대상으로 재사용(신규 코드 불요).
- **1.3~1.6 백엔드 계약 동결:** auth/users/categories 라우터·스키마·마이그레이션·시드 완성 → 1.8은 이를 배포·검증만. 시드(`python -m app.seed`)는 배포 DB에 1회.
- **1.7 프론트 게이트:** `pnpm typecheck`(6/6)·`lint`·`build`(user-web 정적 프리렌더) 그린 + 생성물(`generated/`) 커밋·`openapi.json` gitignore 확정 → CI JS 잡이 그대로 의존(재생성 불요, 결정 #1/함정 #8 of 1.7).
- **manual-setup-checkpoints 메모 계승:** 외부 설정(Railway/Supabase/GitHub)을 dev-story 진입 전 KTH에 선안내(아래 체크포인트). 1.7이 CORS/.env.local을 KTH 처리로 확정한 패턴과 동일.
- **backend-env-setup 메모:** KTH PC는 uv standalone 3.12 실행 불가(0xC0E90002) → `python-preference="only-system"`. CI도 동일 설정 적용되므로 setup-python 선행 필수(함정 #3). 로컬 DB 연결은 이미 검증됨(Supabase asyncpg).
- **deferred-work 정합:** "CORS credentialed-wildcard 풋건"(`*` 금지) — 배포 시 `CORS_ORIGINS`를 명시 오리진으로(함정 #5). 다른 deferred 항목은 1.8 범위 무관.
  [Source: 1-2~1-7 story, manual-setup-checkpoints·backend-env-setup 메모, deferred-work.md]

### References

- [Source: epics.md#Story 1.8 (line 339-361)] — 4개 AC 원본(BDD): GitHub Actions CI, Railway 배포, 시크릿 env, AR23 체크포인트
- [Source: epics.md#Epic 1 (line 140-143)] — Epic 1 = CI + 워킹 스켈레톤 첫 배포 포함, 단일 기반
- [Source: architecture.md#Infrastructure & Deployment (line 219-229)] — Railway 서비스·시크릿·CI/CD·Phase2·운영주의
- [Source: architecture.md#Complete Project Directory Structure (line 361-363·409·426)] — .github/workflows/ci.yml, apps/api/Dockerfile, tests 위치
- [Source: architecture.md (line 457·484·486)] — Phase별 DATABASE_URL, 테스트 표준, 빌드/배포 매핑
- [Source: Addendum (line 40-65·70·75-88)] — Supabase=DB전용, 이관 절차, 무료티어 일시정지, AR23 수동 설정 체크포인트 표
- [Source: apps/api/Dockerfile] — "최종 확정은 Story 1.8" 스텁(uv·uvicorn)
- [Source: apps/api/pyproject.toml] — dev 그룹·`python-preference=only-system`·pytest 설정
- [Source: apps/api/tests/conftest.py] — 실 DB 통합 테스트(CI Postgres 서비스 근거)
- [Source: apps/api/app/core/config.py] — database_url·jwt_secret 필수 env
- [Source: package.json, turbo.json, pnpm-workspace.yaml, pnpm-lock.yaml] — JS CI 명령·락
- [Source: .gitignore] — openapi.json 무시·생성물 추적·.env 무시
- [Source: manual-setup-checkpoints·backend-env-setup 메모, deferred-work.md(CORS)] — KTH 선안내 원칙, uv only-system, CORS `*` 금지

## ⚡ 수동 설정 체크포인트 (AR23 — dev-story 진입 전 KTH 확인)

이 스토리는 **외부 서비스(GitHub·Supabase·Railway) 콘솔 작업이 핵심**이라, dev 코드 작성과 별개로 KTH의 수동 설정이 배포 동작(AC2)의 선결 조건입니다. dev는 아래를 먼저 안내한 뒤, KTH 설정 완료 시점에 배포를 공동 확인합니다.

1. **git init + GitHub 레포 + 최초 push (필수 — 모든 검증의 게이트):** 현재 워크스페이스는 git 저장소가 아닙니다(NO_VCS). GitHub Actions·Railway 연동 전부 GitHub 원격이 있어야 동작합니다.
   - 단계: 레포 루트에서 `git init` → `.gitignore` 확인(시크릿 `.env`류 제외, `openapi.json` 제외, 생성물·`.github` 포함) → GitHub에 새 레포 생성(private 권장) → `git remote add origin ...` → 최초 커밋·push. **시크릿 파일(`apps/api/.env`, `apps/user-web/.env.local`)이 커밋에 포함되지 않는지** push 전 확인.
2. **Supabase `DATABASE_URL` 확인 (필수 — 배포 대상 확정):** 이전 스토리에서 로컬 개발용 Supabase 프로젝트/DB 연결은 이미 검증됨(backend-env-setup). **이 프로젝트를 배포 대상으로 그대로 쓸지** 확인하고, asyncpg 형식 `DATABASE_URL`(`postgresql+asyncpg://...`)을 준비하세요. (별도 운영 DB를 원하면 알려주세요.)
3. **`JWT_SECRET` 생성 (필수):** 충분히 긴 랜덤 문자열(예: `openssl rand -hex 32` 또는 동등). 로컬과 배포는 **다른 시크릿** 권장. 절대 커밋 금지(Railway env로만).
4. **Railway 가입·GitHub 연동·서비스 생성·환경변수 (필수):**
   - Railway 가입 → GitHub 연동 → 이 레포 선택.
   - **api 서비스:** 루트 디렉터리 `apps/api`, 빌드 = Dockerfile. env: `DATABASE_URL`(2번), `JWT_SECRET`(3번), `CORS_ORIGINS`(처음엔 임시, user-web 도메인 확정 후 추가). **release/pre-deploy command = `alembic upgrade head`**(배포당 마이그레이션 1회 — dev가 런북에 정확한 명령 제공). 헬스체크 경로 `/api/v1/health`. → 배포 후 **api 공개 도메인 확보**.
   - **user-web 서비스:** 루트 디렉터리 = **레포 루트**(모노레포), build/start = `pnpm --filter user-web build`/`start`(dev 런북 제공). env: **빌드타임** `NEXT_PUBLIC_API_URL` = (방금 확보한 api 도메인)`/api/v1`. → 배포 후 **user-web 도메인 확보**.
   - **api `CORS_ORIGINS` 갱신:** user-web 도메인을 추가하고 api 재배포(브라우저 가입/로그인 CORS 통과 — `*` 금지).
5. **시드 1회 실행 (필수 — Epic 2/3 의존):** 배포 DB에 관리자/카테고리 시드(`python -m app.seed`)를 **1회** 실행(Railway one-off 또는 로컬에서 배포 `DATABASE_URL` 대상). `SEED_ADMIN_PASSWORD`는 시드 시에만 필요.
6. **배포 동작 확인 (공동):** user-web 배포 URL에서 `/signup`→`/login`→홈(displayName) 수동 플로우로 E2E 확인(AC2). Supabase가 일시정지면 먼저 깨우기(NFR8).

**확정된 결정 (2026-06-08 KTH 확인 — dev는 아래대로 진행):**
- **Supabase:** **기존(로컬 개발용) 프로젝트 재사용** — 별도 운영 DB 신설 안 함. 나중에 Railway PostgreSQL로 마이그레이션 예정(Phase 2/AR21 — 1.8 범위 밖, Post-MVP). 따라서 배포 `DATABASE_URL` = backend-env-setup에서 검증된 그 Supabase asyncpg URL.
- **Railway 빌드 설정:** **`railway.json` 커밋 안 함, 런북(`docs/deploy.md`) 문서만 + 콘솔 설정**(결정 #4·Task 3).
- **api-client Vitest:** **CI에 포함 확정** — JS 잡에 `pnpm --filter @gosoom/api-client test` 스텝 추가(Task 1·테스트 표준).
- **Playwright E2E:** **도입 안 함 확정** — 1.8 CI는 pytest(api 실DB) + JS(lint/typecheck/build + api-client Vitest)까지. 배포 가입→로그인은 KTH+dev 수동 체크리스트로 확인(thin slice 유지).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Claude Opus 4.8, 1M context) — BMAD dev-story 워크플로우

### Debug Log References

- `uv lock --check` (apps/api): exit 0 — uv.lock 동기화 확인(`--frozen` 안전)
- `uv run ruff check .` (apps/api): All checks passed
- `uv run pytest` (apps/api): **71 passed** in 25.33s (실 Postgres 통합)
- `pnpm install --frozen-lockfile` (root): Already up to date (락 드리프트 없음)
- `pnpm lint`: 3 successful / `pnpm typecheck`: 6 successful / `pnpm build`: 2 successful(user-web 정적 프리렌더)
- `pnpm --filter @gosoom/api-client test`: **17 passed** (Vitest, 토큰스토어/클라이언트 인터셉터)
- `ci.yml` YAML 파싱 검증: jobs=[api, js], triggers=[pull_request, push], api.services=[postgres], 스텝 순서 정합
- **GitHub Action 태그 검증(Dev Notes 159줄 "레지스트리 확인" 단서 이행 — dev 로컬 안전망 0):** `astral-sh/setup-uv`는 2026-03 v8.0.0부터 **불변 릴리스 정책**(moving tag `@v8` 미발행, full-version만 resolve) → 스토리 예시 `@v6` 대신 **현행 안정판 `@v8.1.0`으로 정확 핀**(첫 push job 실패 방지). 나머지(`checkout@v4`·`setup-python@v5`·`setup-node@v4`·`pnpm/action-setup@v4`)는 major moving tag 유지로 resolve.
- `pnpm --filter user-web build`(런북 문서 명령) 실검증: 정적 프리렌더(/, /login, /signup) 성공 — `pnpm build`(turbo)와 별개 경로도 그린

### Completion Notes List

**구현 범위(dev 코드 산출물 — 전부 완료·로컬 검증 그린):**
- ✅ **`.github/workflows/ci.yml`** (NEW): api 잡(Postgres 17 서비스 + setup-python 3.12 → setup-uv → `uv sync --frozen` → `alembic upgrade head` → `ruff check` → `pytest`) + JS 잡(pnpm 11.5.2 → node 20 → `--frozen-lockfile` → lint/typecheck/build → api-client Vitest). concurrency로 중복 실행 취소.
- ✅ **`apps/api/Dockerfile`** (UPDATE): `uv.lock` COPY + `uv sync --frozen`으로 재현 가능 설치 전환. CMD=uvicorn 유지(마이그레이션은 release command로 분리, 결정 #3).
- ✅ **`apps/api/.dockerignore`** (NEW): `.venv`/`__pycache__`/`tests`/`.env` 제외(슬림화·시크릿 보호).
- ✅ **`docs/deploy.md`** (NEW): Phase 1 배포 런북 — git/GitHub 게이트, 시크릿 표, api 서비스(release command=`alembic upgrade head`, 헬스체크 `/api/v1/health`), user-web 서비스(레포 루트 컨텍스트 + pnpm 필터, `NEXT_PUBLIC_API_URL` 빌드타임 순서), CORS 갱신, 시드 1회, 공동 동작 확인.
- ✅ **`.gitignore`** (검토 — 변경 없음): `openapi.json` 무시·생성물(`generated/`) 추적·`.env`류 무시·`.github` 추적 모두 요구대로. 시크릿 파일(`apps/api/.env`, `apps/user-web/.env.local`)이 무시 패턴에 걸림을 확인. **변경 최소 원칙대로 수정 없음.**

**dev 검증 한계 / KTH 공동 검증 대기 (거짓 완료 금지 — 정직 보고):**
- 🔶 **AC1의 "GitHub에서 CI 그린"은 dev 단독 검증 불가:** 워크스페이스가 아직 git 저장소가 아니다(NO_VCS). dev의 DoD는 **(a) `ci.yml` 구조/문법 정합, (b) CI가 부르는 명령이 로컬에서 그린**이며 둘 다 충족(위 Debug Log). 실제 GitHub Actions 실행은 **KTH push 후** 확인.
- 🔶 **AC2 "배포 URL에서 가입→로그인 동작"은 dev 단독 검증 불가:** Railway/Supabase 콘솔 배선이 선행돼야 하는 **KTH+dev 공동 검증**이다. dev는 파이프라인·설정 파일·런북을 정확히 작성했고, KTH 체크포인트(스토리 맨 아래) 완료 후 함께 배포 동작을 확인한다.
- 회귀 0: 앱 기능 코드(api 라우터/서비스/모델, user-web 화면/훅, api-client) 미변경. 기존 pytest 71·JS 게이트 그린 유지.

**KTH 체크포인트(AC4 — 진입 전 선안내 완료):** git init·GitHub 레포·push → Supabase `DATABASE_URL` 확인 → `JWT_SECRET` 생성 → Railway api/user-web 서비스 + env + **release command** + CORS 갱신 → 시드 1회 → 공동 배포 확인. 상세는 스토리 "⚡ 수동 설정 체크포인트" 및 `docs/deploy.md` 참조.

### File List

- `.github/workflows/ci.yml` (NEW)
- `apps/api/Dockerfile` (UPDATE)
- `apps/api/.dockerignore` (NEW)
- `docs/deploy.md` (NEW)
- `.gitignore` (검토 — 변경 없음)

### Review Findings

- [x] [Review][Patch] Dockerfile `uv:latest` 비고정으로 빌드 재현성 위반 [`apps/api/Dockerfile`:8] — fixed: `0.11`로 핀
- [x] [Review][Patch] Dockerfile `CMD` 셸 형식으로 SIGTERM 미전달 — Railway 그레이스풀 셧다운 불가 [`apps/api/Dockerfile`:24] — fixed: exec 형식으로 변경
- [x] [Review][Defer] CI `JWT_SECRET` 평문 하드코딩 [`apps/api/Dockerfile`:27, `ci.yml`:25] — deferred, CI 전용 테스트 값, 공개 레포 시 패턴 주의
- [x] [Review][Defer] `turbo`에 `test` 태스크 없어 향후 패키지 테스트 자동화 누락 가능 — deferred, 의도적 설계, 추후 범위
- [x] [Review][Defer] `apps/mobile` 빌드 트리거 우려 — deferred, 1.7에서 그린 검증됨
- [x] [Review][Defer] Railway release command 실패 시 부분 마이그레이션 위험 — deferred, 아키텍처적 제약
- [x] [Review][Defer] GitHub Actions 액션 SHA 미고정 (supply chain 표면) — deferred, MVP 범위 결정
- [x] [Review][Defer] `.dockerignore`에 `alembic/` 미제외 — deferred, 이미지 슬림화 경미한 최적화

## Change Log

- 2026-06-08 — Story 1.8 구현(CI 파이프라인 + 배포 골격). `.github/workflows/ci.yml`(api pytest+ruff / JS lint+typecheck+build+Vitest) 신규, `apps/api/Dockerfile` 재현성 마무리(uv.lock+`--frozen`), `apps/api/.dockerignore` 신규, `docs/deploy.md` 배포 런북 신규, `.gitignore` 정합 확인(변경 없음). 로컬 게이트 전부 그린(pytest 71·Vitest 17·typecheck 6·build 2). AC2 배포 동작은 KTH 콘솔 배선 후 공동 검증 대기.
