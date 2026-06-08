"""opaque cursor 규약의 단일 구현(Story 1.6).

cursor는 정렬 경계값을 base64로 감싼 불투명 문자열 — 클라이언트는 구조를 해석하지 않는다
(서버가 자유롭게 키 구성을 변경 가능). Epic 2+는 복합 키(createdAt+id 등)를 이 규약으로
인코딩한다 — **재사용 자산은 이 불투명 규약**이지 keyset 로직이 아니다(결정 사항 #1).

최소 2함수만 제공한다(일반 keyset 엔진 금지).
"""

import base64
import binascii

from app.core.exceptions import InvalidCursorError


def encode_cursor(value: str) -> str:
    """경계값 문자열(여기선 UUID 문자열)을 opaque base64 cursor로 인코딩."""
    return base64.urlsafe_b64encode(value.encode()).decode()


def decode_cursor(cursor: str) -> str:
    """opaque base64 cursor를 경계값 문자열로 디코딩.

    디코드 실패(비-base64·UTF-8 디코드 실패)는 InvalidCursorError(400)로 변환해 500 누수를
    방지한다(1.5 형식 가드 철학 계승). 호출측(service)에서 추가로 UUID 변환 실패도
    InvalidCursorError로 정규화한다.
    """
    try:
        return base64.urlsafe_b64decode(cursor.encode()).decode()
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursorError() from exc
