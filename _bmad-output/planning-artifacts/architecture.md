---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - '_bmad-output/planning-artifacts/prds/prd-gosoom-2026-06-07/prd.md'
  - '_bmad-output/planning-artifacts/prds/prd-gosoom-2026-06-07/addendum.md'
  - '_bmad-output/planning-artifacts/research/technical-gosoom-mvp-tech-stack-research-2026-06-07.md'
  - 'docs/idea.md'
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-06-07'
project_name: 'gosoom'
user_name: 'KTH'
date: '2026-06-07'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (24개, 6개 그룹):**
- **인증·계정 (FR1-4):** 역할 선택 가입(고객/고수), 관리자는 시드+기존 관리자 추가.
  JWT 세션·refresh, 역할 기반 접근 제어. → *단일 인증/인가 계층*이 모든 기능을 감쌈.
- **고객·서비스 요청 (FR5-8):** 요청 CRUD + 상태(open→matched→completed/cancelled),
  견적 비교. → *요청 상태 기계*가 거래 루프의 출발점.
- **고수·카테고리·견적 (FR9-12):** 복수 카테고리 설정, 카테고리 매칭 요청 열람,
  견적 제안(요청당 1개), 견적 상태 조회. → *카테고리 참조 무결성* + *견적 상태 기계*.
- **매칭 (FR13-14):** 견적 수락(원자적 3-step: 요청→matched, 채팅방 생성, 타 견적 마감) /
  거절. → *트랜잭션 무결성의 핵심 지점*.
- **채팅 (FR15-18):** 수락 기반 1:1 채팅방, 텍스트 전송/폴링 수신, 채팅방 목록.
  → *REST 폴링 패턴* (실시간 인프라 없음).
- **관리자 (FR19-24):** 계정(고객/고수/관리자) 비활성화, 요청 관리·소프트삭제, 채팅 열람(읽기전용),
  카테고리 CRUD. → *소프트 삭제/비활성화 + 읽기전용 감사 접근*.

**Non-Functional Requirements (아키텍처 구동 요인):**
- **NFR4 권한 일관성:** 3클라이언트가 동일 권한 규칙 → API 레벨 단일 시행 지점.
- **NFR6 이식성:** Phase 1(Supabase)→Phase 2(Railway) 이관이 기능 코드 변경 없이 가능해야 함
  → repository 계층 + SQLAlchemy/Alembic 의무화.
- **NFR7 데이터 무결성:** 상태 전이 일관성·거래 데이터 무손실 → 트랜잭션 경계 설계.
- **NFR3 보안:** 비밀번호 해싱(Argon2), 토큰 기반 인증, 서버 측 권한 검사, 시크릿 비노출, HTTPS.
- **NFR5 성능 / CM1:** 채팅 폴링 주기·페이로드 관리(과도한 요청 방지).
- **NFR9 확장성:** 채팅을 데이터 모델 변경 없이 실시간으로 업그레이드 가능하게(과설계 금지).
- **NFR1 플랫폼:** 반응형 웹 ×2 + 모바일 앱(Expo Go 시연) = 3 클라이언트.
- **NFR8/NFR10 운영:** 시연 안정 기동(Supabase 일시정지 깨우기), 데이터 단조증가·용량 한도 인지.

### Scale & Complexity

- **Primary domain:** 풀스택 (Next.js 웹 ×2 + React Native/Expo 모바일 + FastAPI + PostgreSQL)
- **Complexity level:** Medium — 도메인 범위는 좁고 명확(단일 거래 루프)하나,
  3클라이언트 동시 지원 · 상태 기계 2종 · 트랜잭션 무결성 · DB 이식성이 복잡도를 끌어올림.
- **Estimated architectural components:**
  앱 4개(user-web, admin-web, mobile, api) + 공유 패키지(types, api-client, ui, config) +
  도메인 모듈 6개(auth, users, categories, requests, quotes, chat) + DB 6 엔티티.

### Technical Constraints & Dependencies

확정된 제약(Addendum·리서치에서 도출):
- **아키텍처 원칙:** Supabase = DB(PostgreSQL) 전용. 인증·채팅·권한 등 나머지 전부 FastAPI 소유.
- **패턴 A 강제:** 클라이언트는 Supabase 직접 접속 금지. 모든 요청은 FastAPI 단일 경유.
- **RLS 미사용:** service_role 키가 RLS를 항상 우회하므로 권한은 앱 레벨로 일원화.
- **미도입 기술:** WebSocket · Redis · 파일 스토리지 · 소셜로그인 · 결제 · 알림 (전부 Post-MVP).
- **스택 고정:** Next.js / RN+Expo(SDK52+) / FastAPI(router→service→repository) /
  SQLAlchemy+Alembic / Turborepo / Railway.
- **운영 제약:** Supabase 무료 티어(DB 500MB, 1주 비활성 시 자동 일시정지), 한국어 UI.
- **통합 함정:** CORS(웹↔API 오리진 상이), Expo Go 실기기는 localhost 불가(LAN IP/배포 URL).

### Cross-Cutting Concerns Identified

1. **인증·인가 (Auth/RBAC):** JWT 발급·검증, `user_role` 기반 라우트 가드 — 전 FR 횡단.
2. **상태 전이 무결성:** 요청·견적 상태 기계의 일관성 — 특히 FR13 견적 수락 트랜잭션.
3. **소프트 삭제/비활성화:** 계정·요청·카테고리의 물리 삭제 금지 + 참조 무결성 보호.
4. **채팅 폴링:** 페이로드·주기 관리, 데이터 모델 무변경 업그레이드 여지.
5. **DB 이식성(Phase 1→2):** repository 계층 격리 + Alembic 스키마 버전 관리.
6. **모노레포 코드 공유:** types·api-client를 3 클라이언트가 공유 (웹↔모바일).
7. **시크릿·환경 관리:** JWT 키·DB 자격증명 서버 전용, 클라이언트별 API URL 주입.

