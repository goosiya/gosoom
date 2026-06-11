"""도메인 예외 베이스 + 표준 에러 envelope.

service 계층이 `AppError`(또는 서브클래스)를 던지면 전역 핸들러가
`{code, message, detail?}` + 적절한 HTTP status로 변환한다(AR12, NFR2).
- `code`: 기계 판독용 안정 식별자(snake_case).
- `message`: 사용자 노출 가능(한국어).
"""

from typing import Any


class AppError(Exception):
    """애플리케이션 도메인 예외 베이스. 전역 핸들러가 envelope로 변환."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        detail: Any | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)

    def to_envelope(self) -> dict[str, Any]:
        """`{code, message, detail?}` envelope 직렬화 (detail은 있을 때만)."""
        body: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.detail is not None:
            body["detail"] = self.detail
        return body


# ---- 도메인 예외 (첫 예시: 이후 도메인이 동일 패턴 복제) ----


class DuplicateEmailError(AppError):
    """이미 가입된 이메일로 재가입 시도(AC2). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="email_already_exists",
            message="이미 가입된 이메일입니다.",
            status_code=409,
        )


class InvalidCredentialsError(AppError):
    """로그인 실패(Story 1.4 AC2). 401.

    미존재 이메일·비밀번호 불일치·비활성 계정 **모두 단일 일반 401**로 사용한다.
    공격자가 응답으로 이메일 존재·계정 상태를 추론하지 못하게 하는 anti-enumeration(NFR3).
    """

    def __init__(self) -> None:
        super().__init__(
            code="invalid_credentials",
            message="이메일 또는 비밀번호가 올바르지 않습니다.",
            status_code=401,
        )


class InvalidTokenError(AppError):
    """유효하지 않은 토큰(Story 1.4 AC3). 401.

    refresh 디코드 실패(만료/위조/서명오류)·`type` 불일치(토큰 혼동)·
    비활성/삭제 사용자 재조회 실패에 사용한다.
    Story 1.5의 get_current_user도 동일하게 토큰은 있으나 무효한 경우에 재사용한다.
    """

    def __init__(self) -> None:
        super().__init__(
            code="invalid_token",
            message="유효하지 않은 토큰입니다.",
            status_code=401,
        )


class NotAuthenticatedError(AppError):
    """인증 누락(Story 1.5 AC1). 401.

    `Authorization` 헤더 부재 — 즉 **토큰을 아예 보내지 않은** 경우 전용.
    토큰이 있으나 무효한 경우(만료/위조/type 불일치/형식 오류/비활성)는
    `InvalidTokenError`를 쓴다. `code`로 클라이언트가 "로그인 필요"(not_authenticated) vs
    "세션 만료→refresh 시도"(invalid_token)를 구분할 수 있다(1.7 인터셉터 로직).
    """

    def __init__(self) -> None:
        super().__init__(
            code="not_authenticated",
            message="인증이 필요합니다.",
            status_code=401,
        )


class ForbiddenError(AppError):
    """권한 부족(Story 1.5 AC3/AC4). 403.

    인증은 되었으나 역할이 허용 집합에 없거나(`require_role`),
    자기 소유가 아닌 자원에 접근(`ensure_owner_or_admin`)할 때 사용하는 공용 예외.
    """

    def __init__(self) -> None:
        super().__init__(
            code="forbidden",
            message="이 작업을 수행할 권한이 없습니다.",
            status_code=403,
        )


class InvalidCursorError(AppError):
    """손상/위조된 페이지네이션 cursor(Story 1.6 AC4). 400.

    base64 디코드 실패·비-UUID cursor가 decode_cursor/UUID()에서 예외를 던지면 잡지 않을 경우
    전역 Exception 핸들러로 새어 500이 된다. 사용자 입력 오류는 4xx로 정규화한다
    (1.5 payload 형식 가드 철학 계승). 400은 이 스토리가 처음 도입하나 전역 핸들러가
    AppError.status_code를 그대로 쓰므로 핸들러 수정은 불요.
    """

    def __init__(self) -> None:
        super().__init__(
            code="invalid_cursor",
            message="잘못된 커서입니다.",
            status_code=400,
        )


class CategoryNotFoundError(AppError):
    """존재하지 않거나 비활성 카테고리 조회 시(Story 2.1 AC2). 404."""

    def __init__(self) -> None:
        super().__init__(
            code="category_not_found",
            message="카테고리를 찾을 수 없습니다.",
            status_code=404,
        )


class ServiceRequestNotFoundError(AppError):
    """존재하지 않거나 삭제된 서비스 요청 조회 시(Story 2.2 AC2). 404."""

    def __init__(self) -> None:
        super().__init__(
            code="service_request_not_found",
            message="요청을 찾을 수 없습니다.",
            status_code=404,
        )


class InvalidStatusTransitionError(AppError):
    """허용되지 않는 상태 전이 시도(Story 2.3 AC3). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="invalid_status_transition",
            message="허용되지 않는 상태 전이입니다.",
            status_code=409,
        )


class InvalidCategoryIdsError(AppError):
    """존재하지 않거나 비활성 카테고리 ID가 포함된 경우(Story 3.1 AC4). 400."""

    def __init__(self) -> None:
        super().__init__(
            code="invalid_category_ids",
            message="유효하지 않은 카테고리 ID가 포함되어 있습니다.",
            status_code=400,
        )


class DuplicateQuoteError(AppError):
    """동일 요청에 이미 견적을 제안한 경우(Story 3.3 AC3). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="duplicate_quote",
            message="이미 이 요청에 견적을 제안했습니다.",
            status_code=409,
        )


class ServiceRequestNotOpenForQuoteError(AppError):
    """견적 제안 시 요청이 open 상태가 아닌 경우(Story 3.3 AC4). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="service_request_not_open",
            message="견적 제안은 open 상태의 요청에만 가능합니다.",
            status_code=409,
        )


class QuoteNotFoundError(AppError):
    """존재하지 않거나 삭제된 견적 조회 시(Story 4.2 AC3). 404."""

    def __init__(self) -> None:
        super().__init__(
            code="quote_not_found",
            message="견적을 찾을 수 없습니다.",
            status_code=404,
        )


class QuoteNotPendingError(AppError):
    """pending이 아닌 견적에 상태 변경(수락/거절)을 시도할 때(Story 4.2 AC3, Story 4.3 AC3). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="quote_not_pending",
            message="pending 상태의 견적만 변경할 수 있습니다.",
            status_code=409,
        )


class ServiceRequestAlreadyMatchedError(AppError):
    """이미 matched 상태인 요청의 견적을 수락하려 할 때(Story 4.2 AC3). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="service_request_already_matched",
            message="이미 수락된 견적이 있는 요청입니다.",
            status_code=409,
        )


class ChatRoomNotFoundError(AppError):
    """존재하지 않는 채팅방 조회 시(Story 4.4 AC4). 404."""

    def __init__(self) -> None:
        super().__init__(
            code="chat_room_not_found",
            message="채팅방을 찾을 수 없습니다.",
            status_code=404,
        )


class UserNotFoundError(AppError):
    """존재하지 않거나 삭제된 사용자 조회 시(Story 6.2 AC1). 404."""

    def __init__(self) -> None:
        super().__init__(
            code="user_not_found",
            message="사용자를 찾을 수 없습니다.",
            status_code=404,
        )


class SeedAdminDeactivationError(AppError):
    """시드 관리자 비활성화 시도 시(FR21). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="seed_admin_deactivation_forbidden",
            message="시드 관리자는 비활성화할 수 없습니다.",
            status_code=409,
        )
