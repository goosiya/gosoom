---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - '_bmad-output/planning-artifacts/prds/prd-gosoom-2026-06-07/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/prds/prd-gosoom-2026-06-07/addendum.md'
---

# gosoom - Epic Breakdown

## Overview

이 문서는 gosoom의 완전한 에픽·스토리 분해를 제공한다. PRD(FR/NFR)와 Architecture(기술 결정·구조·패턴), Addendum(기술 결정 근거·수동 설정 체크포인트)의 요구사항을 구현 가능한 스토리로 분해한다. 별도 UX 설계 문서는 없으며, UI 패턴은 Architecture의 Frontend 섹션을 따른다.

## Requirements Inventory

### Functional Requirements

**인증 & 계정 (Auth & Accounts)**
- **FR1:** 신규 사용자는 역할(고객 또는 고수)을 선택하여 이메일+비밀번호로 회원가입할 수 있다. 관리자 계정은 자가 가입 불가 — 초기 관리자 1개는 시스템 시드로 제공되고, 이후 관리자는 기존 관리자만 추가할 수 있다(FR21).
- **FR2:** 사용자는 이메일+비밀번호로 로그인/로그아웃할 수 있다.
- **FR3:** 로그인 세션은 일정 시간 유지되며, 만료 시 재인증 없이 갱신(refresh)된다.
- **FR4:** 모든 기능은 사용자 역할에 따라 접근이 제어된다(고객=본인 요청/견적/채팅, 고수=본인 견적/채팅, 관리자=전체).

**고객 — 서비스 요청 (Customer · Service Requests)**
- **FR5:** 고객은 카테고리, 지역, 요청 내용(설명)을 포함한 서비스 요청을 생성할 수 있다(선택: 희망 일정·예산, 단일 카테고리).
- **FR6:** 고객은 자신이 생성한 요청의 목록과 상세를 조회할 수 있다.
- **FR7:** 서비스 요청은 상태를 가진다: `open` → `matched` → `completed` / `cancelled`. 고객은 자신의 요청을 취소할 수 있고, 거래 종료 시 완료 처리할 수 있다. `matched`는 견적 수락(FR13) 시 자동 전환된다.
- **FR8:** 고객은 자신의 요청에 들어온 견적 목록을 조회하고, 각 견적의 가격·메시지·고수 정보(고수 **표시명** + 해당 고수의 활동 카테고리)를 비교할 수 있다.

**고수 — 카테고리 & 견적 (Pro · Categories & Quotes)**
- **FR9:** 고수는 자신의 활동 카테고리를 설정/변경할 수 있다(복수 카테고리 선택 가능).
- **FR10:** 고수는 자신의 활동 카테고리와 일치하는 서비스 요청 목록과 상세를 열람할 수 있다. `matched` 상태가 된 요청은 목록에서 제외되지 않고 비활성 상태로 표시되어, 더 이상 견적을 제안할 수 없다.
- **FR11:** 고수는 `open` 상태의 요청에 가격과 제안 메시지를 담아 견적을 제안할 수 있다(한 요청에 고수당 1개의 견적).
- **FR12:** 고수는 자신이 제안한 견적의 목록과 상태(`pending/accepted/rejected/closed`)를 조회할 수 있다.

**매칭 — 견적 수락/거절 (Matching · Quote Acceptance/Rejection)**
- **FR13:** 고객은 받은 견적 중 하나를 수락할 수 있다. 수락 시 ① 요청 상태가 `matched`로 전환, ② 고객-고수 사이 채팅방 생성, ③ 동일 요청의 다른 `pending` 견적은 `closed`로 전환(정보 보존). 한 요청은 하나의 견적만 수락한다.
- **FR14:** 고객은 받은 견적을 명시적으로 거절할 수 있다. 거절된 견적은 `rejected` 상태로 표시되며, 고수의 견적 목록(FR12)에도 반영된다. 거절은 개별 견적 단위이며, 요청 상태(open)는 변하지 않는다.

**채팅 (Chat)**
- **FR15:** 수락된 견적을 기준으로 고객과 고수 사이에 1:1 채팅방이 존재한다.
- **FR16:** 채팅방 참여자(고객·고수)는 텍스트 메시지를 전송할 수 있다.
- **FR17:** 채팅방 참여자는 새 메시지를 수신·확인할 수 있다(약 2~3초 폴링으로 신규 메시지 갱신, 실시간 인프라 없음).
- **FR18:** 고객·고수는 자신이 참여 중인 채팅방 목록을 조회할 수 있다.

**관리자 (Admin)**
- **FR19:** 관리자는 고객 계정 목록·상세를 조회하고 계정을 비활성화/재활성화할 수 있다. 비활성화 계정은 로그인 및 신규 거래 활동(요청 생성·견적 제안·채팅 전송)이 차단되며, 기존 데이터는 유지(소프트 비활성화).
- **FR20:** 관리자는 고수 계정 목록·상세를 조회하고 계정을 비활성화/재활성화할 수 있다(차단·데이터 유지 규칙은 FR19와 동일).
- **FR21:** 관리자는 관리자 계정 목록을 조회하고, 신규 관리자를 추가하거나 기존 관리자를 비활성화할 수 있다(시드 관리자는 비활성화 대상에서 제외하여 잠금 방지).
- **FR22:** 관리자는 전체 서비스 요청 목록·상세·상태를 조회할 수 있고, 요청 상태를 변경하거나 부적절한 요청을 숨김 처리(소프트 삭제)할 수 있다(연결된 견적·채팅은 보존).
- **FR23:** 관리자는 채팅방과 메시지 내역을 열람할 수 있다(읽기 전용 — 전송·수정 불가).
- **FR24:** 관리자는 서비스 카테고리를 생성·수정·삭제할 수 있다(사용 중 카테고리는 비활성화만 가능, 물리 삭제 차단).

### NonFunctional Requirements

- **NFR1. 폼팩터/플랫폼:** 고객/고수용 반응형 웹, 관리자용 반응형 웹, 고객/고수용 모바일 앱(iOS/Android) — 총 3개 클라이언트. 모바일 시연은 Expo Go.
- **NFR2. 언어/현지화:** UI·콘텐츠는 한국어 기준.
- **NFR3. 보안:** 비밀번호 해싱 저장(평문 미보관), 토큰 기반 인증, 모든 권한 검사는 서버 수행, 서버 시크릿 비노출, HTTPS 통신.
- **NFR4. 권한 일관성:** 권한 경계는 애플리케이션(API) 레벨에서 단일 관리되어 3개 클라이언트가 동일 규칙을 따른다.
- **NFR5. 성능:** 일반 CRUD는 체감 지연 없이 동작. 채팅 폴링 주기는 부하·즉시성 균형(과도한 요청 금지).
- **NFR6. 이식성/이관 용이성:** Phase 1(개발)→Phase 2(인프라 독립) DB 이관이 애플리케이션 기능 코드 변경 없이 가능해야 한다.
- **NFR7. 데이터 무결성:** 거래 핵심 데이터(요청·견적·채팅·계정)는 손실 없이 보존, 상태 전이는 일관성 유지.
- **NFR8. 시연 안정성:** 데모 환경은 사전 점검 절차로 시작 시점에 안정적으로 기동(예: 데모 직전 DB 깨우기).
- **NFR9. 확장성(설계 여지):** 채팅은 데이터 모델 변경 없이 추후 실시간 방식으로 업그레이드 가능한 여지를 남긴다(과설계 금지).
- **NFR10. 데이터 보존/용량 인지:** 비활성 계정 데이터 유지(FR19)와 채팅 누적으로 데이터 단조 증가. 저장 용량 한도(Supabase 무료 티어 500MB 등) 인지, 한도 임박 시 유료 전환 또는 Phase 2 이관 대응.

### Additional Requirements

Architecture·Addendum에서 도출한, 에픽·스토리 구현에 직접 영향을 주는 기술 요구사항:

**기반/스캐폴드**
- **AR1. Composed Scaffold(첫 구현 스토리):** 단일 올인원 스타터 없음 — 의도적 조합형 스캐폴드. `create-turbo`로 Turborepo 골격 + `create-next-app`(user-web, admin-web) + `create-expo-app`(mobile, SDK 55 핀) + FastAPI 수동 스켈레톤(router→service→repository) + 공유 패키지(types, api-client, ui, config). Metro 설정은 Vercel `with-react-native-web` 예제 배선 참조.
- **AR2. React 버전 정렬(G5):** 스캐폴드 시점에 Next.js 16(React 19.2)과 Expo SDK 55의 React 버전 호환을 점검, 공유 `packages/ui`의 단일 React 해석 보장(필요 시 SDK 55 지원 React로 정렬).