## Starter Template Evaluation

### Primary Technology Domain

**폴리글랏(polyglot) 모노레포** — TypeScript 앱 3개(types·api-client 공유) + Python FastAPI 1개 + PostgreSQL.
프로젝트 요구사항(NFR1 3클라이언트 + 확정 스택)에서 도출.

### Starter Options Considered (웹 검증 완료, 2026-06)

| 스타터 | 제공 | gosoom 적합성 판정 |
|--------|------|-------------------|
| **create-t3-turbo** | Turbo + Next 15 + Expo 54 / **tRPC v11 + Better Auth + Drizzle ORM** | ❌ **부적합** — 모노레포 글루의 핵심 가치가 *tRPC(end-to-end TS 클라이언트)* 인데, FastAPI 백엔드 채택 시 정확히 그 부분을 삭제하게 됨. 남는 것은 SQLAlchemy·자체 JWT와 **충돌**하는 Drizzle·Better Auth 잔재. "도입 후 제거" 전략의 이득이 거의 없고, 기본 Pages Router는 확정된 App Router와도 불일치. |
| **Railway Next.js+FastAPI 스타터** | Next + FastAPI + **Redis + 백그라운드 워커**, 단일 웹 | ⚠️ **배포 토폴로지 참조용** — 모바일·모노레포 없음. gosoom이 배제한 Redis/워커 포함. 토폴로지(Railway에 Next+FastAPI+PG)가 검증되었다는 근거로만 활용. |
| **Vercel `with-react-native-web` (공식 Turborepo 예제)** | Turbo + Next + Expo + 공유 UI 패키지 | ✅ **배선(wiring) 참조** — Expo-in-모노레포의 Metro 설정을 tRPC/인증/ORM 강요 없이 제공. 단 핀된 버전이 현재보다 뒤처짐 → 초기화는 공식 per-app 스캐폴드로. |

> **핵심 통찰:** create-t3-turbo가 모노레포 글루를 정당화하는 공유 패키지는 *tRPC 클라이언트* 그 자체다.
> gosoom은 이를 FastAPI로 대체하므로, 이 스타터를 통째로 도입한 뒤 도려내는 것은 vestigial 설정만 남긴다.

### 검증된 현재 버전 (2026-06)

- **Next.js 16.2.7** — App Router 안정, Turbopack 기본, React Compiler 안정.
- **Expo SDK** — 최신 56(약 1일 전 릴리스, RN 0.85/React 19.2) vs **55(채택)**.
- create-t3-turbo는 Next 15 / Expo 54로 뒤처져 있어 직접 차용 시 추가 업그레이드 부담.

### Selected Starter: "단일 올인원 스타터 없음 — 의도적 조합형 스캐폴드 (Composed Scaffold)"

**Rationale for Selection:**
gosoom의 폴리글랏 형상(TS 앱 3 + Python API 1)에 통째로 맞는 스타터는 존재하지 않는다. 이는 *공백*이 아니라
**의도적 결정**이다 — 공식 최소 스캐폴드를 조합하여 ① 현재 버전을 확보하고, ② 확정 아키텍처(FastAPI 자체 JWT,
SQLAlchemy/Alembic, App Router)와 충돌하는 군더더기(tRPC/Better Auth/Drizzle)를 처음부터 배제한다.

**Initialization Command (= 첫 구현 스토리로 채택):**

```bash
# 1) Turborepo 워크스페이스 골격 (공식 최소)
pnpm dlx create-turbo@latest gosoom --package-manager pnpm

# 2) 앱 스캐폴드 (각 공식 최신 — 현재 버전 확보)
pnpm dlx create-next-app@latest apps/user-web    # Next 16, App Router, TS
pnpm dlx create-next-app@latest apps/admin-web   # Next 16, App Router, TS
pnpm dlx create-expo-app@latest apps/mobile      # Expo SDK 55 핀(아래 결정)

# 3) FastAPI 백엔드 — Turbo 태스크 그래프 외부, 수동 스켈레톤
#    apps/api: router→service→repository + Alembic (Python, 별도 빌드/배포 파이프라인)

# 4) 공유 패키지
#    packages/types  packages/api-client  packages/ui  packages/config
```

> Expo-in-모노레포의 Metro 설정은 Vercel `with-react-native-web` 공식 예제를 **배선 참조**로 사용한다.

**Architectural Decisions Provided / Fixed by This Scaffold:**

- **Language & Runtime:** TypeScript(웹·모바일, strict), Python 3.x(API). pnpm 워크스페이스 + Turborepo 태스크 그래프.
- **앱 토폴로지:** `apps/user-web`, `apps/admin-web`, `apps/mobile`, `apps/api`(Turbo 외부).
- **공유 패키지:** `types`(공유 DTO/타입), `api-client`(FastAPI 호출, 3앱 공유), `ui`(RN Web 호환), `config`(eslint/tsconfig).
- **Build Tooling:** Turborepo 캐싱·병렬 태스크(JS 앱 한정). FastAPI는 별도 파이프라인.
- **Styling/Testing/Lint:** per-app 공식 스캐폴드 기본값 채택 후, 공유 `config` 패키지로 lint/tsconfig 일원화.

### Expo SDK 버전 결정 (NFR8 시연 안정성)

- **채택: Expo SDK 55** — one-behind 안정 버전. Expo Go 호환성 검증됨. 데모 신뢰성 우선 MVP에 안전.
- (반려) SDK 56: 약 1일 전 릴리스 최신. 라이브러리/Expo Go 호환 이슈가 최신 SDK에 먼저 표면화하는 경향 → 시연 리스크.

