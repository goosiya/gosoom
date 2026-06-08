"""애플리케이션 설정 (pydantic-settings).

`.env`에서 환경변수를 로드해 타입 검증된 단일 `settings` 싱글톤으로 노출한다.
- `JWT_SECRET`/토큰 수명 필드는 Story 1.4/1.5(인증)가 소비 — 여기선 선언만, 로직 구현 금지.
- `CORS_ORIGINS`는 콤마 구분 문자열을 list로 파싱(아래 NoDecode 함정 참조).
"""

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수 기반 설정. env 키는 대소문자 무시(DATABASE_URL → database_url)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # DB (asyncpg 드라이버 형식) — repository 계층이 소비
    database_url: str

    # 인증(Story 1.4/1.5 소비) — 이 스토리에선 필드 선언만
    jwt_secret: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # CORS 허용 오리진 (AR14). NoDecode로 pydantic-settings의 JSON 선디코드를 끄고,
    # before-validator에서 콤마 구분 문자열을 직접 분리한다(함정 #1).
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # 시드 관리자(Story 1.3 / FR21) — 시드 스크립트(`python -m app.seed`) 실행 시에만 소비.
    # 필수 아님: 미설정이어도 앱 기동/마이그레이션/회원가입엔 영향 없음(시드 실행 시 검사).
    seed_admin_email: str | None = None
    seed_admin_password: str | None = None
    seed_admin_display_name: str = "관리자"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, v: object) -> object:
        # env 문자열("a,b")이면 분리, 이미 list면 그대로 통과.
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


# 모듈 수준 싱글톤 — 앱 전역에서 import해 사용
settings = Settings()  # type: ignore[call-arg]