**데이터 계층**
- **AR3. DB 접근 계층:** SQLAlchemy 2.0(async + asyncpg) + Alembic. repository 계층으로 DB 격리(NFR6). 모든 조회는 `deleted_at IS NULL` 공통 필터.
- **AR4. UUIDv7 앱측 생성(G4):** PK는 UUIDv7. Supabase는 PG17이라 네이티브 `uuidv7()` 미지원 → DB DEFAULT 금지, Python `uuid7` 라이브러리로 앱 측 생성(이관 시 확장 의존성 회피).
- **AR5. 시드 데이터:** 초기 관리자 1개(FR1/FR21) + 기본 카테고리는 Alembic data migration/seed 스크립트로 제공.
- **AR6. 데이터 모델 세부 확정(G1-G3):** ① 고수↔카테고리 M:N 조인 테이블(`pro_categories`), ② `chat_rooms` 관계 컬럼(`service_request_id`, `customer_id`, `pro_id`, `quote_id`), ③ `messages` 발신자 식별(`sender_id`+role)과 증분 폴링 정렬 키 — 첫 데이터 모델링 스토리에서 컬럼 수준 확정.
- **AR7. FR13 동시성 안전:** `SELECT ... FOR UPDATE`(요청 행 잠금) + `service_request_id`당 "accepted 견적 1개" partial unique index(`uq_quotes_accepted_per_request`)로 동시 수락 race 차단. 단일 트랜잭션 내 3-step 처리.

**API/통합**
- **AR8. REST 단일 경유(패턴 A):** 모든 클라이언트는 FastAPI `/api/v1`만 경유, DB 직접 접속 금지. RLS 미사용(앱 레벨 권한 일원화).
- **AR9. Orval 코드 생성:** FastAPI OpenAPI(`openapi.json`) → `packages/api-client`에 TS 타입 + TanStack Query 훅 자동 생성. 생성물 수동 수정 금지(빌드 아티팩트). operationId 안정화.
- **AR10. Bearer 헤더 통일:** 웹·모바일 모두 `Authorization: Bearer <jwt>`. access=메모리, refresh=웹 저장소/모바일 Expo SecureStore. api-client 단일 인터셉터(401→refresh 1회→재요청).
- **AR11. JWT/인증:** HS256, payload `{user_id, user_role, exp}`, access 15~30분 + refresh 7~30일. Argon2(pwdlib) 해싱. service 계층 소유권 검사.
- **AR12. 에러 envelope 표준:** `{code, message, detail?}` + 적절한 HTTP status. 목록 응답=`{items, nextCursor}`(cursor 페이지네이션). 날짜=ISO 8601 UTC, 금액=정수 KRW.
- **AR13. 채팅 폴링 계약:** 송신 `POST /api/v1/chat-rooms/{id}/messages`, 수신 `GET .../messages?after=<lastId>`(증분). 클라이언트 TanStack Query `refetchInterval` 2~3초, 페이로드 최소화(CM1).
- **AR14. CORS:** FastAPI `CORSMiddleware`에 명시 오리진 등록(웹↔API 오리진 상이, 운영 `*` 금지).

**프론트엔드**
- **AR15. 서버 상태 관리:** TanStack Query v5 단일 소스(폴링=refetchInterval, 캐시·무효화 일원화). 클라이언트 상태 최소화.
- **AR16. 스타일:** Tailwind(웹) + NativeWind(모바일) + 공유 `packages/ui`(RN Web 호환 프리미티브).
- **AR17. 라우트 가드:** App Router 레이아웃/미들웨어에서 역할 기반 가드(UX 보조), 권한 최종 시행은 서버.
- **AR18. 환경변수 주입:** `NEXT_PUBLIC_API_URL` / `EXPO_PUBLIC_API_URL`로 API 베이스 주입. Expo Go 실기기는 LAN IP 또는 배포 URL(localhost 불가).

**인프라/배포/운영**
- **AR19. Railway 배포:** `api`(FastAPI/Dockerfile), `user-web`, `admin-web`, `postgres`(Phase1=Supabase 외부/Phase2=Railway PG). 모바일=Expo Go/EAS. 시크릿=Railway 환경변수.
- **AR20. CI/CD:** GitHub Actions — PR마다 `pytest`(api) + lint/typecheck/build(JS). Railway GitHub 연동 자동 배포.
- **AR21. Phase 2 이관 절차:** Railway PG 프로비저닝 → `pg_extension` 확인 → `alembic upgrade head` + `supabase db dump` 데이터 → `DATABASE_URL` 교체·재배포. 앱 코드 변경 없음(NFR6).
- **AR22. 시연 안정 운영:** Supabase 무료 1주 비활성 일시정지 → 시연 직전 깨우기(NFR8). 용량 단조증가 인지(NFR10).
- **AR23. 수동 설정 체크포인트(⚡사용자 지침):** 각 기능 구현 진입 *전*, 사용자(KTH)가 직접 수동으로 해야 할 외부 서비스·콘솔 작업(Supabase/JWT 시크릿/Expo/Railway 등)을 먼저 구체적 단계와 함께 안내한 뒤 코드 작업 시작.

### UX Design Requirements

해당 없음 — 별도 UX 설계 문서가 존재하지 않는다. UI/인터랙션 패턴(반응형 웹, TanStack Query 로딩/에러 상태, 공유 UI 프리미티브, 한국어 UI)은 Architecture의 Frontend Architecture 및 Implementation Patterns 섹션을 단일 참조로 삼는다.

### FR Coverage Map

- **FR1:** Epic 1 — 역할 선택 회원가입(고객/고수), 관리자 시드
- **FR2:** Epic 1 — 로그인/로그아웃
- **FR3:** Epic 1 — 세션 유지·refresh 갱신
- **FR4:** Epic 1 — 역할 기반 접근 제어(RBAC) 기반
- **FR5:** Epic 2 — 서비스 요청 생성(카테고리/지역/내용)
- **FR6:** Epic 2 — 본인 요청 목록·상세 조회
- **FR7:** Epic 2 — 요청 상태(open→matched→completed/cancelled), 취소·완료
- **FR8:** Epic 4 — 받은 견적 목록 조회·비교
- **FR9:** Epic 3 — 고수 활동 카테고리 설정/변경(복수)
- **FR10:** Epic 3 — 카테고리 매칭 요청 열람(matched는 비활성 표시)
- **FR11:** Epic 3 — open 요청에 견적 제안(요청당 고수 1개)
- **FR12:** Epic 3 — 본인 견적 목록·상태 조회
- **FR13:** Epic 4 — 견적 수락(단일 트랜잭션: matched·채팅방 생성·타 견적 closed)
- **FR14:** Epic 4 — 견적 거절(개별 단위)
- **FR15:** Epic 4 — 수락 기반 1:1 채팅방
- **FR16:** Epic 4 — 텍스트 메시지 전송
- **FR17:** Epic 4 — 신규 메시지 수신(2~3초 폴링)
- **FR18:** Epic 4 — 참여 채팅방 목록 조회
- **FR19:** Epic 6 — 고객 계정 비활성화/재활성화(소프트)
- **FR20:** Epic 6 — 고수 계정 비활성화/재활성화(소프트)
- **FR21:** Epic 6 — 관리자 추가/비활성화(시드 관리자 잠금 방지)
- **FR22:** Epic 6 — 전체 요청 관리·상태 변경·숨김(소프트 삭제)
- **FR23:** Epic 6 — 채팅 내역 열람(읽기 전용)
- **FR24:** Epic 6 — 카테고리 CRUD(사용 중은 비활성화만)

> Epic 5(모바일 앱)는 신규 FR을 도입하지 않고 FR1-18의 고객·고수 플로우를 모바일 플랫폼(NFR1)으로 전달한다.

## Epic List

### Epic 1: 기반 구축, 인증 & 배포 골격
3개 역할(고객·고수·관리자)이 이메일+비밀번호로 가입·로그인할 수 있고, 그 결과물이 실제 배포 환경에서 동작한다. Composed Scaffold(모노레포+4앱 골격, `packages/ui`는 처음부터 RN-Web 호환으로 구축), DB 기반(SQLAlchemy async/Alembic, 카테고리 포함 엔티티+조회 API+시드, UUIDv7 앱측 생성), 인증(JWT/Argon2, Orval 첫 생성으로 api-client 확립), CI + 워킹 스켈레톤 첫 배포(Railway)를 포함한다. 이후 모든 에픽이 의존하는 단일 기반.
**FRs covered:** FR1, FR2, FR3, FR4
**구현 노트:** AR1-2(스캐폴드·React 버전 정렬), AR3-7(데이터 기반·UUIDv7·시드·모델 세부 G1-3 일부 착수), AR9-12(Orval·Bearer·JWT·에러 envelope), AR19-20(CI·첫 배포). ⚡AR23 수동 설정 체크포인트(Supabase/JWT 시크릿/Railway) 선안내.

