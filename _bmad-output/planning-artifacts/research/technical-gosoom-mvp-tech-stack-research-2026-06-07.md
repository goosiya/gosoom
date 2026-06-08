---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: ['docs/idea.md']
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: '숨고형 MVP 기술 스택 종합 타당성 검증 (실시간 채팅 · 인증/권한 3-role · Supabase→Railway 이관 · 코드 공유 모노레포)'
research_goals: 'PRD 작성용 기술 의사결정 근거 마련 — 4개 핵심 주제의 기술 타당성을 넓고 빠르게 검증'
user_name: 'KTH'
date: '2026-06-07'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-06-07
**Author:** KTH
**Research Type:** technical

---

## Research Overview

본 문서는 "숨고" 유사 양면 서비스 마켓플레이스 MVP(고객·고수·관리자 3-role, Next.js 웹×2 + React Native 앱 + FastAPI + PostgreSQL)의 **기술 타당성을 PRD 의사결정 근거로** 검증한 기술 리서치 보고서다. 6단계 워크플로우(범위확정 → 기술스택 → 통합패턴 → 아키텍처 → 구현 → 종합)로 진행했으며, 모든 핵심 주장은 2026년 현재 공개 출처로 교차 검증했다.

핵심 결론: idea.md의 스택은 2026년 기준 전부 검증된 조합이며, Railway에 Next.js+FastAPI+PostgreSQL을 올리는 공식 풀스택 스타터가 존재해 토폴로지가 입증되었다. 리서치 진행 중 사용자 지침으로 **아키텍처 원칙이 "Supabase=DB 전용, 나머지 기능 전부 FastAPI 소유"로 확정**되었고, 이에 따라 ① 채팅은 WebSocket 없이 **HTTP 폴링**, ② 인증은 **FastAPI 자체 JWT**, ③ 파일 업로드는 **MVP 범위 제외**, ④ 권한은 **앱 레벨(RLS 미사용)**로 결정되었다. 이 결정들의 종합 효과로 Phase 2 Railway 이관이 "기능 재구현"에서 **"DATABASE_URL 환경변수 교체 수준"**으로 단순화되고, MVP 기술 스택이 **REST + PostgreSQL** 중심으로 최소화된다.

상세 분석은 본문 각 섹션을, 최종 권고·로드맵·리스크는 "Technical Research Recommendations"와 아래 "Research Synthesis"의 임원 요약을 참조하라.

---

<!-- Content will be appended sequentially through research workflow steps -->

## Technical Research Scope Confirmation

**Research Topic:** 숨고형 MVP 기술 스택 종합 타당성 검증 (실시간 채팅 · 인증/권한 3-role · Supabase→Railway 이관 · 코드 공유 모노레포)
**Research Goals:** PRD 작성용 기술 의사결정 근거 마련 — 4개 핵심 주제의 기술 타당성을 넓고 빠르게 검증

**Technical Research Scope:**

- Architecture Analysis - design patterns, frameworks, system architecture
- Implementation Approaches - development methodologies, coding patterns
- Technology Stack - languages, frameworks, tools, platforms
- Integration Patterns - APIs, protocols, interoperability
- Performance Considerations - scalability, optimization, patterns

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-06-07

---

## Technology Stack Analysis

> 신뢰도 등급: 🟢 다중 출처 확인 · 🟡 단일/제한 출처 · 🔴 추정·검증 필요

### 기술 스택 (Technology Stack) — idea.md 스택의 성숙도 평가

| 계층 | 선택 | 2026 성숙도 | 판정 |
|------|------|------------|------|
| 사용자/관리자 웹 | Next.js | 🟢 표준, 안정 | 적합 |
| 모바일 앱 | React Native + Expo (SDK 52+) | 🟢 모노레포 자동 감지 지원 | 적합 |
| 통합 API | FastAPI | 🟢 비동기 표준 | 적합, 단 실시간엔 추가 구성 필요 |
| DB(Phase 1) | Supabase (PostgreSQL) | 🟢 BaaS 성숙 | 적합 |
| DB(Phase 2) | Railway PostgreSQL | 🟢 zero-config 프로비저닝 | 적합 |
| 배포 | Railway (FE/BE/PG) | 🟢 풀스택 스타터 존재 | 적합 |