**Note:** 위 초기화(Composed Scaffold)는 **첫 번째 구현 스토리**로 다룬다.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (구현 차단 — 반드시 선결):**
- DB=PostgreSQL + SQLAlchemy 2.0(async/asyncpg) + Alembic (확정)
- 인증=FastAPI 자체 JWT, 인가=앱 레벨(RLS 미사용) (확정)
- API=REST 단일 경유(패턴 A), 채팅=REST 폴링 (확정)
- 공유 타입/클라이언트=FastAPI OpenAPI → **Orval 자동생성** (신규 결정)
- 토큰 전송=**Bearer 헤더 통일**(웹·모바일) (신규 결정)
- FR13 동시성=`SELECT FOR UPDATE` + 요청당 수락 1개 partial unique index (신규 결정)

**Important Decisions (아키텍처 형성):**
- ID=UUIDv7, 소프트삭제=status/is_active+deleted_at, 상태기계=service 단일 시행
- 에러 envelope 표준, cursor 페이지네이션, `/api/v1` 버저닝
- 프론트 서버상태=TanStack Query v5, 스타일=Tailwind+NativeWind+공유 ui

**Deferred Decisions (Post-MVP):**
- BFF 분리(현재는 단일 API+역할별 엔드포인트), Rate limiting, 자동 계측/모니터링 고도화
- 파일 스토리지(R2), 실시간(SSE/WebSocket), 데이터 아카이빙 정책

### Data Architecture

- **DB 접근:** SQLAlchemy 2.0.36 **async 엔진 + asyncpg**(SQLAlchemy 2.0 호환 버전). FastAPI async 라우트와 정합,
  채팅 폴링의 다수 동시 read에 유리(NFR5/CM1).
- **마이그레이션:** Alembic. 스키마=코드 버전관리 → Phase 2는 `alembic upgrade head`로 동일 스키마 재생성.
  autogenerate 후 사람이 검수. **시드:** 초기 관리자 1개(FR1/FR21) + 기본 카테고리는 Alembic data migration/seed 스크립트.
- **모델링:**
  - **ID:** UUIDv7 PK (시간정렬 가능, 이관·노출 안전).
  - **소프트 삭제/비활성화:** 계정=`is_active`, 요청=`status`(open/matched/completed/cancelled),
    숨김/삭제=`deleted_at` 타임스탬프. 물리삭제 금지(FR19/20/22/24, NFR7/NFR10).
  - **상태 기계:** 요청·견적 상태를 DB enum으로 제약 + **전이 규칙은 service 계층에서 단일 시행**.
  - **참조 무결성:** 사용 중 카테고리는 비활성화만(물리삭제 차단, FR24).
- **FR13 트랜잭션(가장 위험):** 단일 트랜잭션 안에서 ① 요청→matched ② chat_room 생성 ③ 타 견적→closed.
  동시 수락 race는 `SELECT ... FOR UPDATE`(요청 행 잠금) + **`service_request_id`에 "accepted 견적 1개" partial unique index**로 차단.
- **검증:** Pydantic v2(`ConfigDict(from_attributes=True)`)로 요청/응답 스키마. service 계층에서 비즈니스 규칙 검증.

### Authentication & Security

- **토큰 전송: Bearer 헤더 통일** — 웹·모바일 모두 `Authorization: Bearer <jwt>`.
  - **저장:** access=클라이언트 메모리(휘발), refresh=웹 저장소/모바일 **Expo SecureStore**.
  - **함의:** api-client 웹/모바일 분기 없음(과설계 금지 부합), CSRF 무관. **XSS 노출 리스크**는
    입력 이스케이프·의존성 관리·짧은 access 수명으로 완화. (보안 강화 필요 시 Post-MVP에 httpOnly 쿠키 하이브리드 승격 여지)
- **JWT:** HS256, payload=`{user_id, user_role, exp}`. access 15~30분 + refresh 7~30일. 시크릿=서버 환경변수 전용.
- **인가:** FastAPI `OAuth2PasswordBearer` + `Depends` 가드. `user_role`로 고객/고수/관리자 라우트 분기.
  권한은 **service 계층에서 소유권 검사**(고객=본인 요청, 고수=본인 견적, 관리자=전체).
- **비밀번호:** Argon2(pwdlib) 해싱. 평문 미보관(NFR3).
- **refresh 전략(MVP):** refresh로 access 재발급 엔드포인트. 로그아웃/탈취 대응 회전·블랙리스트는 Post-MVP(단순 유지).
- **전송:** HTTPS(Railway 자동), CORS=FastAPI `CORSMiddleware`에 명시 오리진(운영 `*` 금지).

### API & Communication Patterns

- **REST + OpenAPI 3.1(FastAPI 자동).** `/api/v1` 프리픽스. 태그=도메인(auth/users/categories/requests/quotes/chat).
- **클라이언트 생성: Orval** — `openapi.json` → `packages/api-client`에 **TS 타입 + TanStack Query 훅** 생성.
  → FastAPI Pydantic이 **단일 소스**, 3클라이언트 타입 자동 동기화(NFR4, AI 에이전트 일관 구현 목표).
  - **빌드 산출물 취급:** OpenAPI를 빌드 아티팩트로 관리, operationId 안정화(라우트 함수명 규칙).
- **에러 표준:** 통일 envelope `{code, message, detail?}`, 적절한 HTTP status. api-client에서 일관 처리.
- **페이지네이션:** cursor 기반(요청·견적·메시지·관리자 목록).
- **채팅 폴링 계약:** 송신 `POST /api/v1/chat/rooms/{id}/messages`, 수신 `GET .../messages?after=<last_id>`.
  클라이언트 2~3초 폴링(TanStack Query `refetchInterval`). 페이로드 최소화(증분만, CM1).
- **(Deferred)** Rate limiting, BFF 분리.

### Frontend Architecture

