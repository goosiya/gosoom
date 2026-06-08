# gosoom

숨고형 양면 마켓플레이스 MVP — 고객·고수·관리자 3개 역할의 서비스 요청·견적·매칭·채팅 플랫폼.

## 모노레포 구조

```
apps/
  user-web/    고객·고수 반응형 웹 (Next.js 16, App Router)
  admin-web/   관리자 반응형 웹 (Next.js 16, App Router)
  mobile/      고객·고수 모바일 앱 (Expo SDK 55)
  api/         통합 API (FastAPI) — Turbo 외부, 별도 파이프라인
packages/
  api-client/  Orval 생성 TS 타입 + TanStack Query 훅 (3앱 공유)
  types/       비-API 공유 타입·상수
  ui/          RN-Web 호환 공유 프리미티브
  config/      eslint / tsconfig / tailwind 프리셋
```

## 기술 스택

- **프론트엔드:** Next.js 16(웹 ×2), Expo SDK 55(모바일), React 19.2.0, TanStack Query v5, Tailwind/NativeWind
- **백엔드:** FastAPI, SQLAlchemy 2.0(async/asyncpg), Alembic, Argon2, JWT(HS256)
- **DB:** PostgreSQL (Phase 1: Supabase → Phase 2: Railway)
- **모노레포:** pnpm workspaces + Turborepo (JS 앱 한정)

## 개발 시작

### 사전 요구사항

- Node 20+ / pnpm 11+
- Python 3.12 (apps/api — `uv` 권장)

### JS 앱

```bash
pnpm install          # 루트에서 1회
pnpm dev              # turbo dev — 웹·모바일 병렬 기동
pnpm build            # 전체 빌드
pnpm lint             # 린트
```

### 백엔드 (apps/api) — Story 1.2에서 구성

```bash
cd apps/api
uv sync               # .venv + 의존성
uv run uvicorn app.main:app --reload
```

## 환경변수

`.env.example` 참조. 시크릿(`DATABASE_URL`, `JWT_SECRET`)은 절대 커밋하지 않는다.
