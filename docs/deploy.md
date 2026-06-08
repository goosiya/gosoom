# gosoom 배포 런북 (Phase 1 — Railway + Supabase)

이 문서는 **워킹 스켈레톤(가입→로그인)을 실 배포 환경에서 동작**시키기 위한 절차다(Story 1.8 / AC2).
배포 대상은 **`api`(FastAPI) + `user-web`(Next.js)** 두 서비스이며, DB는 **Supabase PostgreSQL(Phase 1)** 을 외부 연결로 사용한다.

> **Phase 경계:** Phase 1은 Supabase(외부 PG)만 사용한다. Railway PostgreSQL로의 이관(Phase 2/AR21)은
> Post-MVP 범위이며 이 런북 밖이다. 코드는 동일하고 `DATABASE_URL`만 달라진다(NFR6).

> **admin-web · mobile은 배포 범위 밖**이다(admin=Epic 6, mobile=Expo Go/Epic 5). 1.8 배포는 api + user-web만.

---

## 0. 사전 준비 (KTH 수동 — 모든 검증의 게이트)

현재 워크스페이스는 **git 저장소가 아니다**(NO_VCS). GitHub Actions(CI)와 Railway GitHub 연동은
**GitHub 원격 저장소가 선결 조건**이다. `ci.yml`을 작성해도 push되기 전엔 실행되지 않는다.

1. 레포 루트에서 `git init`
2. `.gitignore` 확인 — 시크릿(`.env`류) 제외, `openapi.json` 제외, **생성물(`packages/api-client/src/generated/`)·`.github/`는 추적 포함**
3. GitHub에 새 레포 생성(private 권장)
4. `git remote add origin <repo-url>`
5. **최초 커밋 전 시크릿 파일이 스테이징에 없는지 반드시 확인:**
   ```bash
   git status            # apps/api/.env, apps/user-web/.env.local 이 보이면 안 됨
   git ls-files | grep -E '\.env($|\.local)'   # 출력이 비어야 정상
   ```
6. 최초 커밋·`git push -u origin main`

> push 직후 GitHub Actions의 `CI` 워크플로우(api + js 잡)가 자동 실행된다. 두 잡이 그린인지 확인.

---

## 1. 시크릿/환경변수 준비 (KTH 수동)

| 변수 | 주입 위치 | 비고 |
|---|---|---|
| `DATABASE_URL` | Railway **api** env | `postgresql+asyncpg://...` (asyncpg 형식). **기존 Supabase 프로젝트 재사용**(2026-06-08 확정). |
| `JWT_SECRET` | Railway **api** env | `openssl rand -hex 32` 등 충분히 긴 랜덤. **로컬과 다른 값 권장.** 절대 커밋 금지. |
| `CORS_ORIGINS` | Railway **api** env | 콤마 구분. 처음엔 임시, **user-web 도메인 확정 후 추가**(아래 4단계). `*` 금지(`allow_credentials=True`). |
| `NEXT_PUBLIC_API_URL` | Railway **user-web** env | **빌드타임** 공개 변수. `https://<api-도메인>/api/v1`. api 배포·도메인 확보 후 주입. |
| `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` | 시드 실행 시에만 | 1회 시드(5단계)에만 필요. 평문 비밀번호는 미보관(Argon2 해싱). |

**시크릿은 클라이언트 번들·로그·코드·레포에 절대 노출 금지(AC3/NFR3).** `.env`류는 `.gitignore`로 추적 제외돼 있다.

---

## 2. api 서비스 (Railway — Dockerfile 빌드)