- **앱:** `user-web`(Next 16 App Router), `admin-web`(Next 16 App Router), `mobile`(Expo SDK 55).
- **서버 상태:** **TanStack Query v5** — 폴링은 `refetchInterval`, 캐시·재검증 일원화. api-client 훅(Orval) 소비.
- **클라이언트 상태:** 최소화(인증 토큰·UI 상태). 전역 상태 라이브러리 도입은 필요 시에만(과설계 금지).
- **라우팅/가드:** App Router 레이아웃에서 역할 기반 가드(미인증·권한 외 리다이렉트). 권한 최종 시행은 서버(NFR4).
- **스타일:** Tailwind v4(웹) + NativeWind v4(모바일, tailwindcss@3 기반), 공유 `packages/ui`(RN Web 호환 프리미티브).
- **환경:** `NEXT_PUBLIC_API_URL` / `EXPO_PUBLIC_API_URL`로 API 베이스 주입(로컬·배포 분리).
  Expo Go 실기기=LAN IP 또는 배포 Railway URL(localhost 불가).

#### user-web 디자인 시스템 (Epic 1~4 완료 시점 확정, 2026-06-11)

- **컴포넌트 라이브러리:** **shadcn/ui** (v4.11.0) — `src/components/ui/` 하위에 button, input, card, badge, label, textarea, select, separator 설치됨.
  - user-web 페이지는 **`@gosoom/ui` 직접 사용 금지**. shadcn/ui를 사용한다(`@gosoom/ui`는 mobile 전용).
- **브랜드 컬러:** Primary = `#1360F5` → `oklch(0.506 0.236 264.4)`. globals.css `--primary` 변수로 관리.
- **공통 레이아웃 컴포넌트:** `src/components/AppHeader.tsx` — sticky h-14 전역 헤더.
  - `/login`, `/signup`에서 `null` 반환(인증 페이지는 전체화면 Card 레이아웃 사용).
  - 고객 네비: 내 요청 / 채팅. 고수 네비: 요청 피드 / 내 견적 / 카테고리 / 채팅.
- **페이지 레이아웃:** 기본 `max-w-screen-lg mx-auto p-6`. 채팅 상세는 `h-[calc(100vh-3.5rem)]`(AppHeader 높이 보정).
- **컨벤션:** 상세 패턴(임포트 규칙, 폼 패턴, 상태 Badge, 채팅 메시지 스타일 등)은 `apps/user-web/CLAUDE.md` 참조.

#### mobile 디자인 시스템 (인프라만 준비, 기능 페이지는 bmad 루프로 개발)

- **NativeWind v4** 세팅 완료 (tailwindcss@3, babel.config.js, metro.config.js withNativeWind, global.css).
- **브랜드 토큰:** `packages/ui/src/tokens.ts` — React Native StyleSheet용 색상·간격·반경 상수. 모바일 컴포넌트는 이 토큰을 참조한다.
- mobile 기능 페이지 신규 개발 시: NativeWind className + tokens.ts 조합 사용. `@gosoom/ui` 공유 프리미티브 활용.

### Infrastructure & Deployment

- **Railway 서비스:** `api`(FastAPI), `user-web`, `admin-web`, `postgres`(Phase1=Supabase 외부 / Phase2=Railway PG).
  모바일=Expo Go(시연) → 필요 시 EAS Build.
- **환경 구성:** 시크릿(JWT·DATABASE_URL)=Railway 환경변수. 클라이언트엔 `*_PUBLIC_API_URL`만.
- **CI/CD:** GitHub Actions — PR마다 `pytest`(api) + lint/typecheck(JS). 핵심 경로 우선, 커버리지 점진.
  Railway=GitHub 연동 자동 배포.
- **로깅/모니터링:** 구조적 로깅(기본). 고도화 모니터링·자동 계측=Post-MVP(R4).
- **Phase 2 이관:** Railway PG 프로비저닝 → `pg_extension` 확인 → `alembic upgrade head` + `supabase db dump` 데이터 →
  `DATABASE_URL` 교체·재배포. **앱 코드 변경 없음**(NFR6).
- **운영 주의:** Supabase 무료 1주 비활성 일시정지 → 시연 직전 깨우기(NFR8). 용량 단조증가 인지(NFR10).

### Decision Impact Analysis

**Implementation Sequence (의존 순서):**
1. Composed Scaffold(모노레포+4앱 골격) — 첫 스토리
2. DB 기반: SQLAlchemy(async) + Alembic 초기 마이그레이션 + 시드(관리자/카테고리)
3. 인증: users + 가입/로그인/refresh + JWT 가드 → Orval 첫 생성으로 api-client 확립
4. 핵심 도메인: 카테고리 → 요청(고객) → 견적(고수) → 견적 수락(FR13 트랜잭션)
5. 채팅: chat_rooms/messages + 폴링 계약
6. 관리자: 계정/요청/카테고리 관리 + 채팅 열람
7. 클라이언트: user-web → mobile → admin-web (공유 api-client 재사용)
8. Phase 2 이관(필요 시)

**Cross-Component Dependencies:**
- Orval 생성 api-client는 **FastAPI OpenAPI에 종속** → 백엔드 엔드포인트 선행, 프론트가 소비.
- Bearer 헤더 통일 → api-client 인증 인터셉터 단일 구현(웹·모바일 공유).
- 상태 기계(요청·견적)는 service 계층이 단일 소유 → FR7/FR10/FR12/FR13/FR14가 동일 전이 규칙 참조.
- 소프트 삭제 규칙은 전 도메인 횡단 → repository 공통 필터(`deleted_at IS NULL`).

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 폴리글랏(Python+TS) 스택에서 에이전트가 다르게 선택할 수 있는
지점 — JSON 필드 표기(경계), 명명 규칙, 계층 구조, 에러/페이로드 포맷, 폴링·인증 처리.

### Naming Patterns

