# gosoom API — Railway 배포용 컨테이너 (AR19).
# uv 기반 의존성 설치 → uvicorn 기동. 빌드 컨텍스트 = apps/api (Railway 루트 디렉터리).
# 마이그레이션(alembic upgrade head)은 CMD에 넣지 않는다 — Railway release/pre-deploy
# command로 분리(배포당 1회, 다중 레플리카 중복 실행 방지). 결정 #3 / docs/deploy.md 참조.
FROM python:3.12-slim

# uv 설치 — 버전 고정(latest는 빌드 재현성을 깨뜨림)
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

WORKDIR /app

# 의존성 레이어 캐싱 — uv.lock 포함해 재현 가능한 설치(--frozen: lock 그대로, 갱신 금지)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 앱 소스
COPY . .
RUN uv sync --frozen --no-dev

ENV PORT=8000
EXPOSE 8000

# exec 형식으로 uvicorn이 PID 1을 받아 Railway SIGTERM을 처리(그레이스풀 셧다운)
# sh -c 안에서 exec를 사용해 $PORT 셸 확장도 보장
CMD ["sh", "-c", "exec uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
