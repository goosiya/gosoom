# gosoom API (FastAPI)

통합 API — 모든 클라이언트(user-web, admin-web, mobile)가 `/api/v1`만 경유한다(패턴 A, AR8).
계층: **router(HTTP) → service(비즈니스/권한/트랜잭션) → repository(DB)**. 역방향 호출 금지.

## 구조

```
app/
  main.py          FastAPI 앱, /api/v1, CORS, 예외 핸들러(Story 1.2)
  core/            config(설정) · db(async 엔진/세션) · security(Argon2/JWT)
  models/          SQLAlchemy 모델
  schemas/         Pydantic (to_camel alias)
  routers/         HTTP 엔드포인트
  services/        비즈니스 규칙·권한·트랜잭션·상태기계 단일 시행
  repositories/    DB 접근 격리 (deleted_at IS NULL 공통 필터)
  deps.py          get_current_user, require_role
alembic/           마이그레이션 + 시드(초기 관리자/기본 카테고리)
tests/             pytest
```

> Story 1.1은 **디렉터리 골격만** 생성한다. 실제 구현(DB 기반·인증·도메인)은 Story 1.2부터.

## 개발 (Story 1.2~)

```bash
# Python 3.12 + 의존성 (uv가 .venv·인터프리터까지 관리)
uv sync
# 환경변수
cp .env.example .env   # DATABASE_URL, JWT_SECRET, CORS_ORIGINS 채움
# 마이그레이션
uv run alembic upgrade head
# 서버
uv run uvicorn app.main:app --reload
```

## 주의

- Turbo 태스크 그래프 **외부**(JS 앱과 별도 파이프라인).
- 시크릿(`DATABASE_URL`, `JWT_SECRET`)은 절대 커밋·로그 노출 금지(NFR3).