### Epic 2: 고객 서비스 요청
고객이 (시드된) 카테고리를 골라 지역·내용을 담아 서비스 요청을 생성하고, 자신의 요청 목록·상세를 조회하며, 상태(open→matched→completed/cancelled)에 따라 취소·완료 처리할 수 있다. 거래 루프의 출발점.
**FRs covered:** FR5, FR6, FR7
**구현 노트:** service_requests 도메인(router→service→repository), 요청 상태 기계 service 단일 시행, 소프트 규칙. 카테고리 조회 API는 Epic 1 기반 재사용.

### Epic 3: 고수 카테고리 & 견적
고수가 활동 카테고리를 복수 설정하고, 카테고리가 일치하는 open 요청 목록·상세를 열람하며(matched 요청은 비활성 표시), 가격·메시지를 담아 견적을 제안하고 자신의 견적 목록·상태를 조회할 수 있다.
**FRs covered:** FR9, FR10, FR11, FR12
**구현 노트:** AR6 `pro_categories` M:N 조인 확정, quotes 도메인, 견적 상태 기계(pending/accepted/rejected/closed), 요청당 고수 1견적 제약.

### Epic 4: 매칭 & 채팅 (거래 루프 완결)
고객이 받은 견적을 비교하고 하나를 수락(또는 거절)하면, 수락 시 단일 트랜잭션으로 요청이 matched로 전환되고 채팅방이 생성되며 타 견적은 closed 처리된다. 이후 고객↔고수가 1:1 채팅(텍스트, 2~3초 폴링)으로 거래를 마무리한다. 제품의 핵심 가치이자 가장 위험한 트랜잭션 지점.
**FRs covered:** FR8, FR13, FR14, FR15, FR16, FR17, FR18
**구현 노트:** AR7 FR13 동시성 안전(SELECT FOR UPDATE + partial unique index), AR6 chat_rooms FK·messages 발신자/정렬 키 확정, AR13 폴링 계약. 사이징 어려울 시 매칭(FR8/13/14) | 채팅(FR15-18) 분할 여지.

### Epic 5: 모바일 앱
고객·고수가 모바일 앱(Expo SDK 55, 시연 Expo Go)에서 거래 루프(가입~요청~견적~수락~채팅)를 사용할 수 있다. 공유 `packages/api-client`(Orval)와 `packages/ui`(RN-Web 호환)를 재사용하여 user-web의 도메인 기능을 모바일로 전달한다.
**FRs covered:** (신규 FR 없음 — FR1-18의 고객·고수 플로우를 모바일 플랫폼으로 전달, NFR1)
**구현 노트:** AR10 refresh=Expo SecureStore, AR16 NativeWind, AR18 EXPO_PUBLIC_API_URL(실기기 LAN IP/배포 URL). ⚡AR23 Expo 계정·Expo Go 설정 선안내.

### Epic 6: 관리자 콘솔
운영자가 관리자 전용 웹(admin-web)에서 고객·고수·관리자 계정을 조회하고 비활성화/재활성화하며, 전체 서비스 요청을 관리(상태 변경·숨김 소프트 삭제)하고, 채팅 내역을 읽기 전용으로 열람하며, 서비스 카테고리를 CRUD(사용 중은 비활성화만)할 수 있다.
**FRs covered:** FR19, FR20, FR21, FR22, FR23, FR24
**구현 노트:** admin 라우터는 도메인 service를 역할 가드 하에 호출(로직 중복 금지), 소프트 삭제/비활성화 규칙, 시드 관리자 잠금 방지, 채팅 읽기 전용 접근.

### Epic 7: 공개 랜딩 & 브랜드 표기 (Post-MVP UX)
미인증 방문자가 user-web·mobile 진입 시 곧바로 로그인 화면이 아니라 공개 메인 랜딩을 보고, 거기서 로그인/회원가입으로 연결될 수 있다. 또한 화면에 노출되는 제품명을 `gosoom` → `meetgo`로 변경한다(코드/설정 식별자는 `gosoom` 유지).
**FRs covered:** 없음 — 신규 FR 미도입, UX 개선·브랜드 표기 변경.
**구현 노트:** 기존 PRD/FR 범위(FR1~24) 밖에서 KTH 요청으로 직접 구현(정식 create-story→dev-story 절차 없이 ad-hoc). 클라이언트 표시 텍스트·라우팅만 변경하고 패키지명(`@gosoom/*`)·env·저장소 키 등 프로그램 요소는 불변.

> **Deferred(Post-MVP):** AR21 Phase 2 이관(Railway PG)은 필요 시 별도로 수행, MVP 에픽에 포함하지 않음. 자동 계측·모니터링 고도화, 실시간 채팅, 파일 스토리지, BFF 분리 등도 Post-MVP.

## Epic 1: 기반 구축, 인증 & 배포 골격

3개 역할(고객·고수·관리자)이 이메일+비밀번호로 가입·로그인할 수 있고, 그 결과물이 실제 배포 환경에서 동작한다. 모노레포 골격, DB 기반, 인증, CI/첫 배포를 확립하여 이후 모든 에픽의 단일 기반을 제공한다.
**FRs covered:** FR1, FR2, FR3, FR4

### Story 1.1: Composed Scaffold 초기화

As a 개발 에이전트,
I want 모노레포(Turborepo)와 4개 앱(user-web, admin-web, mobile, api) 골격 및 공유 패키지를 표준 스캐폴드로 초기화하기를,
So that 이후 모든 기능을 일관된 구조·버전 위에서 구현할 수 있다.

**Acceptance Criteria:**

**Given** 빈 프로젝트 루트에서
**When** `create-turbo`로 워크스페이스를, `create-next-app`으로 user-web·admin-web를, `create-expo-app`(Expo SDK 55 핀)으로 mobile을 스캐폴드하고 apps/api에 FastAPI 스켈레톤(router→service→repository 디렉터리)을 수동 생성하면
**Then** 아키텍처 문서의 디렉터리 구조(apps/_, packages/types·api-client·ui·config)가 그대로 생성되고
**And** `pnpm-workspace.yaml`·`turbo.json`·`tsconfig.base.json`이 JS 앱들을 인식하며 `turbo build`/`turbo lint`가 통과한다.

**Given** 공유 `packages/ui`를 구성할 때
**When** RN-Web 호환 프리미티브(Button, Input, Card 등 최소 셋)를 추가하면
**Then** 웹(Next)과 모바일(Expo) 양쪽에서 import 가능한 형태로 작성되고(AR16), 모바일 에픽에서의 retrofit이 불필요하다.

**Given** Next.js 16(React 19.2)과 Expo SDK 55의 React 버전 차이(G5/AR2)가 있을 때
**When** 스캐폴드 직후 pnpm 모노레포의 React 해석을 점검하면
**Then** 공유 `packages/ui`가 단일 React로 해석되도록 정렬되고(필요 시 SDK 55가 지원하는 React로), `turbo dev`로 user-web과 mobile이 동시에 기동된다.

**Given** Expo-in-모노레포 배선이 필요할 때
**When** Vercel `with-react-native-web` 공식 예제를 참조해 mobile의 `metro.config.js`를 모노레포 인식하도록 설정하면
**Then** mobile 앱이 모노레포의 공유 패키지를 번들링 오류 없이 로드한다.

### Story 1.2: 백엔드 & DB 기반 (FastAPI + SQLAlchemy + Alembic)

As a 개발 에이전트,
I want FastAPI 앱과 비동기 DB 접근 계층(SQLAlchemy async + asyncpg), Alembic 마이그레이션, 공통 코어(설정·보안·DB·에러 envelope)를 구축하기를,
So that 이후 도메인 기능이 일관된 계층·규약 위에서 데이터에 접근할 수 있다.

**Acceptance Criteria:**

**Given** apps/api 스켈레톤에서
**When** `app/core/db.py`에 async 엔진/세션(asyncpg)과 `get_db` 의존성을, `app/core/config.py`에 pydantic-settings 기반 설정(DATABASE_URL, JWT_SECRET, CORS_ORIGINS)을 구성하면
**Then** `/api/v1` 프리픽스와 `CORSMiddleware`(명시 오리진)가 등록된 FastAPI 앱이 기동되고, `GET /api/v1/health`가 DB 연결을 포함해 200을 반환한다.

**Given** Alembic이 초기화될 때
**When** `alembic upgrade head`를 실행하면
**Then** 마이그레이션이 멱등하게 적용되어 동일 스키마가 재생성되고(NFR6), 스키마는 코드로 버전 관리된다.