- **빌드:** Dockerfile (`apps/api/Dockerfile`)
- **루트 디렉터리:** `apps/api`  *(빌드 컨텍스트 = apps/api 트리; Dockerfile `COPY . .`이 이 트리를 복사)*
- **환경변수:** `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`(임시 → 4단계에서 갱신)
- **🔴 release / pre-deploy command (필수):**
  ```bash
  uv run alembic upgrade head
  ```
  > 배포 DB에 스키마를 생성/갱신한다. **이 설정이 없으면 배포된 API가 빈 스키마를 바라봐
  > 가입/로그인이 500으로 실패한다(가장 흔한 누락).** 마이그레이션은 멱등이므로 매 배포 1회 실행돼도 안전.
  > 마이그레이션을 Dockerfile `CMD`/`entrypoint`에 넣지 않는 이유: 다중 레플리카가 동시에
  > 마이그레이션하는 것을 피하기 위해 **배포당 1회만** 실행하는 release command로 분리(결정 #3).
- **헬스체크 경로:** `/api/v1/health` (Story 1.2 — DB 연결 포함 200/503)
- 배포 성공 후 **api 공개 도메인을 확보**한다(다음 단계에서 user-web에 주입).

> **대안(release command 미지원 시):** `apps/api/entrypoint.sh`로 `alembic upgrade head && exec uvicorn ...`를
> 구성할 수 있으나 **단일 인스턴스 가정**에서만 안전하다. MVP는 release command를 권장한다.

---

## 3. user-web 서비스 (Railway — 모노레포 Next 빌드)

user-web은 pnpm 워크스페이스의 일부이고 `@gosoom/api-client`·`@gosoom/ui`(`workspace:*`)를 의존한다.
공유 패키지가 해소되려면 **빌드 컨텍스트가 레포 루트**여야 한다.

- **빌더:** Railway 기본 빌더(Nixpacks/Railpack) — *1차 경로*
- **루트 디렉터리:** **레포 루트**(모노레포 루트)
- **install command:** `pnpm install --frozen-lockfile`
- **build command:** `pnpm --filter user-web build`
- **start command:** `pnpm --filter user-web start`
- **환경변수(빌드타임):** `NEXT_PUBLIC_API_URL = https://<api-도메인>/api/v1`
  > `NEXT_PUBLIC_*`는 **Next 빌드 시점에 번들로 인라인**된다(런타임 주입 아님). 따라서
  > **api 먼저 배포 → api 도메인 확보 → user-web에 주입 → user-web 빌드** 순서를 반드시 지킨다.
- 배포 성공 후 **user-web 공개 도메인을 확보**한다(다음 단계 CORS 갱신에 사용).

> **`railway.json`은 커밋하지 않는다**(2026-06-08 KTH 확정). 위 설정값은 Railway 콘솔에서 적용하고
> 이 런북으로 문서화한다. user-web 전용 Dockerfile은 1차 경로(Railway 빌더)가 막힐 때만 고려(후순위).

---

## 4. CORS 갱신 (api ← user-web 도메인)

브라우저에서 가입/로그인이 동작하려면 api의 `CORS_ORIGINS`에 **배포된 user-web 오리진**이 포함돼야 한다
(`allow_credentials=True`라 `*` 사용 불가). user-web 도메인은 3단계 배포 후 확정되므로 여기서 갱신한다.

1. Railway **api** 서비스 env `CORS_ORIGINS`에 user-web 오리진 추가
   (예: `https://<user-web-도메인>`; 콤마로 여러 개 가능)
2. api 재배포

---

## 5. 시드 1회 실행 (관리자/카테고리 — Epic 2/3 의존)

마이그레이션은 매 배포 release command로 멱등 실행되지만, **시드는 1회만** 실행한다.

```bash
# Railway one-off 명령 또는 로컬에서 배포 DATABASE_URL 대상으로
uv run python -m app.seed
```

- `SEED_ADMIN_PASSWORD`는 시드 실행 시에만 필요한 시크릿이다.
- 관리자/카테고리가 없으면 Epic 2/3의 의존이 비게 된다(시드 누락 주의).

---

## 6. 배포 동작 확인 (KTH + dev 공동 — AC2)

배포된 **user-web URL**에서 수동 E2E:

1. `/signup` — 회원가입
2. `/login` — 로그인
3. 인증 후 홈에서 **displayName 표시** 확인

> **Supabase 무료 티어 일시정지(NFR8):** 1주 비활성 시 자동 정지된다. 데모/확인 직전에 깨운다.
> (CI의 pytest는 자체 Postgres 서비스 컨테이너를 쓰므로 Supabase에 의존하지 않는다 — 배포 동작 확인 시에만 활성 필요.)

---

## 부록 — CI(GitHub Actions)와 배포의 관계

- **CI(`.github/workflows/ci.yml`):** PR/main push마다 코드 품질 게이트만 검증한다.
  - **api 잡:** Postgres 서비스 컨테이너 + `alembic upgrade head` + `ruff check` + `pytest`(실 DB 통합).
  - **JS 잡:** `pnpm install --frozen-lockfile` + `lint`/`typecheck`/`build`(turbo 전역) + api-client Vitest.
  - CI는 **Supabase를 건드리지 않는다**(자체 Postgres 컨테이너 사용).
- **배포(Railway):** main 병합 시 GitHub 연동으로 api·user-web이 자동 배포된다(이 런북의 콘솔 설정 기반).
- CI 게이트와 배포 파이프라인은 **Epic 2~6의 모든 기능이 통과·전달되는 공통 경로**가 된다.

## 로컬 검증 명령 (CI와 1:1 대응)

CI가 부르는 명령은 로컬에서 그대로 재현된다:

```bash
# api (apps/api에서; 로컬 Postgres + .env 필요)
uv run ruff check .
uv run pytest

# JS (레포 루트)
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm build
pnpm --filter @gosoom/api-client test
```