**Database (PostgreSQL, snake_case):**
- 테이블=복수 snake_case: `users`, `categories`, `service_requests`, `quotes`, `chat_rooms`, `messages`
- 컬럼=snake_case: `created_at`, `updated_at`, `deleted_at`, `is_active`, `user_role`
- FK=`<단수참조>_id`: `customer_id`, `pro_id`, `category_id`, `service_request_id`, `chat_room_id`
- PK=`id`(UUIDv7) · 인덱스=`ix_<table>_<col>` · partial unique=`uq_quotes_accepted_per_request`
- enum 값=snake_case 문자열: 요청 `open|matched|completed|cancelled`, 견적 `pending|accepted|rejected|closed`

**API (REST, `/api/v1`):**
- 경로=복수 명사 kebab-case: `/api/v1/service-requests`, `/api/v1/chat-rooms/{id}/messages`
- 경로 파라미터=`{id}` · 쿼리=camelCase(`after`, `cursor`, `categoryId`)
- **JSON 필드=camelCase** (Pydantic `alias_generator=to_camel` + `populate_by_name=True`).
  내부 Python 속성은 snake_case 유지, 직렬화/역직렬화 경계에서만 camelCase.
- operationId=라우트 함수명 안정화(Orval 생성 클라이언트 함수명에 직결).

**Python (FastAPI):**
- 함수/변수=snake_case, 클래스=PascalCase, 모듈/파일=snake_case
- Pydantic 스키마=PascalCase + 접미사(`ServiceRequestCreate`, `ServiceRequestRead`, `QuoteRead`)
- SQLAlchemy 모델=PascalCase 단수(`ServiceRequest`, `Quote`)

**TypeScript (웹·모바일):**
- 변수/함수=camelCase, 타입/컴포넌트=PascalCase
- React 컴포넌트 파일=`UserCard.tsx`(PascalCase), 훅=`useChatPolling.ts`, 유틸=camelCase `.ts`
- Orval 생성 타입/훅=생성기 규칙 따름(수정 금지, 빌드 산출물)

### Structure Patterns

**Backend (`apps/api`) — router→service→repository:**
- `app/routers/<domain>.py` (HTTP·검증·의존성) → `app/services/<domain>.py` (비즈니스·권한·트랜잭션)
  → `app/repositories/<domain>.py` (DB 접근, `deleted_at IS NULL` 공통 필터)
- `app/models/` (SQLAlchemy), `app/schemas/` (Pydantic), `app/core/` (config·security·db), `alembic/`
- **과설계 금지:** 도메인이 작으면 파일 분리 최소화, 필요 시 확장.
- 테스트=`tests/`(pytest + httpx.AsyncClient + dependency_overrides + 트랜잭션 롤백)

**Frontend (Next.js / Expo):**
- 기능(feature) 단위 구성. 공유는 `packages/`(types·api-client·ui·config)로 승격.
- 테스트=co-located `*.test.ts(x)`.

### Format Patterns

- **성공 응답:** 리소스 직접 반환(불필요 래핑 금지). 목록=`{items: [...], nextCursor: string|null}`.
- **에러 응답:** `{code: string, message: string, detail?: object}` + 적절한 HTTP status(4xx/5xx).
  `code`=기계 판독용 안정 식별자, `message`=사용자 노출 가능 한국어.
- **날짜/시간:** API=ISO 8601 UTC 문자열(`2026-06-07T12:00:00Z`). 현지화·포맷팅은 클라이언트.
- **불리언/null:** `true/false`, 비어있음은 `null` 명시(빈 문자열 대체 금지).
- **금액(견적가):** 정수 KRW(원 단위), 소수점 없음.

### Communication Patterns

- **상태 변경:** 이벤트 버스 없음(MVP). 상태 전이는 service 계층 메서드로 동기 수행.
- **채팅 폴링:** 수신 `GET /chat-rooms/{id}/messages?after=<lastId>`(증분), 송신 `POST .../messages`.
  클라이언트=TanStack Query `refetchInterval` 2~3초. 페이로드=신규 메시지만(CM1).
- **상태 업데이트(프론트):** 불변 업데이트. 서버 상태=TanStack Query 단일 소스(수동 캐시 중복 금지).
- **로깅:** 구조적(JSON) 로깅, 레벨 `debug|info|warning|error`. 시크릿·비밀번호·토큰 로깅 절대 금지.

### Process Patterns

- **인증 플로우:** api-client 단일 인터셉터가 `Authorization: Bearer` 부착, 401 시 refresh 1회 시도 후 재요청,
  실패 시 로그아웃. 웹·모바일 공유 로직.
- **에러 처리:** 백엔드=service에서 도메인 예외 → 라우터/예외 핸들러가 표준 envelope로 변환.
  프론트=TanStack Query `error` 상태로 일관 처리, 사용자 메시지=`error.message`.
- **로딩 상태:** TanStack Query `isPending`/`isFetching` 사용(자체 boolean 난립 금지).
- **검증 타이밍:** 1차=클라이언트(UX), 최종·권위=서버(Pydantic + service). 클라이언트 검증 신뢰 금지(NFR3/NFR4).
- **권한 검사:** 모든 보호 엔드포인트에서 `Depends` 인증 + service 소유권 검사. 클라이언트 라우트 가드는 UX 보조일 뿐.

### Enforcement Guidelines

**All AI Agents MUST:**
- DB=snake_case, API JSON=camelCase, Python=snake_case, TS=camelCase/PascalCase 규칙을 예외 없이 따른다.
- Orval 생성물(`packages/api-client`)을 **수동 수정하지 않는다**(스키마 변경은 백엔드에서, 재생성).
- 모든 권한·상태 전이·소프트삭제 규칙은 **service 계층**에서 시행한다(라우터/클라이언트에 분산 금지).
- 에러는 표준 envelope로만 반환한다.
- 시크릿을 클라이언트·로그·코드에 노출하지 않는다.

**Pattern Enforcement:**
- lint/typecheck(공유 `config`) + `pytest` CI로 1차 검증.
- 규칙 위반·신규 패턴 필요 시 본 문서에 추가 후 합의.

### Pattern Examples