**Given** API가 오류를 반환할 때
**When** service 계층이 도메인 예외를 던지면
**Then** 전역 예외 핸들러가 표준 envelope `{code, message, detail?}` + 적절한 HTTP status로 변환하고, `message`는 한국어로 노출 가능하다(AR12, NFR2).

**Given** PK 생성 정책(G4/AR4)에서
**When** 모델 PK를 정의하면
**Then** UUIDv7을 Python `uuid7` 라이브러리로 앱 측에서 생성하며 DB `DEFAULT uuidv7()`을 사용하지 않는다(Supabase PG17 호환·이관 안전).

### Story 1.3: 역할 선택 회원가입 + 시드 관리자

As a 신규 사용자(고객 또는 고수),
I want 역할을 선택해 이메일+비밀번호로 회원가입하기를,
So that gosoom에서 내 역할에 맞는 활동을 시작할 수 있다.

**Acceptance Criteria:**

**Given** `users` 테이블(id UUIDv7, email, password_hash, **display_name**, user_role, is_active, created_at/updated_at/deleted_at)이 마이그레이션될 때
**When** `POST /api/v1/auth/signup`에 이메일·비밀번호·**표시명(displayName)**·역할(customer|pro)을 보내면
**Then** 비밀번호는 Argon2로 해싱 저장되고(평문 미보관, NFR3), `display_name`이 함께 저장되어 사용자가 생성되며 안전한 사용자 표현(비밀번호 제외, displayName 포함)이 반환된다(FR1).
> **표시명(display_name) 근거:** FR8 견적 비교의 "고수 정보"와 Story 4.5 채팅 목록의 "상대방 정보"가 이메일이 아닌 사람이 식별 가능한 이름으로 노출되도록 하는 최소 식별 필드. 고수 선택(SM3 견적→채팅 전환)의 전제. 고객·고수 공통 필수 입력이며, 관리자 시드 계정도 표시명을 가진다.

**Given** 이미 등록된 이메일로
**When** 다시 가입을 시도하면
**Then** 중복 이메일 오류가 표준 envelope로 반환된다(409 등).

**Given** 역할 값이 `admin`이거나 허용 외 값일 때
**When** 가입을 시도하면
**Then** 거부된다 — 관리자는 자가 가입 대상이 아니다(FR1).

**Given** 초기 시스템 부트스트랩 시
**When** Alembic data migration/seed가 실행되면
**Then** 시드 관리자 1개(FR1/FR21)가 생성되고, 이 시드 관리자는 비활성화 대상에서 제외되도록 표식된다(잠금 방지, FR21).

### Story 1.4: 로그인/로그아웃 & 세션 갱신 (JWT)

As a 사용자(고객·고수·관리자),
I want 이메일+비밀번호로 로그인하고 세션이 만료돼도 재인증 없이 갱신되기를,
So that 끊김 없이 서비스를 이용하고 안전하게 로그아웃할 수 있다.

**Acceptance Criteria:**

**Given** 활성 사용자가
**When** `POST /api/v1/auth/login`에 올바른 자격증명을 보내면
**Then** access 토큰(15~30분)과 refresh 토큰(7~30일)이 발급되고, JWT payload는 `{user_id, user_role, exp}`(HS256)이다(FR2, AR11).

**Given** 잘못된 자격증명이거나 비활성(is_active=false) 계정일 때
**When** 로그인을 시도하면
**Then** 인증 실패(401)가 표준 envelope로 반환되고 토큰은 발급되지 않는다(FR19/20 차단 규칙 정합).

**Given** access 토큰이 만료되었고 유효한 refresh 토큰이 있을 때
**When** `POST /api/v1/auth/refresh`를 호출하면
**Then** 새 access 토큰이 재발급된다(FR3).

**Given** 로그인 상태에서
**When** 로그아웃하면
**Then** 클라이언트가 보유 토큰을 폐기하여 세션이 종료된다(Bearer 무상태 — 서버 토큰 무효화는 MVP 범위 외, 의도된 단순화).

### Story 1.5: 역할 기반 접근 제어(RBAC)

As a 시스템,
I want 모든 보호된 엔드포인트에서 인증과 역할·소유권을 서버에서 검사하기를,
So that 각 역할이 자신에게 허용된 데이터·기능에만 접근하도록 일관되게 강제할 수 있다.

**Acceptance Criteria:**

**Given** 보호된 엔드포인트가 있을 때
**When** `Depends(get_current_user)`로 JWT를 검증하고 `require_role(...)` 가드를 적용하면
**Then** 토큰 누락·만료·역할 불일치 시 각각 401/403이 표준 envelope로 반환된다(FR4, AR8).

**Given** 권한 규칙이 여러 곳에 흩어질 위험이 있을 때
**When** 소유권 검사(고객=본인 자원, 고수=본인 자원, 관리자=전체)를 구현하면
**Then** 검사는 service 계층에서 단일 시행되고 라우터/클라이언트에 분산되지 않는다(NFR4, AR8).

**Given** RBAC를 검증하는 테스트가 있을 때
**When** pytest로 각 역할의 허용/거부 경로를 실행하면
**Then** 허용 케이스는 200, 권한 외 케이스는 403으로 통과한다.

### Story 1.6: 카테고리 엔티티·조회 API·시드

As a 고객·고수,
I want 서비스 카테고리 목록을 조회하기를,
So that 요청 생성(FR5)과 고수 카테고리 설정(FR9)에서 동일한 카테고리를 선택할 수 있다.

**Acceptance Criteria:**

**Given** `categories` 테이블(id UUIDv7, name, is_active, created_at/updated_at, deleted_at)이 마이그레이션될 때
**When** `GET /api/v1/categories`를 호출하면
**Then** 활성 카테고리 목록이 `{items, nextCursor}` 형식으로 반환된다(소프트 삭제·비활성 제외).

**Given** 초기 부트스트랩 시
**When** seed 스크립트가 실행되면
**Then** 기본 카테고리(예: 청소, 정리수납 등)가 생성되어 Epic 2·3가 빈 의존성 없이 동작한다(AR5).

**Given** 인증된 사용자가
**When** 카테고리 조회를 요청하면
**Then** 고객·고수 모두 읽기가 허용되고, 카테고리 생성/수정/삭제(FR24)는 이 스토리 범위에 포함되지 않는다(관리자 Epic 6).

### Story 1.7: 인증 UI(user-web) + api-client 확립

As a 고객·고수,
I want user-web에서 가입·로그인 화면을 통해 계정을 만들고 로그인하기를,
So that 웹에서 즉시 서비스에 진입할 수 있다.

**Acceptance Criteria:**

**Given** FastAPI OpenAPI(`openapi.json`)가 준비되었을 때
**When** Orval을 실행하면
**Then** `packages/api-client/src/generated`에 TS 타입 + TanStack Query 훅이 생성되고(수동 수정 금지, AR9), `src/client.ts`에 Bearer 인터셉터(401→refresh 1회→재요청)가 구성된다(AR10).

**Given** user-web에 `(auth)/signup`·`(auth)/login` 화면이 있을 때
**When** 사용자가 역할을 선택하고 **표시명(displayName)**·이메일·비밀번호를 입력해 가입하고 로그인하면
**Then** Orval 훅을 통해 백엔드와 통신하여 가입→로그인 플로우가 E2E로 완결되고, access는 메모리·refresh는 웹 저장소에 보관된다(AR10). 가입 폼에는 표시명 입력이 포함된다(Story 1.3 `display_name`).

**Given** 로딩·오류 상태가 발생할 때
**When** TanStack Query의 `isPending`/`error`를 사용하면
**Then** 로딩·에러 UI가 일관되게 표시되고 에러 메시지는 `error.message`(한국어)로 노출된다.

**Given** 미인증 상태로 보호 화면에 접근할 때
**When** App Router 가드가 동작하면
**Then** 로그인 화면으로 리다이렉트된다(UX 보조, 최종 권한은 서버, AR17).

### Story 1.8: CI 파이프라인 + 워킹 스켈레톤 배포

As a 개발팀,
I want CI(테스트·린트)와 워킹 스켈레톤의 배포 파이프라인을 갖추기를,
So that 가입/로그인이 실제 배포 환경에서 동작함을 검증하고 데모 안정성(NFR8)을 확보할 수 있다.

**Acceptance Criteria:**

**Given** GitHub Actions 워크플로우가 구성될 때
**When** PR이 생성되면
**Then** `pytest`(api)와 lint/typecheck/build(JS)가 실행되어 핵심 경로를 검증한다(AR20).

