---
title: "gosoom PRD — Addendum (기술 결정 보존)"
status: draft
created: 2026-06-07
updated: 2026-06-07
---

# gosoom PRD Addendum

> 이 문서는 PRD 본문(WHAT)에 들어가지 않는 **기술적 HOW·결정 근거**를 보존합니다.
> 출처: `_bmad-output/planning-artifacts/research/technical-gosoom-mvp-tech-stack-research-2026-06-07.md`.
> 다운스트림 작업(`bmad-create-architecture`)의 입력으로 사용됩니다.

## 확정된 아키텍처 원칙

> **"Supabase는 DB(PostgreSQL)로만 사용한다. 인증·실시간 채팅·스토리지 등 나머지 모든 기능은 FastAPI가 담당하여 Supabase에 종속되지 않게 한다."**

- 클라이언트는 Supabase에 직접 접속하지 않음. 모든 요청은 FastAPI 단일 경유(패턴 A).
- 권한 경계 = 앱 레벨(FastAPI). RLS 미사용 (service_role 키는 RLS를 항상 우회하므로 RLS 병행은 무의미).
- 이관(Phase 2) = `DATABASE_URL` 환경변수 교체 + 데이터 덤프 수준. 앱 코드 변경 없음.

## 5대 핵심 기술 결정

| # | 결정 | 비고 |
|---|------|------|
| 1 | Supabase = DB 전용, 나머지 기능 전부 FastAPI 소유 | 이관 = 환경변수 교체 |
| 2 | 채팅 = REST + HTTP 폴링 (2~3초) | WebSocket·Redis 미도입. 메시지는 `messages` 테이블 |
| 3 | 인증 = FastAPI 자체 JWT | users 테이블, Argon2 해싱, HS256, access(15~30분)+refresh(7~30일) |
| 4 | 파일 업로드 = MVP 범위 제외 | Post-MVP: Cloudflare R2 |
| 5 | 권한 = 앱 레벨(RLS 미사용), JWT `user_role` 기반 | 고객/고수/관리자 라우트 분기 |

## 기술 스택 (PRD 반영용)

| 영역 | 선택 |
|------|------|
| 사용자/관리자 웹 | Next.js (App Router) |
| 모바일 | React Native + Expo (SDK 52+), 시연 Expo Go |
| API | FastAPI (router→service→repository) |
| DB 접근 | SQLAlchemy + Alembic |
| DB(호스팅) | Phase1 Supabase → Phase2 Railway PostgreSQL |
| 모노레포 | Turborepo (JS 앱 3개 타입·api-client·UI 공유, FastAPI는 별도) |
| 배포 | Railway (FE/BE/PG), 공식 풀스택 스타터 검증됨 |

## 데이터 모델 핵심 엔티티(예상)

`users`(role 포함) · `categories` · `service_requests` · `quotes` · `chat_rooms` · `messages`

## 토큰 저장 / 통합 함정

- 웹(Next.js): httpOnly 쿠키 권장. RN/Expo: Expo SecureStore(refresh).
- FastAPI `CORSMiddleware` 필수(웹↔API 오리진 상이).
- Expo Go 실기기 시연: API 주소는 PC LAN IP 또는 배포된 Railway URL(localhost 불가). 시연은 Railway 배포 API 권장.
- 환경변수: `NEXT_PUBLIC_API_URL` / `EXPO_PUBLIC_API_URL`.

## (고려 후 기각) 대안들

- **Supabase Auth + RLS RBAC**: 개발 빠르나 `auth.users`·플랫폼 종속 → 이관 시 전원 재인증 필요. 기각.
- **Supabase Realtime / FastAPI WebSocket**: 실시간 우수하나 인프라(Redis/브로커)·복잡도 증가. MVP엔 폴링이 "효용 80%를 복잡도 20%"로 제공. 기각(Post-MVP 업그레이드 경로로 보존).
- **BFF(Backend for Frontend)**: 다중 클라이언트엔 검증된 패턴이나 MVP는 단일 API + 역할별 엔드포인트로 충분. Post-MVP.

## Phase 2 이관 세부 및 리스크 완화

- **덤프 도구:** 원시 `pg_dump`가 아니라 **`supabase db dump`** 사용(내부 스키마 제외, 예약 롤 제거, 멱등 `IF NOT EXISTS`). 원시 pg_dump는 Supabase 내부 스키마 포함 → 복원 시 권한 오류 위험.
- **사전 점검:** `select * from pg_extension`로 비기본 확장 확인 후 대상(Railway) DB에 활성화.
- **이관 절차:** Railway PostgreSQL 프로비저닝 → 확장 확인 → `alembic upgrade head`(스키마) + 데이터 덤프 → `DATABASE_URL` 교체·재배포.
- **완화책:** ① 테스트 인스턴스에서 이관 선검증 → ② 점검창(maintenance window) 확보 → ③ 데이터 정합성 검증 후 전환. 앱 코드 변경 없음.

## 운영 주의

- **Supabase 무료 티어 한도(2026):** DB 500MB · 파일 1GB · MAU 5만 · realtime 동시연결 200(폴링 채택으로 무관) · 프로젝트 2개. **1주 비활성 시 자동 일시정지**(2026-02 변경) → 시연 직전 깨우기(~30초) 또는 Pro/Railway 조기 전환.
- **용량 주의:** 비활성 계정 데이터 유지(FR19) + 채팅 메시지 누적으로 DB 500MB 한도에 점진 접근 가능 → NFR10으로 표면화. 한도 임박 시 Pro 전환 또는 Phase 2 이관으로 대응.
- **모노레포 학습곡선:** Turborepo 태스크/의존성 그래프 학습 비용 → 검증된 스타터(`create-t3-turbo`) 차용으로 완화.
- MVP 월 비용 ≈ $0~$25.

## 구현 진행 합의 — 수동 설정 체크포인트 (⚡사용자 지침 2026-06-07)

> **합의:** 각 기능 구현에 진입하기 *전에*, 사용자(KTH)가 직접 수동으로 가입/설정해야 하는 외부 서비스·콘솔 작업을 먼저 알려주고, 구체적 방법(단계)을 함께 제시한다. 구현 에이전트는 이 체크포인트를 먼저 안내한 뒤 코드 작업을 시작한다.

예상되는 수동 설정 항목과 발생 시점(아키텍처/스프린트 단계에서 확정·정교화):

| 구현 단계 | 사용자가 수동으로 해야 할 일(예상) |
|-----------|-----------------------------------|
| 기반 셋업 | Supabase 계정 가입 · 프로젝트 생성 · `DATABASE_URL`/연결정보 확보, 로컬 `.env` 구성 |
| 모노레포/도구 | Node/pnpm·Python 환경, Turborepo 초기화 전제 도구 설치 |
| 인증 | JWT 서명용 시크릿 생성·`.env` 등록 |
| 모바일 | Expo 계정·Expo Go 설치, 실기기 시연용 API URL(LAN IP 또는 배포 URL) 설정 |
| 배포 | Railway 계정 가입 · GitHub 연동 · 서비스(api/web/postgres) 생성 · 환경변수 등록 |
| Phase 2 이관 | Railway PostgreSQL 프로비저닝 · 확장 확인 · `DATABASE_URL` 교체 |

> 위 표는 PRD 단계의 예측이며, 실제 항목·순서는 `bmad-create-architecture`와 스프린트 계획에서 확정한다.