**Good:**
- `GET /api/v1/service-requests?status=open&cursor=...` → `{items, nextCursor}`, 필드 `createdAt`(camel).
- 견적 수락=`QuoteService.accept(quote_id, current_user)` 단일 트랜잭션(요청 잠금→matched→방 생성→타 견적 closed).

**Anti-Patterns:**
- 라우터에서 직접 DB 쿼리·권한 검사(service 우회) ❌
- TS에서 snake_case 필드 수기 매핑 또는 Orval 산출물 직접 편집 ❌
- 클라이언트 검증만 믿고 서버 검증 생략 ❌
- 채팅에서 전체 메시지 매 폴링마다 재수신(증분 미사용) ❌

## Project Structure & Boundaries

### Complete Project Directory Structure

```
gosoom/
├─ package.json                  # 루트(pnpm workspaces, turbo 스크립트)
├─ pnpm-workspace.yaml           # apps/*, packages/*
├─ turbo.json                    # 태스크 그래프(build/lint/test/typecheck) — JS 앱 한정
├─ tsconfig.base.json            # 공유 TS 베이스
├─ orval.config.ts               # FastAPI openapi.json → packages/api-client 생성 설정
├─ .env.example                  # 루트 공통 예시(클라이언트 *_PUBLIC_API_URL 등)
├─ .gitignore
├─ README.md
├─ .github/
│  └─ workflows/
│     └─ ci.yml                  # pytest(api) + lint/typecheck/build(JS)
│
├─ apps/
│  ├─ user-web/                  # 고객·고수 반응형 웹 (Next.js 16, App Router)
│  │  ├─ package.json
│  │  ├─ next.config.ts
│  │  ├─ tailwind.config.ts      # packages/config 프리셋 확장
│  │  ├─ tsconfig.json
│  │  ├─ .env.local.example      # NEXT_PUBLIC_API_URL
│  │  ├─ src/
│  │  │  ├─ app/
│  │  │  │  ├─ layout.tsx
│  │  │  │  ├─ (auth)/login/page.tsx       # FR2
│  │  │  │  ├─ (auth)/signup/page.tsx      # FR1
│  │  │  │  ├─ (customer)/requests/        # FR5-8 (목록/생성/상세/견적비교)
│  │  │  │  ├─ (pro)/feed/                 # FR10 (카테고리 매칭 요청)
│  │  │  │  ├─ (pro)/quotes/               # FR11-12 (견적 제안/내 견적)
│  │  │  │  ├─ (pro)/categories/page.tsx   # FR9
│  │  │  │  └─ chat/                       # FR15-18
│  │  │  ├─ features/            # 기능 단위 컴포넌트·훅(auth/requests/quotes/chat)
│  │  │  ├─ providers/           # QueryClientProvider, AuthProvider
│  │  │  └─ middleware.ts        # 역할 기반 라우트 가드(UX 보조)
│  │  └─ tests/                  # *.test.tsx (co-located 우선)
│  │
│  ├─ admin-web/                 # 관리자 반응형 웹 (Next.js 16, App Router)
│  │  ├─ (구성 user-web과 동일 패턴)
│  │  └─ src/app/
│  │     ├─ (auth)/login/        # FR2 (관리자)
│  │     ├─ users/               # FR19-20 (고객/고수 관리)
│  │     ├─ admins/              # FR21 (관리자 관리)
│  │     ├─ requests/            # FR22 (요청 관리·소프트삭제)
│  │     ├─ chats/               # FR23 (채팅 열람, 읽기전용)
│  │     └─ categories/          # FR24 (카테고리 CRUD)
│  │
│  ├─ mobile/                    # 고객·고수 모바일 앱 (Expo SDK 55, RN)
│  │  ├─ package.json
│  │  ├─ app.json                # Expo 설정
│  │  ├─ metro.config.js         # 모노레포 인식(Vercel RN+Next 예제 배선 참조)
│  │  ├─ babel.config.js         # nativewind
│  │  ├─ .env.example            # EXPO_PUBLIC_API_URL
│  │  ├─ app/                    # expo-router(파일 라우팅): auth/requests/quotes/chat
│  │  └─ src/features/           # user-web과 동일 도메인, ui·api-client 공유
│  │
│  └─ api/                       # 통합 API (FastAPI) — Turbo 태스크 그래프 외부
│     ├─ pyproject.toml          # FastAPI/SQLAlchemy/asyncpg/alembic/pydantic/pwdlib
│     ├─ .env.example            # DATABASE_URL, JWT_SECRET, CORS_ORIGINS
│     ├─ Dockerfile              # Railway 배포
│     ├─ alembic.ini
│     ├─ alembic/
│     │  ├─ env.py
│     │  └─ versions/            # 마이그레이션 + 시드(초기 관리자/기본 카테고리)
│     ├─ app/
│     │  ├─ main.py              # FastAPI 앱, CORSMiddleware, /api/v1 라우터 등록, 예외 핸들러
│     │  ├─ core/
│     │  │  ├─ config.py         # 환경설정(pydantic-settings)
│     │  │  ├─ db.py             # async engine/session(asyncpg), get_db 의존성
│     │  │  └─ security.py       # Argon2, JWT 발급/검증, OAuth2PasswordBearer
│     │  ├─ models/              # SQLAlchemy: user, category, service_request, quote, chat_room, message
│     │  ├─ schemas/             # Pydantic(to_camel alias): *Create/*Read/*Update
│     │  ├─ routers/             # auth, users, categories, service_requests, quotes, chat, admin
│     │  ├─ services/            # 비즈니스·권한·트랜잭션(상태기계 단일 시행)
│     │  ├─ repositories/        # DB 접근(deleted_at IS NULL 공통 필터)
│     │  └─ deps.py              # get_current_user, require_role(...)
│     └─ tests/                  # pytest: 핵심 플로우(가입·요청·견적·수락·채팅)
│
└─ packages/
   ├─ api-client/               # Orval 생성물 + 래퍼
   │  ├─ src/generated/         # ⚠️ 자동생성(수정 금지): TS 타입 + TanStack Query 훅
   │  ├─ src/client.ts          # Bearer 인터셉터, 401→refresh 1회, baseURL 주입
   │  └─ src/index.ts
   ├─ types/                    # 비-API 공유 타입·상수(역할/상태 enum 미러, 라우트 상수)
   ├─ ui/                       # RN Web 호환 공유 프리미티브(Button, Input, Card...)
   └─ config/                   # eslint-config, tsconfig presets, tailwind preset
```