**Given** Railway에 api·user-web 서비스와 Supabase PostgreSQL(Phase 1) 연결이 구성될 때
**When** main 브랜치에 병합되면
**Then** GitHub 연동으로 자동 배포되어 배포 URL에서 가입→로그인이 동작한다(AR19, SM4 데모 무중단 기반).

**Given** 시크릿(JWT_SECRET, DATABASE_URL)이 필요할 때
**When** Railway 환경변수로 주입하면
**Then** 시크릿은 클라이언트·로그·코드에 노출되지 않고, 클라이언트엔 `NEXT_PUBLIC_API_URL`만 주입된다(NFR3, AR18).

**Given** ⚡수동 설정 체크포인트(AR23)에 따라
**When** 이 스토리(및 Epic 1) 구현에 진입하기 전
**Then** 사용자(KTH)가 직접 할 외부 설정(Supabase 가입·프로젝트 생성·DATABASE_URL 확보, JWT 시크릿 생성, Railway 가입·GitHub 연동)을 구체적 단계와 함께 먼저 안내한다.

## Epic 2: 고객 서비스 요청

고객이 (시드된) 카테고리를 골라 지역·내용을 담아 서비스 요청을 생성하고, 자신의 요청 목록·상세를 조회하며, 상태에 따라 취소·완료 처리할 수 있다. 거래 루프의 출발점이며, 각 스토리는 API + user-web UI를 함께 전달한다.
**FRs covered:** FR5, FR6, FR7

### Story 2.1: 서비스 요청 생성

As a 고객,
I want 카테고리·지역·요청 내용(과 선택적 희망 일정·예산)을 담아 서비스 요청을 올리기를,
So that 나에게 맞는 고수들로부터 견적을 받을 수 있다.

**Acceptance Criteria:**

**Given** `service_requests` 테이블(id UUIDv7, customer_id FK, category_id FK, region, description, desired_schedule nullable, budget nullable 정수 KRW, status, created_at/updated_at/deleted_at)이 마이그레이션될 때
**When** 고객이 `POST /api/v1/service-requests`에 categoryId·region·description(+선택 desiredSchedule·budget)을 보내면
**Then** 요청이 `status=open`으로 생성되고 `customer_id`는 현재 로그인 고객으로 설정되며, 생성된 요청이 반환된다(FR5).

**Given** 필수 필드 누락이거나 존재하지 않는/비활성 카테고리일 때
**When** 생성을 시도하면
**Then** 서버 검증(Pydantic + service)이 실패를 표준 envelope로 반환한다(클라이언트 검증만 신뢰하지 않음, NFR3/NFR4).

**Given** 고수·관리자 또는 비활성 고객 계정일 때
**When** 요청 생성을 시도하면
**Then** 권한 없음(403) 또는 차단되어 거부된다(FR4, FR19 차단 규칙).

**Given** user-web의 `(customer)/requests/new` 화면에서
**When** 고객이 카테고리(시드 목록 조회)를 선택해 폼을 제출하면
**Then** Orval 훅으로 요청이 생성되고 내 요청 목록으로 이동하며, 폼 이탈을 줄이도록 입력은 최소·명확하게 구성된다(CM3).

### Story 2.2: 내 요청 목록·상세 조회

As a 고객,
I want 내가 생성한 요청의 목록과 상세를 조회하기를,
So that 각 요청의 진행 상태를 파악할 수 있다.

**Acceptance Criteria:**

**Given** 고객이 여러 요청을 생성했을 때
**When** `GET /api/v1/service-requests?mine=true`(또는 동등 규약)를 호출하면
**Then** 본인 요청만 `{items, nextCursor}` cursor 페이지네이션으로 최신순 반환되고, 소프트 삭제(숨김)된 요청은 제외된다(FR6).

**Given** 특정 요청 상세를 볼 때
**When** `GET /api/v1/service-requests/{id}`를 호출하면
**Then** 카테고리·지역·내용·상태·생성일이 반환되며, 타인 요청 조회는 403으로 차단된다(소유권 검사, FR4).

**Given** user-web의 `(customer)/requests` 화면에서
**When** 고객이 목록과 상세를 열람하면
**Then** 각 요청의 상태(open/matched/completed/cancelled)가 한국어 라벨로 표시되고, 견적 비교(FR8)는 Epic 4에서 상세 화면에 추가된다(이 스토리는 요청 정보만 표시).

### Story 2.3: 요청 상태 관리 (취소·완료)

As a 고객,
I want 내 요청을 취소하거나 거래 종료 시 완료 처리하기를,
So that 요청의 생애주기를 내가 직접 관리할 수 있다.

**Acceptance Criteria:**

**Given** `open` 상태의 본인 요청이 있을 때
**When** 고객이 취소를 요청하면(`PATCH .../{id}` 또는 전용 액션)
**Then** 상태가 `cancelled`로 전이되고, service 계층이 전이 규칙을 단일 시행한다(FR7).

**Given** `matched` 상태의 본인 요청이 있을 때
**When** 고객이 완료 처리하면
**Then** 상태가 `completed`로 전이된다(R2: 완료는 고객 수동, FR7).

**Given** 허용되지 않는 전이(예: `completed`→`open`, `cancelled`→`matched`)일 때
**When** 전이를 시도하면
**Then** service가 거부하고 표준 envelope 오류를 반환하여 상태 일관성을 보장한다(NFR7).

**Given** user-web 요청 상세 화면에서
**When** 현재 상태에 따라 가능한 액션만 노출되면
**Then** 고객은 취소/완료 버튼을 상태에 맞게 사용할 수 있고, 액션 후 TanStack Query 캐시가 무효화·갱신된다.

## Epic 3: 고수 카테고리 & 견적

고수가 활동 카테고리를 복수 설정하고, 일치하는 open 요청을 열람하며, 견적을 제안하고 자신의 견적 상태를 조회할 수 있다. 각 스토리는 API + user-web(고수) UI를 함께 전달한다.
**FRs covered:** FR9, FR10, FR11, FR12

### Story 3.1: 고수 활동 카테고리 설정

As a 고수,
I want 내 활동 카테고리를 복수로 설정·변경하기를,
So that 나에게 맞는 요청만 효율적으로 찾아볼 수 있다.

**Acceptance Criteria:**

**Given** `pro_categories`(user_id FK, category_id FK, 복합 PK) M:N 조인 테이블이 마이그레이션될 때(AR6/G1)
**When** 고수가 `PUT /api/v1/pros/me/categories`에 categoryId 배열을 보내면
**Then** 해당 고수의 활동 카테고리가 교체 저장되고, 현재 설정된 카테고리 목록이 반환된다(FR9, 복수 허용).

**Given** 존재하지 않거나 비활성인 카테고리를 포함할 때
**When** 설정을 시도하면
**Then** service가 검증 실패를 표준 envelope로 반환한다.

**Given** 고객·관리자 또는 비활성 고수일 때
**When** 카테고리 설정을 시도하면
**Then** 권한 없음(403) 또는 차단된다(FR4, FR20).

**Given** user-web `(pro)/categories` 화면에서
**When** 고수가 카테고리(시드 목록)를 다중 선택해 저장하면
**Then** Orval 훅으로 반영되고 현재 선택이 표시된다.

### Story 3.2: 카테고리 매칭 요청 열람

As a 고수,
I want 내 활동 카테고리와 일치하는 서비스 요청 목록·상세를 열람하기를,
So that 견적을 제안할 만한 일감을 발견할 수 있다.

**Acceptance Criteria:**

**Given** 고수가 활동 카테고리를 설정했을 때
**When** `GET /api/v1/service-requests/feed`(또는 동등 규약)를 호출하면
**Then** 고수 카테고리와 일치하는 요청만 `{items, nextCursor}`로 반환되고, 소프트 삭제된 요청은 제외된다(FR10).

**Given** 요청이 `matched` 상태가 되었을 때
**When** 고수가 피드를 조회하면
**Then** 해당 요청은 목록에서 제외되지 않고 비활성 상태로 표시되어 더 이상 견적 제안 대상이 아님을 인지할 수 있다(R1/FR10).

**Given** 요청 상세를 볼 때
**When** `GET /api/v1/service-requests/{id}`를 호출하면
**Then** 고수는 자신의 카테고리와 일치하는 요청의 상세(카테고리·지역·내용·상태)를 열람할 수 있다.

**Given** user-web `(pro)/feed` 화면에서
**When** 고수가 피드와 상세를 열람하면
**Then** open 요청에는 견적 제안 진입이, matched 요청에는 비활성 표시가 노출된다.

### Story 3.3: 견적 제안

As a 고수,
I want open 상태의 요청에 가격과 제안 메시지를 담아 견적을 제안하기를,
So that 고객에게 나를 어필하고 거래로 이어갈 수 있다.

**Acceptance Criteria:**