**핵심 발견:** idea.md의 6개 스택은 2026년 기준 모두 검증된 조합이며, Next.js + FastAPI + PostgreSQL을 Railway에 배포하는 공식 풀스택 스타터 템플릿이 존재한다(Next.js+FastAPI+PostgreSQL+Redis+worker). 🟢
_Source: [Railway Next.js+FastAPI Starter](https://railway.com/deploy/nextjs-fastapi-full-stack-starter), [Railway FastAPI Guide](https://docs.railway.com/guides/fastapi)_

### 주제 1 — 실시간 채팅 아키텍처

두 가지 선택지가 명확히 갈린다:

- **Supabase Realtime (Broadcast):** Elixir/Phoenix 기반 글로벌 분산 클러스터. WebSocket으로 수백만 동시 연결 처리 가능, 채팅용 Broadcast 기능 내장. **추가 인프라 0** (Redis·메시지 브로커 불필요). 무료 티어 **동시 realtime 연결 200개** 제한. 🟢
- **FastAPI WebSocket 직접 구현:** 최대 제어·처리량 가능하나 **Redis + 메시지 브로커 + 커스텀 WebSocket 코드**가 별도로 필요. 한 사례에서 동등 기능 구축에 Supabase 4시간 vs FastAPI 18시간(단 FastAPI가 부하 시 3배 처리량). 🟡

**MVP 권고 (⚡사용자 지침 — 최대한 단순 + 스택 최소화):** Supabase Realtime·WebSocket **둘 다 사용 안 함.** 채팅을 **순수 REST + HTTP 폴링(short polling)**으로 구현한다. 즉 채팅도 평범한 CRUD:
> - 전송: `POST /chat/rooms/{id}/messages`
> - 수신: `GET /chat/rooms/{id}/messages?after=<last_id>` 를 클라이언트가 **2~3초 간격으로 폴링**
>
> **추가 기술 0** — WebSocket·ConnectionManager·Redis·sticky-session 전부 불필요. 무상태(stateless)라 배포·확장이 일반 REST와 동일. 폴링은 "WebSocket 효용의 80%를 복잡도 20%로" 제공해 MVP/시연에 최적. 메시지는 PostgreSQL `messages` 테이블에 저장. 🟢
> **업그레이드 경로:** 추후 실시간성이 필요하면 **데이터 모델 변경 없이** 폴링 → SSE → WebSocket으로 단계 전환 가능(`messages` 테이블 그대로 재사용). 🟢
_Source: [WebSocket vs SSE vs Polling 가이드](https://dev.to/crit3cal/websockets-vs-server-sent-events-vs-polling-a-full-stack-developers-guide-to-real-time-3312), [Long Polling Guide 2025](https://velt.dev/blog/long-polling-guide-real-time-updates), [Polling vs WebSockets](https://designgurus.substack.com/p/real-time-web-apps-choosing-between)_

### 주제 2 — 인증/권한 (3-role: 고객·고수·관리자)

> ⚡ **사용자 지침 반영:** Supabase Auth 사용 안 함(`auth.users`·JWT 시크릿 종속 회피). **FastAPI가 인증을 자체 소유**한다. Supabase Auth 패턴은 아래 "고려 후 기각"으로 보존.

- **권장 패턴 (FastAPI 자체 인증):** PostgreSQL에 `users` 테이블 직접 운영 → 비밀번호 **Argon2(pwdlib, FastAPI 공식 권장)** 또는 bcrypt 해싱 → 로그인 시 FastAPI가 **JWT 자체 발급**(짧은 access 15~30분 + refresh 7~30일). access 토큰 페이로드에 `user_id`, `user_role`(고객/고수/관리자), 만료 포함. 단일 서비스이므로 **HS256**으로 충분(분산 시 RS256 고려). 🟢
- **검증:** 모든 API 호출의 `Authorization: Bearer <jwt>`를 FastAPI `OAuth2PasswordBearer` + `Depends`로 추출·검증, `user_role`로 라우트 권한 분기. 🟢
- **웹+모바일 토큰 저장:** 웹(Next.js)=httpOnly 쿠키 권장, **RN/Expo=Expo SecureStore**(refresh 토큰). supabase-js 인증 기능은 사용하지 않음. 🟢
- **이관 영향:** `users` 테이블·인증 코드 모두 FastAPI/PostgreSQL에 있으므로 **Phase 2 이관 시 인증은 무수정**(JWT 시크릿 동일 유지 → 재로그인 불필요). 🟢

**(고려 후 기각) Supabase Auth 방식:** Custom Access Token Hook으로 JWT에 `user_role` 주입 + RLS `has_role()` 검사. 개발은 빠르나 `auth.users`·플랫폼 종속이 생겨 **이관 시 전원 재인증 필요** → 사용자 지침과 충돌하여 기각. 🟢
_Source: [FastAPI OAuth2+JWT 공식](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [FastAPI JWT Auth (Neon)](https://neon.com/guides/fastapi-jwt), [Securing FastAPI with JWT](https://testdriven.io/blog/fastapi-jwt-auth/), [(기각) Custom Claims & RBAC](https://supabase.com/docs/guides/database/postgres/custom-claims-and-role-based-access-control-rbac)_

### 주제 3 — Supabase → Railway PostgreSQL 이관

- **핵심 도구:** 원시 `pg_dump`가 아니라 **`supabase db dump`** 사용(내부 스키마 제외, 예약 롤 제거, 멱등 `IF NOT EXISTS` 추가). 원시 pg_dump는 Supabase 내부 포함 → 복원 시 권한 오류. 🟢
- **사전 점검:** `select * from pg_extension`로 비기본 확장 확인 후 대상 DB에 활성화. plain SQL 덤프는 메이저 버전 간 호환(Supabase는 PG17, 자체호스팅 기본 PG15 가능). 🟢
- **이관 시 사라지는 BaaS 기능:** Auth, Realtime, Storage, RLS 자동 적용은 Supabase 플랫폼 종속 → Railway 순수 PostgreSQL로 가면 이 기능들을 **FastAPI 애플리케이션 레벨에서 재구현**해야 함. 🟡

**판단:** DB 데이터 이관 자체는 표준 절차로 저위험. **진짜 비용은 DB가 아니라 Auth/Realtime/RLS의 앱 레벨 재구현**임. → PRD에서 "Phase 2 = 단순 DB 이사"가 아니라 "BaaS 기능 내재화"로 정의해야 함. 🟡
_Source: [Restore Platform to Self-Hosted](https://supabase.com/docs/guides/self-hosting/restore-from-platform), [Transferring cloud to self-host](https://supabase.com/docs/guides/troubleshooting/transferring-from-cloud-to-self-host-in-supabase-2oWNvW)_

### 주제 4 — 코드 공유 모노레포 (Next.js ×2 + RN)

- **표준 구성:** Turborepo + Expo + Next.js App Router + React Native Web. Expo **SDK 52부터 모노레포 자동 감지**로 Metro 설정 이슈 해소, 웹↔모바일 **최대 90% 코드 공유** 가능. 🟢
- **검증된 스타터:** `create-t3-turbo`(Expo+Next.js+pnpm+Turborepo), `turborepo-bun-next-expo`(Next 웹 + Expo 앱 + 공유 UI/config 패키지). 🟢
- **공유 대상:** 타입, API 클라이언트, supabase-js 래퍼, 도메인 로직을 `packages/`에 두고 앱 3개(user-web, admin-web, mobile)가 소비. 🟡
- **비용:** Turborepo 캐싱/태스크 그래프·의존성 그래프 학습 곡선. 단 2명 이상 팀이면 코드 재사용 이득이 복잡도 상회. 🟢

_Source: [Turborepo React Native (Vercel)](https://vercel.com/templates/next.js/turborepo-react-native), [create-t3-turbo Review 2026](https://starterpick.com/guides/create-t3-turbo-review-2026), [Turborepo+RN+Next 2025 Guide](https://medium.com/better-dev-nextjs-react/setting-up-turborepo-with-react-native-and-next-js-the-2025-production-guide-690478ad75af)_

### 기술 채택 트렌드 / 제약 (Adoption & Constraints)

- **Supabase 무료 티어 (2026):** DB 500MB, 파일 1GB, MAU 5만, **realtime 동시 연결 200개**, 프로젝트 2개. **2026-02-01부터 비활성 1주 후 자동 일시정지**(재개 ~30초). 시연/MVP엔 충분하나, 데모 직전 일시정지 깨우기 필요. Pro $25/월. 🟢
- **supabase-py 성능 주의:** 의존성 주입 시 매번 httpx 클라이언트 생성 → **클라이언트 재사용**으로 최적화 필요. 🟡
- **FastAPI+Supabase 통합 한계:** FastAPI 네이티브가 아닌 REST/Python 클라이언트 경유라 DI·async 패턴과 덜 자연스러움. 🟡

_Source: [Supabase Pricing](https://supabase.com/pricing), [Supabase Free Tier 2026](https://uibakery.io/blog/supabase-pricing), [supabase-py](https://github.com/supabase/supabase-py)_

---

## Integration Patterns Analysis

### ⚡ 확정된 아키텍처 원칙 (사용자 지침 — 2026-06-07)

> **"Supabase는 DB(PostgreSQL)로만 사용한다. 인증·실시간 채팅·스토리지 등 나머지 모든 기능은 FastAPI가 담당하여 Supabase에 종속되지 않게 한다."**
>
> → 클라이언트는 **Supabase에 직접 접속하지 않는다.** 모든 요청은 FastAPI 단일 경유(패턴 A). FastAPI ↔ PostgreSQL은 표준 DB 드라이버(asyncpg/SQLAlchemy) 또는 Phase 1 한정 supabase-py로 연결.
> → **이관 = DB 연결 문자열 교체 수준.** 채팅·인증·권한 로직은 전부 FastAPI에 있어 Phase 2에서 무수정.
> → Supabase 고유 기능(Auth/Realtime/Storage/RLS) **전부 미사용.**

### ⭐ 위 원칙의 근거: "API 경유" vs "BaaS 직접 접속"

idea.md는 "통합 API(FastAPI)"를 두는데, 클라이언트가 DB에 닿는 경로가 두 가지로 갈린다. 사용자 지침은 아래 표의 **패턴 A를 전면 채택**(채팅 예외 없음)으로 확정했다:

| | 패턴 A: 모든 요청 FastAPI 경유 | 패턴 B: 클라이언트가 supabase-js로 DB 직접 접속 |
|---|---|---|
| 인증 | FastAPI가 JWT 검증 후 처리 | RLS가 JWT 기반 행 단위 보호 |
| 권한 경계 | **앱 레벨**(FastAPI 코드) | **DB 레벨**(RLS 정책) |
| Phase 2 이관 | **거의 그대로** Railway PG로 전환 | RLS를 앱 레벨로 전부 재작성 필요 |
| 개발 속도 | 보일러플레이트 ↑ | 빠름(BaaS 직접) |

**결정적 사실:** FastAPI가 **service_role 키**로 Supabase에 접속하면 **RLS를 항상 우회**(BYPASSRLS)한다. 즉 패턴 A를 택하면 RLS는 사실상 무력화되고 권한은 FastAPI가 책임진다. 두 방식을 섞으면 보안 경계가 모호해진다. 🟢

**권고 (PRD 핵심 결정):** **패턴 A(FastAPI 단일 경유) 채택**. 이유 — ① idea.md가 이미 "통합 API"를 명시, ② Phase 2 Railway 이관 시 권한 로직이 앱에 있어 **이관 비용 최소화**, ③ 3개 클라이언트(고객/고수/관리자)의 서로 다른 권한을 한 곳에서 관리. RLS는 "service_role 키 유출 시 무방비"이므로 service_role 키는 **FastAPI 서버 환경변수에만** 보관, 클라이언트 노출 절대 금지. 🟢
_Source: [Service role bypasses RLS](https://supabase.com/docs/guides/troubleshooting/why-is-my-service-role-key-client-getting-rls-errors-or-not-returning-data-7_1K9z), [Securing your API](https://supabase.com/docs/guides/api/securing-your-api)_

### API 설계 패턴 (API Design Patterns)

- **REST(FastAPI) 채택 적합.** MVP 범위(가입/요청/견적/채팅)는 REST로 충분. gRPC/GraphQL은 과잉. 🟢
- **BFF(Backend for Frontend) 고려:** 고객/고수 앱 vs 관리자 웹은 요구 페이로드가 다름(모바일=경량, 관리자=리치/필터링). 단 MVP에선 **단일 API + 역할별 엔드포인트/응답 분기**로 시작하고, BFF 분리는 Post-MVP로. (BFF는 Netflix/SoundCloud가 다중 클라이언트 위해 도입한 검증된 패턴) 🟡
_Source: [BFF Pattern (AWS)](https://aws.amazon.com/blogs/mobile/backends-for-frontends-pattern/), [BFF Pattern (Azure)](https://learn.microsoft.com/en-us/azure/architecture/patterns/backends-for-frontends)_

### 통신 프로토콜 (Communication Protocols)

- **HTTP/REST:** 일반 CRUD(가입·요청·견적). 🟢
- **채팅(MVP):** WebSocket 미사용. **REST + HTTP 폴링**(GET 신규 메시지 / POST 전송). 전 경로를 일반 REST로 통일. 🟢
- **데이터 포맷:** JSON 표준. 🟢

> ✅ 일관성 확보: 전 경로 패턴 A(FastAPI 단일 경유) + **전 경로 REST**(별도 실시간 프로토콜 0) → 스택·배포 최소. Phase 2 이관 시 채팅 코드 변경 불필요.

### 인증/인가 통합 (Auth Integration)

- **흐름 (FastAPI 자체 인증):** 클라이언트 → **FastAPI `/auth/login`** 호출 → FastAPI가 `users` 테이블 조회·Argon2 검증 후 **JWT 발급** → 이후 모든 호출에 `Authorization: Bearer <jwt>` → **FastAPI `Depends`로 검증**(HS256). 🟢
- **권한 검사:** JWT의 `user_role` 클레임으로 FastAPI 라우트에서 고객/고수/관리자 분기. 🟢
- **refresh:** access 토큰 만료 시 refresh 토큰으로 재발급 엔드포인트 제공. 🟢
_Source: [FastAPI OAuth2+JWT 공식](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [FastAPI JWT Auth (Neon)](https://neon.com/guides/fastapi-jwt)_

### 시스템 상호운용성 / Phase 2 이관 관점 (Interoperability)

- **DB 접근 (지침 반영):** 종속 회피를 위해 Phase 1부터 **SQLAlchemy/asyncpg로 표준 PostgreSQL 접속**을 권장(supabase-py도 가능하나 굳이 쓸 이유 없음). Supabase는 순수 PostgreSQL 인스턴스로만 취급 → Phase 2는 **연결 문자열(DATABASE_URL)만 Railway로 교체**. 🟢
- **이관 시 변경 대상:** 사실상 **DATABASE_URL 환경변수 + 확장 설치 확인**뿐. Auth/Realtime/Storage는 애초에 FastAPI 소유라 변경 없음. 마이그레이션 데이터는 `supabase db dump`(또는 표준 pg_dump, 내부 스키마 미사용 시 가능)로 이전. 🟢

_Source: [Restore Platform to Self-Hosted](https://supabase.com/docs/guides/self-hosting/restore-from-platform), [supabase-py](https://github.com/supabase/supabase-py)_

---

## Architectural Patterns and Design

### 시스템 아키텍처 패턴 (System Architecture)

사용자 지침에 따른 **FastAPI 단일 게이트웨이 + 순수 PostgreSQL** 구조. MVP는 모듈러 모놀리식(단일 FastAPI 앱, 도메인별 모듈)으로 시작 — 마이크로서비스는 과잉. 🟢

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ 고객/고수    │   │  관리자 웹   │   │ 모바일 앱    │
│ 웹(Next.js) │   │  (Next.js)  │   │ (RN/Expo)   │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │   REST(JSON) — 채팅도 REST 폴링     │
       └────────────────┼──────────────────┘
                        ▼
              ┌───────────────────────┐
              │   통합 API (FastAPI)   │  ← 인증/권한/채팅 전부 소유
              │  router→service→repo  │
              └───────────┬───────────┘
                          │ SQLAlchemy/asyncpg (DATABASE_URL)
                          ▼
        Phase 1: Supabase(PostgreSQL)  →  Phase 2: Railway(PostgreSQL)

   ※ 파일 스토리지는 MVP 범위 제외 (Post-MVP: Cloudflare R2)
   ※ 채팅 = WebSocket 없이 HTTP 폴링 (Redis/실시간 인프라 불필요)
```

_Source: [Clean FastAPI Architecture](https://medium.com/@hadiyolworld007/%EF%B8%8F-clean-fastapi-architecture-in-real-projects-the-complete-blueprint-48e9d80292cc), [FastAPI Project Structure 2026](https://www.zestminds.com/blog/fastapi-project-structure/)_

### 설계 원칙 (Design Principles) — 이관 비용을 좌우하는 핵심

- **계층 분리 (router → service → repository):** HTTP 라우팅 / 비즈니스 로직 / DB 접근을 분리. **repository 계층이 DB 종속을 한 곳에 가둠** → 이관 시 영향 최소화. 단, MVP는 과설계 금지(폴더 10개부터 만들지 말 것) — 필요할 때 추가. 🟢
- **DB 추상화 = 이관 안전판:** SQLAlchemy ORM + **Alembic 마이그레이션**으로 스키마를 **코드로 버전 관리**. → Phase 2 Railway에서 `alembic upgrade head` 한 번이면 동일 스키마 재생성, 데이터는 `pg_dump`로 이전. 🟢
- **파일 스토리지: MVP 범위 제외 (⚡사용자 지침 — Post-MVP).** 파일 업로드 기능을 MVP에서 사용하지 않으므로 스토리지 계층 자체를 두지 않는다(R2·S3·볼륨 모두 불필요). 추후 도입 시 **S3 호환 Cloudflare R2(egress 무료)** 권장 — FastAPI에 storage 인터페이스만 추가하면 됨. 🟢
_Source: [FastAPI×Clean Architecture](https://blog.greeden.me/en/2025/12/23/practical-fastapi-x-clean-architecture-guide-growing-a-maintainable-api-with-router-splitting-a-service-layer-and-the-repository-pattern/), [Alembic for FastAPI](https://medium.com/@vamshimohan.b/alembic-for-fastapi-and-sqlalchemy-the-complete-guide-to-database-migrations-with-real-examples-c4b167d8b2bd)_

### 모노레포 아키텍처 (Monorepo Layout)

Turborepo 기준 권장 레이아웃:

```
gosoom/
├─ apps/
│  ├─ user-web/      (Next.js — 고객/고수)
│  ├─ admin-web/     (Next.js — 관리자)
│  ├─ mobile/        (Expo/React Native — 고객/고수)
│  └─ api/           (FastAPI — 통합 API)  ※ Python은 Turbo 외부, 별도 관리도 가능
├─ packages/
│  ├─ api-client/    (TS — FastAPI 호출 클라이언트, 3개 앱 공유)
│  ├─ types/         (TS — 공유 타입/DTO)
│  ├─ ui/            (공유 UI, RN Web 호환)
│  └─ config/        (eslint/tsconfig 등)
└─ turbo.json
```

- JS/TS 앱 3개는 Turborepo로 타입·API클라이언트·UI 공유(웹↔모바일 최대 90%). 🟢
- **FastAPI(Python)는 Turborepo 캐싱 대상이 아님** → `apps/api`에 두되 빌드/배포는 별도 파이프라인. 모노레포에 함께 두는 건 형상관리·일관성 목적. 🟡
_Source: [Turborepo+RN+Next 2025](https://medium.com/better-dev-nextjs-react/setting-up-turborepo-with-react-native-and-next-js-the-2025-production-guide-690478ad75af), [create-t3-turbo](https://starterpick.com/guides/create-t3-turbo-review-2026)_

### 데이터 / 보안 아키텍처

- **권한:** RLS 미사용(지침). 모든 권한 검사는 FastAPI service 계층 — JWT `user_role` 기반. 고수는 본인 견적/채팅만, 고객은 본인 요청만, 관리자는 전체. 🟢
- **시크릿 관리:** JWT 시크릿·DB 비밀번호·R2 키 전부 Railway/서버 환경변수. 클라이언트 노출 0. 🟢
- **데이터 모델 핵심 엔티티(예상):** `users`(role 포함) · `service_requests` · `quotes` · `chat_rooms` · `messages` · `categories`. 🟡

### 배포 / 운영 아키텍처 (Deployment Topology)

| 서비스 | Phase 1 | Phase 2 |
|--------|---------|---------|
| user-web / admin-web | Railway (또는 Vercel) | 동일 |
| FastAPI | Railway 서비스 | 동일 |
| PostgreSQL | **Supabase** | **Railway PostgreSQL** |
| 파일 스토리지 | ❌ MVP 제외 (Post-MVP: R2) | — |
| 채팅 실시간 인프라 | ❌ 불필요 (HTTP 폴링) | — |
| 모바일 | Expo Go(시연) → EAS Build | 동일 |

- Railway에 Next.js+FastAPI+PostgreSQL 배포하는 **공식 풀스택 스타터**가 존재해 토폴로지 검증됨. 🟢
- **Phase 1→2 전환 절차:** ① Railway PostgreSQL 프로비저닝 → ② 확장 확인 → ③ `alembic upgrade head` 또는 `pg_dump | psql`로 데이터 이전 → ④ FastAPI `DATABASE_URL` 교체·재배포. **앱 코드 변경 없음.** 🟢
- **확장 트리거:** 채팅 폴링 부하가 커지거나 실시간성이 요구될 때에만 SSE/WebSocket(+필요 시 Redis) 도입. MVP에선 불필요. 🟢
_Source: [Railway Next.js+FastAPI Starter](https://railway.com/deploy/nextjs-fastapi-full-stack-starter), [Railway PostgreSQL](https://docs.railway.com/databases/postgresql), [Restore to Self-Hosted](https://supabase.com/docs/guides/self-hosting/restore-from-platform)_

---

## Implementation Approaches and Technology Adoption

### 기술 채택 전략 (2단계 점진 이관)

idea.md의 "Phase 1 BaaS → Phase 2 인프라 독립"은 검증된 **점진적 이관(strangler) 전략**. 단, 사용자 지침으로 BaaS 종속을 처음부터 차단했으므로 실제로는 **"Supabase를 호스팅 Postgres로만 쓰다가 Railway Postgres로 갈아끼우는"** 단순 전환이 된다. 빅뱅 위험 없음. 🟢

### 개발 워크플로우 / 통합 함정 (Dev Workflow & Gotchas)

- **CORS:** Next.js(`localhost:3000`)↔FastAPI는 오리진이 달라 **FastAPI에 `CORSMiddleware` 필수**. JWT를 헤더로 보내면 `allow_credentials` 불필요. 운영에선 `allow_origins=["*"]` 금지, 도메인 명시. 🟢
- **Expo Go 시연 함정:** 실기기 Expo Go는 **PC와 같은 Wi-Fi** 필요 + `localhost` 안 됨 → API 주소를 **PC의 LAN IP** 또는 **배포된 Railway URL**로 지정해야 함. 시연은 Railway 배포 API를 가리키는 게 가장 안정적. 🟢
- **환경설정:** `NEXT_PUBLIC_API_URL` / Expo `EXPO_PUBLIC_API_URL`로 API 베이스 URL 주입, 로컬·배포 분리. 🟡
_Source: [FastAPI+Next.js CORS](https://medium.com/@saveriomazza/understanding-next-config-js-and-fastapi-cors-configuration-fb654a4c555c), [Expo 실기기+로컬백엔드](https://dev.to/katkelly/running-your-react-native-expo-app-on-a-device-with-local-backend-k8l), [Expo testing on devices](https://docs.expo.dev/guides/testing-on-devices)_

### 테스트 / 품질 (Testing & QA)

- **FastAPI:** `pytest` + `httpx.AsyncClient`(async 엔드포인트) + `app.dependency_overrides`로 `get_db`를 테스트 세션으로 교체, 트랜잭션 롤백으로 DB 청결 유지. 핵심 플로우(가입·요청·견적·채팅) 위주 API 테스트부터. 🟢
- **CI:** GitHub Actions에서 PR마다 `pytest` 실행, 커버리지 목표 ~80%. MVP는 핵심 경로만 우선. 🟢
_Source: [FastAPI Testing 공식](https://fastapi.tiangolo.com/tutorial/testing/), [FastAPI 테스트 전략](https://blog.greeden.me/en/2025/11/04/fastapi-testing-strategies-to-raise-quality-pytest-testclient-httpx-dependency-overrides-db-rollbacks-mocks-contract-tests-and-load-testing/)_

### 배포 / 운영 (Deployment & Ops)

- Railway에 GitHub 연동 → push 시 자동 빌드/배포. FastAPI는 Dockerfile 또는 자동 감지. 🟢
- 서비스 분리: `api`(FastAPI), `user-web`, `admin-web`, `postgres`. 환경변수는 Railway가 `DATABASE_URL` 등 자동 주입. 🟢
- 모바일은 시연 = Expo Go, 배포 필요 시 EAS Build. 🟢
_Source: [Deploy FastAPI on Railway](https://docs.railway.com/guides/fastapi), [Deploy Next.js on Railway](https://docs.railway.com/guides/nextjs)_

### 비용 / 리소스 (Cost)

- **MVP 비용 ≈ $0~$25/월.** Supabase 무료(주의: 1주 비활성 시 일시정지, 시연 전 깨우기) + Railway 무료/소액 크레딧. 스택 최소화로 Redis·스토리지 비용 없음. 🟢
_Source: [Supabase Pricing](https://supabase.com/pricing), [Railway PostgreSQL](https://docs.railway.com/databases/postgresql)_

### 리스크 평가 및 완화 (Risk Assessment)

| 리스크 | 영향 | 완화책 | 등급 |
|--------|------|--------|------|
| Supabase 무료 1주 일시정지 | 시연 직전 DB 다운 | 시연 전 쿼리 1회로 깨우기(~30초), 또는 Pro/Railway 조기 전환 | 🟢 |
| 폴링 채팅 부하/지연 | 사용자 많을 때 비효율 | MVP 규모엔 무problem, 폴링 간격 조절, 추후 SSE/WS 업그레이드 | 🟢 |
| 모노레포 학습곡선 | 초기 셋업 지연 | 검증된 스타터(create-t3-turbo) 차용 | 🟡 |
| 자체 인증 보안 취약 | 토큰/비밀번호 노출 | Argon2 해싱, 짧은 access+refresh, 시크릿 서버 전용, HTTPS | 🟡 |
| Phase 2 이관 데이터 정합성 | 이관 중 데이터 손실 | 테스트 인스턴스 선검증, Alembic 스키마 재현 + pg_dump 데이터, 점검창 | 🟢 |

---

## Technical Research Recommendations

### ✅ 최종 기술 스택 권고 (PRD 반영용)

| 영역 | 권고 | 비고 |
|------|------|------|
| 사용자/관리자 웹 | **Next.js** (App Router) | idea.md 그대로 |
| 모바일 | **React Native + Expo** (SDK 52+) | 시연 Expo Go |
| API | **FastAPI** (router→service→repository) | 인증·권한·채팅 전부 소유 |
| 인증 | **FastAPI 자체 JWT** (users 테이블, Argon2, HS256) | Supabase Auth ✗ |
| 채팅 | **REST + HTTP 폴링** | WebSocket ✗, Redis ✗ |
| DB 접근 | **SQLAlchemy + Alembic** | 표준 PG 접속 |
| DB(호스팅) | Phase1 **Supabase** → Phase2 **Railway PostgreSQL** | 연결문자열만 교체 |
| 모노레포 | **Turborepo** (JS 앱 3개 공유) | FastAPI는 별도 |
| 배포 | **Railway** (FE/BE/PG) | 공식 스타터 검증 |
| 파일 스토리지 | **MVP 제외** (Post-MVP: R2) | 사용자 지침 |
| Redis / 실시간 인프라 | **MVP 제외** | 사용자 지침(스택 최소화) |

### 🗺️ 구현 로드맵 (권장 순서)

1. **기반:** Turborepo 셋업 + 공유 `types`/`api-client` 패키지 + FastAPI 스켈레톤(router→service→repo) + Supabase 연결 + Alembic 초기 마이그레이션.
2. **인증:** users 테이블 + 회원가입/로그인(고객·고수·관리자 role) + JWT 발급/검증 + `Depends` 권한 가드.
3. **핵심 도메인:** 카테고리 → 서비스 요청(고객) → 요청 확인/견적 제안(고수) → 견적 확인(고객).
4. **채팅:** `chat_rooms`/`messages` 테이블 + REST 전송/폴링 수신.
5. **관리자:** 고객/고수/관리자 관리 + 요청 관리 + 채팅 내역 확인.
6. **클라이언트:** user-web → mobile(Expo) → admin-web 순, 공유 api-client 재사용.
7. **이관(Phase 2):** Railway PG 프로비저닝 → `alembic upgrade head` + `pg_dump` → `DATABASE_URL` 교체.

### 🎯 핵심 의사결정 요약 (PRD가 명시해야 할 것)

1. Supabase는 **DB 전용**, 나머지 기능 전부 FastAPI 소유 → **이관 = 환경변수 교체**.
2. 채팅 = **HTTP 폴링**(WebSocket/Redis 없음) → 스택 최소.
3. 인증 = **FastAPI 자체 JWT**(Supabase Auth 미사용).
4. 파일 업로드 = **MVP 범위 제외**(Post-MVP).
5. 권한 = **앱 레벨**(RLS 미사용), JWT `user_role` 기반.

### 필요 역량 (Skills)

TypeScript/React(Next.js·RN), Python/FastAPI, SQL/PostgreSQL(SQLAlchemy·Alembic), 모노레포(Turborepo), Railway 배포. 🟡

### 성공 지표 (MVP KPI)

3개 역할 가입~채팅 E2E 플로우 동작 · 시연 환경 안정 기동 · Phase 2 이관이 앱 코드 변경 없이 완료 · 핵심 API 테스트 통과. 🟡

---

# Research Synthesis — 숨고형 MVP 기술 스택 종합 타당성

## Executive Summary (임원 요약)

양면 마켓플레이스 MVP의 성패는 "단일 거래(요청→견적→소통)를 완결하는 최소 인프라"를 얼마나 빠르고 견고하게 세우느냐에 달려 있다. 본 리서치는 idea.md의 스택(Next.js·React Native/Expo·FastAPI·Supabase/PostgreSQL·Railway)이 2026년 기준 **전부 검증된 조합**임을 확인했고, Railway 공식 풀스택 스타터로 배포 토폴로지까지 입증했다.

리서치 도중 확정된 사용자 지침 — **"Supabase는 DB로만, 나머지 기능은 전부 FastAPI 소유"** — 이 설계를 관통하는 원칙이 되었다. 이 원칙은 흔히 BaaS MVP가 겪는 "Phase 2 탈(脫)종속 시 Auth·Realtime·RLS 전면 재구현" 함정을 **사전에 제거**한다. 그 결과 채팅은 HTTP 폴링(WebSocket·Redis 불필요), 인증은 FastAPI 자체 JWT(Argon2+HS256), 파일 업로드는 MVP 제외, 권한은 앱 레벨로 정리되어, 전체 기술 스택이 **REST + PostgreSQL** 중심으로 최소화됐다.

종합 판정: **기술 타당성 높음(🟢), 이관 리스크 낮음(🟢).** Phase 2 Railway 이관은 SQLAlchemy+Alembic 채택을 전제로 "DATABASE_URL 교체 + 데이터 덤프" 수준으로 떨어진다. PRD는 아래 5대 결정을 기술 제약으로 명문화하면 된다.

**Key Technical Findings:**
- idea.md 스택은 2026 검증 조합 + Railway 공식 스타터로 토폴로지 입증 🟢
- FastAPI가 service_role로 접속하면 RLS는 우회됨 → "API 단일 경유"와 RLS 병행은 무의미. 권한은 앱 레벨로 일원화가 정합적 🟢
- 채팅은 폴링으로 "WebSocket 효용 80%를 복잡도 20%"에 확보, MVP에 충분 🟢
- BaaS 종속을 처음부터 차단하면 이관 비용이 "재구현"→"환경변수 교체"로 급감 🟢
- Supabase 무료 티어는 1주 비활성 시 자동 일시정지(2026-02 변경) → 시연 운영 주의 🟢

**Technical Recommendations (Top 5):**
1. **Supabase=순수 PostgreSQL**, 인증·채팅·(차후)스토리지 전부 FastAPI 소유.
2. **채팅 = REST + HTTP 폴링** (WebSocket·Redis 미도입).
3. **인증 = FastAPI 자체 JWT** (users 테이블, Argon2, access+refresh).
4. **SQLAlchemy + Alembic** 채택 → 이관을 환경변수 교체 수준으로.
5. **Turborepo**로 JS 앱 3개 공유, **Railway** 배포. 파일 업로드·실시간 인프라는 Post-MVP.

## Table of Contents

1. 기술 리서치 범위 확정 (Scope Confirmation)
2. 기술 스택 분석 (Technology Stack) — 4개 주제별 타당성
3. 통합 패턴 분석 (Integration Patterns) — API 경유 원칙·인증·이관
4. 아키텍처 패턴 (Architecture) — 시스템 구조·모노레포·배포 토폴로지
5. 구현 접근법 (Implementation) — 워크플로우·테스트·리스크·로드맵
6. 종합 (this section) — 임원 요약·결론·다음 단계

## 1. 서론 및 방법론 (Introduction & Methodology)

한국 "숨고"류 서비스는 고객의 서비스 요청과 검증된 고수의 견적 제안을 잇는 양면 마켓플레이스다. MVP의 본질은 화려한 기능이 아니라 **요청→견적→소통의 거래 루프 한 바퀴**를 안정적으로 완결하는 것이다. 본 리서치는 그 거래 루프를 떠받칠 기술 토대를, "최소 기능·최소 스택·이관 용이성"이라는 제약 아래 검증했다.

- **범위:** 4개 핵심 주제(실시간 채팅·3-role 인증·Supabase→Railway 이관·코드 공유 모노레포)를 5개 관점(아키텍처·구현·스택·통합·성능)으로 횡단.
- **데이터 출처:** 2026년 현재 공식 문서(Supabase·FastAPI·Expo·Railway·Cloudflare) + 기술 비교 글, 핵심 주장은 다중 출처 교차 검증.
- **방법:** 단계별 병렬 웹검색 → 신뢰도 등급(🟢/🟡/🔴) 부여 → PRD 의사결정 권고로 환원.
- **달성:** 4개 주제 모두 타당성·권고·리스크·완화책 도출. 추가로 "API 경유 vs BaaS 직접" 핵심 결정과 service_role의 RLS 우회 함정을 발굴.

_Source: [Marketplace MVP 개발 가이드](https://www.elevenx.asia/post/the-definitive-guide-to-marketplace-mvp-development-for-startups), [On-Demand Marketplace 로드맵](https://www.synergylabs.co/blog/on-demand-app-development-a-roadmap-for-building-scalable-marketplaces)_

## Technical Research Conclusion

### 핵심 결론
idea.md의 기술 방향은 타당하다. 사용자 지침으로 "Supabase=DB 전용" 원칙을 확정함으로써, 본 프로젝트는 BaaS MVP의 최대 약점(이관 비용)을 설계 시점에 제거했다. 채팅·인증·권한을 모두 FastAPI로 일원화한 결과, 스택은 최소화되고 이관은 단순화된다.

### 전략적 영향
- **시연 속도:** REST+폴링+자체JWT는 학습·디버깅이 쉬워 MVP를 빠르게 세운다.
- **이관 안전:** SQLAlchemy+Alembic 전제 시 Phase 2는 사실상 무위험.
- **확장 여지:** 채팅은 데이터 모델 변경 없이 SSE/WebSocket으로, 스토리지는 R2로 단계 확장.

### 다음 단계 (Next Steps)
1. **PRD 작성**(`bmad-prd`) — 본 리서치의 "5대 핵심 결정"을 기술 제약·비기능 요구로 명문화.
2. **UX 설계**(`bmad-ux`) — 3-role 화면 흐름.
3. **아키텍처 문서화**(`bmad-create-architecture`) — 본 문서를 입력으로 솔루션 설계 확정.
4. 데이터 모델 상세화(users·service_requests·quotes·chat_rooms·messages·categories).

## Source Verification (출처 검증)
모든 기술 주장은 본문 각 섹션의 `_Source:_` 링크로 출처를 명시했다(Supabase/FastAPI/Expo/Railway/Cloudflare 공식 문서 및 2025–2026 기술 비교 자료). 신뢰도 등급: 🟢 다중 출처 확인 / 🟡 단일·제한 출처(주로 프로젝트 고유 설계 판단) / 🔴 추정. 본 문서에 🔴 항목은 없으며, 🟡는 대부분 "프로젝트 맥락에 맞춘 설계 권고"로 일반 사실이 아닌 판단 영역이다.

---

**Technical Research Completion Date:** 2026-06-07
**Source Verification:** 모든 핵심 사실 현재 출처로 인용
**Technical Confidence Level:** High — 복수 권위 출처 기반

_본 문서는 gosoom MVP 기술 의사결정의 권위 있는 참조 자료이며, 후속 PRD·아키텍처 작업의 입력으로 사용된다._