### Architectural Boundaries

**API Boundaries (FastAPI = 유일 경유 / 패턴 A):**
- 외부 노출=`/api/v1/*` REST. 클라이언트는 DB 직접 접속 금지.
- 인증 경계=`deps.get_current_user`(JWT 검증) + `require_role`(역할 가드).
- 계층 경계=router(HTTP) → service(비즈니스/권한/트랜잭션) → repository(DB). 역방향 호출 금지.

**Component Boundaries (프론트):**
- 3앱은 도메인 로직을 직접 구현하지 않고 **api-client 훅**으로만 백엔드와 통신.
- 서버 상태=TanStack Query(단일 소스). 공유 UI=packages/ui. 앱 고유 화면=apps/*/features.

**Service Boundaries (백엔드 도메인):**
- auth · users · categories · service_requests · quotes · chat · admin.
- admin 라우터=관리자 콘솔 엔드포인트, 도메인 service를 역할 가드 하에 호출(로직 중복 금지).
- 상태 전이(요청·견적)·소프트삭제·소유권 검사는 **service 단일 소유**.

**Data Boundaries:**
- repository만 DB 접근. 모든 조회는 `deleted_at IS NULL` 기본 필터.
- 트랜잭션 경계=service 메서드(특히 `QuoteService.accept`).
- Phase 1 Supabase / Phase 2 Railway = `DATABASE_URL`만 상이, 코드 동일.

### Requirements to Structure Mapping

| FR 그룹 | 백엔드 | 프론트 |
|---------|--------|--------|
| 인증·계정 FR1-4 | `routers/auth.py`, `services/auth.py`, `core/security.py`, `deps.py` | user-web `(auth)/`, admin-web `(auth)/` |
| 고객 요청 FR5-8 | `routers/service_requests.py`, `services/service_request.py` | user-web `(customer)/requests/` |
| 고수 카테고리·견적 FR9-12 | `routers/categories.py`, `routers/quotes.py`, `services/quote.py` | user-web `(pro)/feed`, `(pro)/quotes`, `(pro)/categories` |
| 매칭 FR13-14 | `services/quote.py`(accept/reject 트랜잭션) | user-web `(customer)/requests/[id]`(견적 수락/거절) |
| 채팅 FR15-18 | `routers/chat.py`, `services/chat.py` | user-web·mobile `chat/` |
| 관리자 FR19-24 | `routers/admin.py` → 도메인 services | admin-web `users/admins/requests/chats/categories` |

**Cross-Cutting Concerns:**
- 인증/인가=`core/security.py` + `deps.py`(백엔드), `packages/api-client/src/client.ts`(프론트 인터셉터).
- 소프트삭제=repository 공통 필터. 상태기계=services. 에러 envelope=`main.py` 예외 핸들러.

### Integration Points

**Internal:** 프론트 → api-client 훅 → `/api/v1` → router → service → repository → PostgreSQL.
**External:** PostgreSQL(Supabase/Railway), Railway(배포), Expo(모바일 빌드/시연). 결제·알림·스토리지 없음.
**Data Flow (견적 수락 예):** 고객 수락 → `POST /quotes/{id}/accept` → `QuoteService.accept`(요청 잠금→matched→chat_room 생성→타 견적 closed, 단일 트랜잭션) → 응답 → 프론트 TanStack Query 무효화·갱신.

### File Organization & Workflow

- **Config:** 루트=turbo/pnpm/tsconfig.base/orval, 공유=packages/config, 앱별=각 app 루트, 시크릿=`.env`(예시는 `.env.example`).
- **Source:** JS=feature 단위 + packages 공유, Python=router/service/repository/models/schemas.
- **Test:** Python=`apps/api/tests/`(pytest), JS=co-located `*.test.ts(x)`.
- **Dev 서버:** `turbo dev`(JS 앱 병렬) + `uvicorn`(api 별도). api-client 재생성=`pnpm orval`(openapi.json 기준).
- **Build/Deploy:** JS=Turbo 빌드→Railway, api=Dockerfile→Railway, mobile=Expo Go/EAS. PG=Phase별 호스팅.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** 모든 기술 선택이 충돌 없이 맞물림. 검증 버전 — Next.js 16.2.7 / Expo SDK 55 /
FastAPI 0.136.1 / SQLAlchemy 2.0.36(async+asyncpg) / Pydantic 2.10.4 / TanStack Query v5 / Turborepo(pnpm).
패턴 A(FastAPI 단일 경유) + RLS 미사용 + 자체 JWT는 일관된 단일 권한 경계로 수렴(상호 모순 없음).

**Pattern Consistency:** 명명(DB snake / API camel / Python snake / TS camel·Pascal)이 Orval 자동생성과 정합.
camelCase API 결정이 Python↔TS 경계 충돌을 제거. 에러 envelope·폴링 계약·인증 인터셉터가 3클라이언트에 단일 적용.

**Structure Alignment:** 모노레포 트리가 모든 결정을 수용 — router→service→repository 계층, packages 공유,
api-client 자동생성 경계, 소프트삭제 공통 필터 위치가 명확.

### Requirements Coverage Validation ✅

**Functional Requirements (24/24 지원):**
- 인증 FR1-4 → auth/security/deps, 관리자 시드(alembic)·추가(admin).
- 고객 FR5-8 → service_requests + 상태기계. 고수 FR9-12 → categories/quotes.
- 매칭 FR13-14 → QuoteService(accept 단일 트랜잭션 / reject).
- 채팅 FR15-18 → chat_rooms/messages + 폴링. 관리자 FR19-24 → admin 라우터 + 소프트삭제/비활성화.

**Non-Functional Requirements (10/10 지원):**
- NFR1 3클라이언트=apps. NFR2 한국어 UI/에러. NFR3 Argon2·JWT·서버검증·시크릿·HTTPS.
- NFR4 단일 API 권한=패턴 A+service. NFR5 async+폴링 주기. NFR6 repository+Alembic+DATABASE_URL.
- NFR7 트랜잭션+상태기계+소프트삭제. NFR8 Supabase 깨우기 절차. NFR9 채팅 모델 무변경 업그레이드.
- NFR10 용량 단조증가 인지.

### Implementation Readiness Validation ✅

**Decision Completeness:** 핵심 결정 모두 버전과 함께 문서화. 신규 결정(Orval/Bearer/async/camelCase) 근거 명시.
**Structure Completeness:** 완전한 모노레포 트리 + FR→파일 매핑 + 경계 정의 완료.
**Pattern Completeness:** 명명·구조·포맷·통신·프로세스 패턴 + Enforcement + Good/Anti 예시 제공.

### Gap Analysis Results

**Critical Gaps:** 없음 (구현 차단 요소 없음).

**Important Gaps (첫 데이터 모델링 스토리에서 확정):**
- **G1. 고수↔카테고리 M:N 조인 테이블** — FR9 "고수 복수 카테고리"는 엔티티 목록에 명시되지 않은
  `pro_categories`(user_id, category_id) 연결 테이블이 필요. 고수 피드(FR10) 쿼리의 전제.
- **G2. chat_rooms 관계 컬럼** — 수락 견적 기반 방(FR13/15)은 `service_request_id`, `customer_id`,
  `pro_id`(+추적용 `quote_id`) FK가 필요. 구조엔 암시됐으나 컬럼 수준 미확정.
- **G3. messages 발신자 식별** — `sender_id`(+role)와 증분 폴링용 정렬 키(`id`/`created_at`) 확정 필요.

**Minor Gaps (의식적 수용):**
- **로그아웃(FR2) 의미** — Bearer 무상태라 서버 토큰 무효화 없음 → 로그아웃=클라이언트 토큰 폐기.
  refresh 회전·블랙리스트는 Post-MVP. (MVP 의도된 단순화)

**Technical Feasibility 주의 (첫 스토리에서 검증·고정 — advisor 검토 반영):**
- **G4. UUIDv7 생성 위치** — 네이티브 `uuidv7()`는 PostgreSQL **18+**부터 제공되나 Supabase는 **PG17**.
  따라서 DB 측 `DEFAULT uuidv7()` 사용 금지 → **앱 측 생성**(Python `uuid7` 라이브러리)로 고정.
  이렇게 하면 PG17→Railway 이관 시 `pg_uuidv7` 등 확장 의존성도 회피(NFR6 강화).
- **G5. React 버전 정렬** — Next.js 16은 React 19.2를 끌어오고 Expo SDK 55는 더 이른 React를 핀.
  공유 `packages/ui`(RN-Web 프리미티브)는 pnpm 모노레포에서 **단일 React 해석**이 필요할 수 있음
  → 스캐폴드 시점에 React 버전 호환을 점검(필요 시 SDK 55가 지원하는 React로 정렬).

### Validation Issues Addressed

G1-G3는 아키텍처 altitude가 아닌 **상세 스키마 영역**으로, 첫 구현(데이터 모델링) 스토리에서 컬럼 수준으로 확정한다.
아키텍처 결정·패턴·경계와는 충돌하지 않으며, 모두 정의된 엔티티(`users`/`categories`/`service_requests`/
`quotes`/`chat_rooms`/`messages`)와 패턴(snake_case·UUIDv7·소프트삭제) 안에서 해소된다.

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY WITH MINOR GAPS
(16개 체크 항목은 아키텍처 altitude에서 모두 충족 / Critical Gap 없음. 단 데이터 모델 세부 G1-G3는
첫 구현 스토리에서 컬럼 수준 확정 필요 → "MINOR GAPS"로 정직하게 표기.)

**Confidence Level:** High — 입력 문서(PRD/리서치/Addendum)가 고도로 정렬되어 있고, 신규 결정이 웹 검증된
현재 버전과 명시 근거를 가짐.

**Key Strengths:**
- "Supabase=DB 전용" 원칙으로 Phase 2 이관 비용을 설계 시점에 제거(NFR6).
- camelCase API + Orval로 폴리글랏 경계의 타입 일관성을 자동 보장(NFR4, AI 일관 구현 목표).
- FR13 트랜잭션·소프트삭제·상태기계가 service 단일 소유로 무결성 보장(NFR7).
- 스택 최소화(WebSocket/Redis/스토리지 제거)로 시연 안정성·운영 단순성 확보.

**Areas for Future Enhancement:**
- 실시간 채팅(SSE/WebSocket), 파일 스토리지(R2), BFF 분리, refresh 회전·rate limiting, 자동 계측.

### Implementation Handoff

**AI Agent Guidelines:**
- 본 문서의 아키텍처 결정을 정확히 준수. 구현 패턴을 전 컴포넌트에 일관 적용.
- 프로젝트 구조·경계 존중. 아키텍처 질문은 본 문서를 단일 참조로.
- Orval 생성물 수동 수정 금지. 권한·상태전이·소프트삭제는 service 단일 시행.

**First Implementation Priority:**
Composed Scaffold 초기화(모노레포+4앱 골격, 스캐폴드 중 G5 React 버전 점검) → 직후 첫 데이터 모델링
스토리에서 G1-G4(M:N 조인·chat_rooms FK·messages 발신자·UUIDv7 앱측 생성) 확정.