**Given** `quotes` 테이블(id UUIDv7, service_request_id FK, pro_id FK, price 정수 KRW, message, status[pending|accepted|rejected|closed], created_at/updated_at/deleted_at)이 마이그레이션될 때
**When** 고수가 `open` 요청에 `POST /api/v1/service-requests/{id}/quotes`로 price·message를 보내면
**Then** 견적이 `status=pending`으로 생성되고 `pro_id`는 현재 고수로 설정된다(FR11).

**Given** 한 요청에 이미 본인 견적이 존재할 때
**When** 같은 요청에 다시 제안하면
**Then** 거부된다 — 요청당 고수 1개 견적(FR11). (DB 유니크 제약 + service 검증)

**Given** 요청이 `open`이 아니거나(matched/completed/cancelled) 고수 카테고리와 불일치할 때
**When** 견적 제안을 시도하면
**Then** service가 거부하고 표준 envelope 오류를 반환한다(FR10/FR11).

**Given** user-web 요청 상세(고수 뷰)에서
**When** 고수가 가격·메시지를 입력해 제안하면
**Then** Orval 훅으로 견적이 생성되고 내 견적 목록에 반영된다(스팸성 남발 방지를 위해 1요청 1견적 UX 강제, CM2).

### Story 3.4: 내 견적 목록·상태 조회

As a 고수,
I want 내가 제안한 견적의 목록과 상태를 조회하기를,
So that 어떤 견적이 수락/거절/마감되었는지 추적할 수 있다.

**Acceptance Criteria:**

**Given** 고수가 여러 견적을 제안했을 때
**When** `GET /api/v1/quotes?mine=true`(또는 동등 규약)를 호출하면
**Then** 본인 견적만 `{items, nextCursor}`로 반환되며 각 견적의 상태(pending/accepted/rejected/closed)와 대상 요청 정보가 포함된다(FR12).

**Given** 견적 상태가 변경되었을 때(수락=accepted, 거절=rejected, 타 견적 수락으로 마감=closed)
**When** 고수가 목록을 조회하면
**Then** 변경된 상태가 정확히 반영된다(Epic 4의 FR13/FR14 전이와 정합).

**Given** 타 고수의 견적일 때
**When** 조회를 시도하면
**Then** 소유권 검사로 본인 견적만 노출된다(FR4).

**Given** user-web `(pro)/quotes` 화면에서
**When** 고수가 견적 목록을 열람하면
**Then** 각 견적의 상태가 한국어 라벨로 표시된다.

## Epic 4: 매칭 & 채팅 (거래 루프 완결)

고객이 받은 견적을 비교하고 하나를 수락(또는 거절)하면, 수락 시 단일 트랜잭션으로 요청이 matched로 전환되고 채팅방이 생성되며 타 견적은 closed 처리된다. 이후 고객↔고수가 1:1 채팅(텍스트, 폴링)으로 거래를 마무리한다. 제품의 핵심 가치이자 무결성이 가장 중요한 지점.
**FRs covered:** FR8, FR13, FR14, FR15, FR16, FR17, FR18

### Story 4.1: 받은 견적 비교

As a 고객,
I want 내 요청에 들어온 견적 목록을 가격·메시지·고수 정보와 함께 비교하기를,
So that 가장 마음에 드는 고수를 골라 거래를 진행할 수 있다.

**Acceptance Criteria:**

**Given** 본인 요청에 여러 견적이 들어왔을 때
**When** 고객이 `GET /api/v1/service-requests/{id}/quotes`를 호출하면
**Then** 해당 요청의 견적들이 가격·제안 메시지·고수 기본 정보(고수 `displayName` + 활동 카테고리)·상태와 함께 `{items, nextCursor}`로 반환된다(FR8). 응답에는 고수의 이메일을 노출하지 않고 표시명만 포함한다(개인정보 최소 노출).

**Given** 타인 요청의 견적일 때
**When** 조회를 시도하면
**Then** 소유권 검사로 본인 요청의 견적만 노출된다(FR4).

**Given** user-web `(customer)/requests/[id]` 상세 화면에서
**When** 고객이 견적 목록을 열람하면
**Then** 견적들이 비교 가능한 형태(가격·메시지·고수)로 표시되고, 각 견적에 수락/거절 액션 진입점이 노출된다(상태가 pending인 경우).

### Story 4.2: 견적 수락 & 채팅방 생성

As a 고객,
I want 받은 견적 중 하나를 수락하여 그 고수와 대화를 시작하기를,
So that 선택한 고수와 거래 세부사항을 조율할 수 있다.

**Acceptance Criteria:**

**Given** `chat_rooms` 테이블(id UUIDv7, service_request_id FK, customer_id FK, pro_id FK, quote_id FK, created_at)과 `quotes`에 대한 partial unique index `uq_quotes_accepted_per_request`(요청당 accepted 1개)가 마이그레이션될 때(AR6/G2, AR7)
**When** 고객이 본인 요청의 `pending` 견적에 `POST /api/v1/quotes/{id}/accept`를 호출하면
**Then** 단일 트랜잭션 안에서 ① 요청 상태가 `matched`로 전환, ② 해당 고객·고수의 `chat_room`이 생성, ③ 동일 요청의 다른 `pending` 견적이 모두 `closed`로 전환되고, 수락된 견적은 `accepted`가 된다(FR13, FR15).

**Given** 두 요청이 동시에 같은 요청의 서로 다른 견적을 수락하려 할 때
**When** accept 트랜잭션이 실행되면
**Then** `SELECT ... FOR UPDATE`로 요청 행을 잠그고 partial unique index가 두 번째 수락을 거부하여, 요청당 정확히 하나의 견적만 수락된다(race 차단, AR7, NFR7).

**Given** 이미 `matched`된 요청이거나 본인 요청이 아니거나 견적이 `pending`이 아닐 때
**When** 수락을 시도하면
**Then** service가 거부하고 표준 envelope 오류를 반환하며 어떤 상태도 변경되지 않는다(원자성).

**Given** user-web 요청 상세에서 고객이 한 견적을 수락하면
**When** 응답이 성공하면
**Then** 요청·견적·채팅방 관련 TanStack Query 캐시가 무효화·갱신되고 고객이 새 채팅방으로 진입할 수 있다.

### Story 4.3: 견적 거절

As a 고객,
I want 받은 견적을 명시적으로 거절하기를,
So that 원치 않는 견적을 정리하면서도 다른 견적은 계속 검토할 수 있다.

**Acceptance Criteria:**

**Given** 본인 요청의 `pending` 견적이 있을 때
**When** 고객이 `POST /api/v1/quotes/{id}/reject`를 호출하면
**Then** 해당 견적만 `rejected`로 전환되고 요청 상태는 `open`으로 유지된다(FR14, 개별 단위).

**Given** 견적이 거절되었을 때
**When** 해당 고수가 자신의 견적 목록(FR12)을 조회하면
**Then** 상태가 `rejected`로 반영되어 보인다.

**Given** 본인 요청이 아니거나 견적이 `pending`이 아닐 때
**When** 거절을 시도하면
**Then** service가 거부한다(FR4, 상태 일관성).

**Given** user-web 요청 상세에서
**When** 고객이 견적을 거절하면
**Then** 목록이 갱신되고 남은 견적은 계속 비교·수락 가능하다.

### Story 4.4: 채팅 메시지 전송·수신 (폴링)

As a 고객·고수,
I want 채팅방에서 텍스트 메시지를 보내고 상대의 새 메시지를 받아보기를,
So that 거래 세부사항(방문 시간 등)을 대화로 조율할 수 있다.

**Acceptance Criteria:**

**Given** `messages` 테이블(id UUIDv7 시간정렬, chat_room_id FK, sender_id FK, content, created_at)이 마이그레이션될 때(AR6/G3, 발신자 식별 + 증분 정렬 키)
**When** 채팅방 참여자가 `POST /api/v1/chat-rooms/{id}/messages`로 content를 보내면
**Then** 메시지가 저장되고 `sender_id`는 현재 사용자로 설정되며 저장된 메시지가 반환된다(FR16).

**Given** 신규 메시지 수신이 필요할 때
**When** 참여자가 `GET /api/v1/chat-rooms/{id}/messages?after=<lastId>`를 호출하면
**Then** `lastId` 이후의 신규 메시지만 증분 반환된다(전체 재수신 금지, CM1/AR13).

**Given** 채팅방 참여자(해당 고객·고수)가 아니거나 비활성 계정일 때
**When** 전송·수신을 시도하면
**Then** 소유권/차단 검사로 거부된다(FR4, FR19/20).

