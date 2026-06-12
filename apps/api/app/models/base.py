"""모델 공통 베이스 + 재사용 mixin.

Story 1.3(users)부터 소비할 **기반만** 확립한다 — 이 스토리는 도메인 테이블을 만들지 않는다.

- `Base`: core.db의 단일 선언적 베이스를 재export(메타데이터 단일 소스).
- `UUIDPrimaryKeyMixin`: UUIDv7 PK를 **앱 측에서** 생성(G4/AR4). server_default 금지 —
  PostgreSQL 17 호환·DB 호스팅 이관 안전을 위해 DB `DEFAULT uuidv7()`에 의존하지 않는다.
- `TimestampMixin` / `SoftDeleteMixin`: created_at/updated_at/deleted_at.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid_extensions import uuid7

from app.core.db import Base

__all__ = ["Base", "UUIDPrimaryKeyMixin", "TimestampMixin", "SoftDeleteMixin"]


class UUIDPrimaryKeyMixin:
    """UUIDv7 PK (`id`). callable default=uuid7로 앱 측 생성, server_default 미사용."""

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,  # 앱 측 생성 (G4/AR4) — server_default 금지
    )


class TimestampMixin:
    """생성/수정 타임스탬프. created_at은 DB now() server_default 허용."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        server_default=func.now(),
    )


class SoftDeleteMixin:
    """소프트삭제 마커. 조회는 repository 계층에서 `deleted_at IS NULL` 공통 필터로 처리."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
