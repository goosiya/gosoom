"""보안 유틸 — 비밀번호 해싱/검증(Argon2) + JWT 발급/검증(HS256).

- `hash_password`/`verify_password`: Argon2 단방향 해싱·대조. 평문은 절대 저장하지 않는다(NFR3/AR11).
- `create_access_token`/`create_refresh_token`/`decode_token`: HS256 JWT 발급·검증(Story 1.4).
  토큰 payload 규약(클레임 이름·`type`·만료)은 여기서 확정되며, Story 1.5의
  `get_current_user`/`require_role`가 동일 키(`user_id`/`user_role`)로 소비한다 — 변경 금지.
- `oauth2_scheme`: Bearer 토큰 추출 스킴(Story 1.5). 추출만 담당 — 누락→예외 변환은 deps.py가 한다.
- 인증/인가 가드(`get_current_user`/`require_role`)는 deps.py(Story 1.5).

⚠️ 이 모듈은 라이브러리 계층 — 도메인 예외를 import하지 않는다. `decode_token`은 PyJWT의
`jwt.InvalidTokenError`(만료/위조/서명오류의 공통 베이스)를 그대로 전파하고, service가 잡아
도메인 예외(`InvalidTokenError`)로 변환한다(계층 분리 + 이름 충돌 회피).
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from app.core.config import settings
from app.models.user import UserRole

# Bearer 토큰 추출 스킴(Story 1.5). `Authorization: Bearer <jwt>`에서 토큰 문자열만 뽑는다.
# ⚠️ auto_error=False가 핵심: 기본값 True면 토큰 누락 시 FastAPI가 자체 HTTPException(401)을
# 던져 envelope 핸들러의 HTTPException 분기로 새어 `{code:"http_401"}`가 된다(우리 표준 코드 깨짐).
# False로 두면 토큰 누락 시 None을 넘겨주고, deps.get_current_user가 도메인 예외
# NotAuthenticatedError(안정 code "not_authenticated")로 변환한다.
# tokenUrl은 OpenAPI(Swagger Authorize) 표시용 상대 경로일 뿐 — 실제 로그인은 1.4 /login(JSON).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)

# 권장 구성(Argon2). 모듈 수준 단일 인스턴스로 재사용.
password_hasher = PasswordHash.recommended()

# JWT 서명 알고리즘(architecture#Authentication AR11). 발급/검증 모두 동일 사용.
_JWT_ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    """평문 비밀번호를 Argon2 해시 문자열로 변환($argon2... 포맷)."""
    return password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """평문 비밀번호와 저장된 Argon2 해시를 대조. 일치하면 True, 아니면 False.

    pwdlib는 불일치 시 False를 반환하지만, 손상된/비-Argon2 해시 문자열에는
    `UnknownHashError` 등 예외를 던진다. 로그인 검증 경로가 절대 예외로 새지 않도록
    예외는 모두 False로 정규화한다(검증 실패 = 인증 거부).
    """
    try:
        return password_hasher.verify(plain, hashed)
    except Exception:
        return False


# 타이밍 공격(사용자 열거) 방어용 더미 해시. 미존재 사용자 경로에서도 실제와 동일한
# Argon2 검증 비용을 치르게 해, 응답 시간 차로 이메일 가입 여부를 추론하지 못하게 한다(NFR3).
# 모듈 import 시 1회 생성.
_DUMMY_PASSWORD_HASH = password_hasher.hash("timing-equalization-dummy")


def dummy_verify_password() -> None:
    """미존재 사용자 로그인 경로에서 호출해 Argon2 검증 시간을 균등화(anti-enumeration, NFR3).

    고정 더미 해시에 대해 (의도적으로 불일치하는) verify를 수행하고 결과는 버린다 —
    목적은 존재하는 사용자의 비밀번호 대조와 동등한 시간을 소비하는 것뿐이다.
    """
    verify_password("timing-equalization-dummy-wrong", _DUMMY_PASSWORD_HASH)


def create_access_token(user_id: UUID, user_role: UserRole) -> str:
    """access 토큰 발급. payload `{user_id, user_role, type:"access", exp}`(HS256).

    exp = now(UTC) + access_token_expire_minutes(기본 30분). user_role은 소문자 값 문자열로
    저장해 1.5 `get_current_user`가 동일 문자열로 읽는다.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "user_id": str(user_id),  # UUID는 JSON 직렬화 불가 → 문자열로 저장
        "user_role": user_role.value,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    """refresh 토큰 발급. payload `{user_id, type:"refresh", exp}`(HS256).

    exp = now(UTC) + refresh_token_expire_days(기본 14일). user_role은 **미포함** —
    refresh 시 사용자를 재조회해 현재 role을 반영하므로 토큰에 박아두면 stale 위험.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "user_id": str(user_id),
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """JWT 서명·만료를 검증하고 payload(dict)를 반환. 실패 시 `jwt.InvalidTokenError`.

    PyJWT가 서명·만료를 자동 검증 → 만료(`ExpiredSignatureError`)·위조(`DecodeError`)·
    서명오류(`InvalidSignatureError`)는 모두 `jwt.InvalidTokenError`의 서브클래스로 발생.
    호출자(service)가 `except jwt.InvalidTokenError`로 한 번에 잡아 도메인 예외로 변환한다.

    `options={"require": ["exp"]}`: PyJWT 기본은 `exp` 부재를 허용(영구 토큰)하므로,
    exp 없는 토큰을 명시적으로 거부해 만료 없는 토큰이 통과하지 못하게 한다(방어적 견고성).
    """
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[_JWT_ALGORITHM],
        options={"require": ["exp"]},
    )