**Given** user-web 채팅 화면에서
**When** 참여자가 채팅방을 열어두면
**Then** TanStack Query `refetchInterval`(2~3초)로 증분 폴링하여 새 메시지가 갱신되고, 메시지 전송 후 즉시 반영된다(FR17, AR13/AR15).

### Story 4.5: 채팅방 목록 조회

As a 고객·고수,
I want 내가 참여 중인 채팅방 목록을 조회하기를,
So that 진행 중인 여러 거래의 대화에 쉽게 접근할 수 있다.

**Acceptance Criteria:**

**Given** 사용자가 여러 채팅방에 참여 중일 때
**When** `GET /api/v1/chat-rooms?mine=true`(또는 동등 규약)를 호출하면
**Then** 본인이 참여한(고객=customer_id, 고수=pro_id) 채팅방 목록이 `{items, nextCursor}`로 반환되며 상대방 정보(상대방 `displayName`)·연관 요청 정보가 포함된다(FR18). 상대방 식별은 이메일이 아닌 표시명으로 노출한다.

**Given** 참여하지 않은 채팅방일 때
**When** 접근을 시도하면
**Then** 소유권 검사로 차단된다(FR4).

**Given** user-web `chat/` 화면에서
**When** 사용자가 채팅방 목록을 열람하면
**Then** 각 방의 상대방·연관 요청이 표시되고 선택 시 해당 채팅방(4.4)으로 진입한다.

## Epic 5: 모바일 앱

고객·고수가 모바일 앱(Expo SDK 55, 시연 Expo Go)에서 거래 루프(가입~요청~견적~수락~채팅)를 사용할 수 있다. 신규 백엔드 FR을 도입하지 않고, 공유 `packages/api-client`(Orval)와 `packages/ui`(RN-Web 호환)를 재사용하여 user-web의 도메인 기능을 모바일 플랫폼으로 전달한다(NFR1).
**FRs covered:** (신규 없음 — FR1-18의 고객·고수 플로우를 모바일로 전달)

> ⚡**수동 설정 체크포인트(AR23):** 이 에픽 구현 진입 전, 사용자(KTH)가 직접 할 설정 — Expo 계정 생성·Expo Go 앱 설치, 실기기 시연용 API URL(PC LAN IP 또는 배포된 Railway URL, localhost 불가) 확인 — 을 구체적 단계와 함께 먼저 안내한다.

### Story 5.1: 모바일 셸 & 인증

As a 고객·고수,
I want 모바일 앱에서 가입·로그인하고 세션이 안전하게 유지되기를,
So that 휴대폰에서 gosoom에 진입할 수 있다.

**Acceptance Criteria:**

**Given** mobile 앱(Expo SDK 55, expo-router)이 공유 패키지를 사용하도록 구성될 때
**When** `EXPO_PUBLIC_API_URL`(LAN IP 또는 배포 URL)을 주입하고 앱을 기동하면
**Then** 공유 `api-client`(Orval 훅)와 `ui` 프리미티브가 모바일에서 정상 로드되고 API와 통신한다(AR18, NFR1).

**Given** 사용자가 모바일에서 가입·로그인할 때
**When** 인증 화면에서 역할 선택 가입·로그인을 수행하면
**Then** FR1-4 백엔드 플로우가 재사용되어 가입→로그인이 완결되고, refresh 토큰은 Expo SecureStore에, access는 메모리에 보관된다(AR10).

**Given** access 토큰 만료 시
**When** api-client 인터셉터가 401을 받으면
**Then** refresh 1회 시도 후 재요청하며, 실패 시 로그아웃 처리된다(웹과 동일 로직 공유).

**Given** 미인증 상태에서 보호 화면 접근 시
**When** expo-router 가드가 동작하면
**Then** 로그인 화면으로 이동한다(UX 보조, 최종 권한은 서버).

### Story 5.2: 모바일 고객 플로우

As a 고객,
I want 모바일에서 서비스 요청을 올리고 견적을 비교·수락/거절하기를,
So that 이동 중에도 거래를 진행할 수 있다.

**Acceptance Criteria:**

**Given** 로그인한 고객이 모바일에 있을 때
**When** 요청 생성·내 요청 목록/상세·상태 관리(취소·완료) 화면을 사용하면
**Then** FR5-7 백엔드를 공유 api-client로 호출하여 웹과 동일하게 동작한다.

**Given** 요청 상세에서
**When** 고객이 받은 견적을 비교하고 수락 또는 거절하면
**Then** FR8/FR13/FR14가 재사용되어 수락 시 채팅방이 생성되고 캐시가 갱신된다.

**Given** 모바일 UI에서
**When** 화면을 렌더링하면
**Then** NativeWind + 공유 `ui` 프리미티브로 일관된 한국어 UI가 표시되고 TanStack Query 로딩/에러 상태가 적용된다(AR15/AR16, NFR2).

### Story 5.3: 모바일 고수 플로우

As a 고수,
I want 모바일에서 활동 카테고리를 설정하고 요청 피드를 보며 견적을 제안·조회하기를,
So that 휴대폰으로 일감을 찾고 대응할 수 있다.

**Acceptance Criteria:**

**Given** 로그인한 고수가 모바일에 있을 때
**When** 카테고리 설정·매칭 요청 피드·견적 제안·내 견적 목록 화면을 사용하면
**Then** FR9-12 백엔드를 공유 api-client로 호출하여 웹과 동일하게 동작한다.

**Given** 피드에서
**When** matched된 요청이 표시되면
**Then** 비활성 상태로 표시되어 견적 제안이 불가함을 인지할 수 있다(FR10 정합).

**Given** 견적 제안 시
**When** 이미 본인 견적이 있는 요청에 다시 제안하면
**Then** 백엔드 규칙(요청당 1견적)에 따라 거부되고 오류 메시지가 표시된다(FR11).

### Story 5.4: 모바일 채팅

As a 고객·고수,
I want 모바일에서 채팅방 목록을 보고 메시지를 주고받기를,
So that 어디서나 거래 상대와 대화할 수 있다.

**Acceptance Criteria:**

**Given** 수락으로 생성된 채팅방이 있을 때
**When** 사용자가 모바일에서 채팅방 목록·채팅방을 열면
**Then** FR15/FR18 백엔드를 재사용해 본인 참여 방과 메시지가 표시된다.

**Given** 채팅방을 열어둘 때
**When** TanStack Query `refetchInterval`(2~3초) 증분 폴링이 동작하면
**Then** 새 메시지가 `after=<lastId>`로 증분 수신되어 갱신되고, 전송 시 즉시 반영된다(FR16/FR17, CM1).

**Given** 모바일 네트워크 환경에서
**When** 폴링이 동작하면
**Then** 페이로드는 증분만 전송되어 과도한 트래픽이 발생하지 않는다(AR13/NFR5).

## Epic 6: 관리자 콘솔

운영자가 관리자 전용 웹(admin-web)에서 계정(고객·고수·관리자), 서비스 요청, 채팅 내역(읽기전용), 카테고리를 관리한다. admin 라우터는 도메인 service를 역할 가드 하에 호출하여 로직 중복을 피하고, 소프트 삭제/비활성화 규칙을 일관 적용한다.
**FRs covered:** FR19, FR20, FR21, FR22, FR23, FR24

### Story 6.1: 관리자 콘솔 셸 & 로그인

As a 관리자,
I want 관리자 전용 웹에 로그인하여 콘솔에 진입하기를,
So that 운영 관리 기능에 안전하게 접근할 수 있다.

**Acceptance Criteria:**

**Given** admin-web(Next 16 App Router)이 공유 `api-client`/`ui`를 사용하도록 구성될 때
**When** Orval 생성 훅과 Bearer 인터셉터를 연결하고 `NEXT_PUBLIC_API_URL`을 주입하면
**Then** admin-web이 백엔드와 통신하고 콘솔 레이아웃이 렌더링된다(AR9/AR10/AR18).

**Given** 관리자 계정(시드 관리자 포함)이
**When** admin-web `(auth)/login`에서 로그인하면
**Then** Epic 1의 로그인 백엔드(FR2)가 재사용되어 토큰이 발급되고 콘솔에 진입한다.

**Given** 비관리자(고객·고수) 토큰이거나 미인증일 때
**When** 관리자 콘솔/엔드포인트에 접근하면
**Then** `require_role('admin')` 가드로 403/리다이렉트되어 차단된다(FR4, AR8).

### Story 6.2: 고객·고수 계정 관리

As a 관리자,
I want 고객·고수 계정 목록·상세를 조회하고 비활성화/재활성화하기를,
So that 부적절한 계정의 활동을 차단하되 데이터는 보존할 수 있다.

**Acceptance Criteria:**

**Given** 관리자가 콘솔에 있을 때
**When** `GET /api/v1/admin/users?role=customer|pro`로 목록·상세를 조회하면
**Then** 해당 역할 계정이 `{items, nextCursor}`로 반환된다(FR19/FR20).

**Given** 활성 계정을
**When** 관리자가 비활성화하면(`is_active=false`)
**Then** 그 계정은 로그인 및 신규 거래 활동(요청 생성·견적 제안·채팅 전송)이 차단되며, 기존 요청·채팅 데이터는 삭제되지 않고 유지된다(소프트 비활성화, FR19/FR20, R3).

**Given** 비활성화된 계정을
**When** 관리자가 재활성화하면
**Then** 다시 정상 활동이 가능해진다.

**Given** admin-web `users/` 화면에서
**When** 관리자가 계정을 관리하면
**Then** 활성/비활성 상태가 표시되고 비활성화/재활성화 액션이 제공되며, 액션 후 목록이 갱신된다.

### Story 6.3: 관리자 계정 관리

As a 관리자,
I want 관리자 계정 목록을 조회하고 신규 관리자를 추가하거나 기존 관리자를 비활성화하기를,
So that 운영 권한을 안전하게 위임·회수할 수 있다.

**Acceptance Criteria:**

**Given** 관리자가 콘솔에 있을 때
**When** `GET /api/v1/admin/admins`로 관리자 목록을 조회하면
**Then** 관리자 계정 목록이 반환된다(FR21).

**Given** 관리자가
**When** 신규 관리자(이메일+비밀번호)를 추가하면
**Then** `user_role=admin` 계정이 생성된다 — 자가 가입이 아닌 기존 관리자에 의한 생성 경로만 허용된다(FR1/FR21).

**Given** 시드 관리자(초기 1개)를
**When** 비활성화하려 시도하면
**Then** 거부되어 잠금(lock-out)을 방지한다(FR21).

**Given** admin-web `admins/` 화면에서
**When** 관리자가 관리자 계정을 관리하면
**Then** 추가/비활성화 액션이 제공되고 시드 관리자에는 비활성화가 비활성 처리된다.

### Story 6.4: 서비스 요청 관리

As a 관리자,
I want 전체 서비스 요청 목록·상세·상태를 조회하고 상태를 변경하거나 부적절한 요청을 숨김 처리하기를,
So that 플랫폼의 거래를 점검하고 운영할 수 있다.

**Acceptance Criteria:**

**Given** 관리자가 콘솔에 있을 때
**When** `GET /api/v1/admin/service-requests`로 전체 요청 목록·상세·상태를 조회하면
**Then** (숨김 포함 여부 옵션과 함께) 요청들이 `{items, nextCursor}`로 반환된다(FR22).

**Given** 관리자가
**When** 요청 상태를 변경하면
**Then** service 계층의 전이 규칙 하에 상태가 변경된다(NFR7).

**Given** 부적절한 요청을
**When** 관리자가 숨김 처리하면
**Then** `deleted_at`이 설정되는 소프트 삭제가 적용되고, 연결된 견적·채팅은 보존된다(물리 삭제 금지, FR22, NFR7).

**Given** admin-web `requests/` 화면에서
**When** 관리자가 요청을 관리하면
**Then** 상태 변경·숨김 액션이 제공되고 일반 조회에서 숨김 요청은 기본 제외된다.

### Story 6.5: 채팅 내역 열람 (읽기 전용)

As a 관리자,
I want 채팅방과 메시지 내역을 읽기 전용으로 열람하기를,
So that 문제가 된 거래의 상황을 감사·모니터링할 수 있다.

**Acceptance Criteria:**

**Given** 관리자가 콘솔에 있을 때
**When** `GET /api/v1/admin/chat-rooms`와 `GET /api/v1/admin/chat-rooms/{id}/messages`를 호출하면
**Then** 채팅방 목록과 메시지 내역이 읽기 전용으로 반환된다(FR23).

**Given** 관리자가
**When** 채팅에 메시지를 전송하거나 내용을 수정하려 시도하면
**Then** 그러한 엔드포인트가 제공되지 않아 불가능하다 — 열람 전용(FR23).

**Given** admin-web `chats/` 화면에서
**When** 관리자가 채팅 내역을 열람하면
**Then** 메시지가 발신자·시간과 함께 읽기 전용으로 표시되고 입력/전송 UI는 없다.

### Story 6.6: 카테고리 관리

As a 관리자,
I want 서비스 카테고리를 생성·수정·(비)활성화하기를,
So that 고객 요청과 고수 활동에 사용될 카테고리 목록을 운영할 수 있다.

**Acceptance Criteria:**

**Given** 관리자가 콘솔에 있을 때
**When** `POST/PATCH /api/v1/admin/categories`로 카테고리를 생성·수정하면
**Then** 카테고리가 생성/수정되고 고객(FR5)·고수(FR9)의 선택 목록에 반영된다(FR24).

**Given** 어떤 요청이나 고수가 참조 중인(사용 중) 카테고리를
**When** 관리자가 삭제하려 시도하면
**Then** 물리 삭제는 차단되고 비활성화만 허용되어 참조 무결성이 보호된다(FR24, NFR7).

**Given** 미사용 카테고리를
**When** 관리자가 비활성화/삭제(소프트)하면
**Then** 활성 카테고리 조회(FR/Epic 1 카테고리 API)에서 제외된다.

**Given** admin-web `categories/` 화면에서
**When** 관리자가 카테고리를 관리하면
**Then** 생성·수정·비활성화 액션이 제공되고 사용 중 카테고리에는 비활성화만 노출된다.

## Epic 7: 공개 랜딩 & 브랜드 표기 (Post-MVP UX)

미인증 방문자에게 공개 메인 랜딩을 제공하고, 화면 노출 제품명을 `gosoom`→`meetgo`로 변경한다. 신규 FR 없음(UX 개선). PRD 범위 밖에서 KTH 요청으로 직접 구현(ad-hoc, 정식 스토리 절차 없이 구현 후 사후 기록).
**FRs covered:** 없음

### Story 7.1: 공개 메인 랜딩 화면

As a 미인증 방문자,
I want user-web·mobile 진입 시 로그인 화면이 아니라 서비스를 소개하는 공개 랜딩을 보기를,
So that 서비스를 이해하고 로그인/회원가입을 선택할 수 있다.

**Acceptance Criteria:**

**Given** 토큰이 없는 방문자가
**When** user-web `/` 또는 mobile 루트(`/`)에 진입하면
**Then** 로그인으로 리다이렉트되지 않고 공개 랜딩(히어로·기능 소개·CTA)이 표시되며, 로그인/회원가입 링크로 기존 인증 화면에 연결된다.

**Given** 이미 인증된 사용자가
**When** 랜딩(`/`)에 진입하면
**Then** 역할별 홈(user-web `/dashboard`, mobile 역할 그룹)으로 리다이렉트된다.

**Given** PC·모바일 각 화면 폭에서
**When** 랜딩을 보면
**Then** 반응형 레이아웃(데스크톱 2단 히어로/모바일 단일 컬럼)과 브랜드 톤 비주얼이 적용된다.

> **구현 메모:** user-web은 기존 대시보드를 `/dashboard`로 이동하고 `/`를 공개 랜딩으로 교체. AppHeader의 `useReadMe`를 `enabled: isAuthenticated()`로 게이트해 공개 페이지에서 401→로그인 강제 이동 버그를 차단. mobile은 `_layout.tsx` AuthGate가 랜딩(`/`)을 미인증 허용하도록 수정.

### Story 7.2: 브랜드 표기 변경 (gosoom → meetgo)

As a 운영자(KTH),
I want 화면에 노출되는 제품명을 `gosoom`에서 `meetgo`로 바꾸기를,
So that 변경된 브랜드 아이덴티티를 사용자에게 일관되게 전달한다.

**Acceptance Criteria:**

**Given** user-web·admin-web·mobile의 화면 텍스트에서
**When** 브랜드명이 표기되는 모든 위치(로고·타이틀·히어로·푸터·메타데이터 등)를 보면
**Then** `gosoom`이 `meetgo`로 표시된다.

**Given** 코드·설정 식별자(`@gosoom/*` 패키지·import, env 키, localStorage `gosoom_quote_submitted_*`, SecureStore `gosoom.refresh`, app.json 등)는
**When** 브랜드 변경을 적용해도
**Then** `gosoom`으로 그대로 유지된다(빌드·런타임 안정성 보존).

> **구현 메모:** 한글 브랜드 "믿고"는 현재 코드에 한글 표기("고숨")가 없어 치환 대상이 없으며 미노출 상태. 필요 시 후속으로 한글 병기 추가. app.json `expo.name` 등 네이티브 설정은 미변경(변경 시 앱 리빌드 필요).
