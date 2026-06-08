"""Category 모델 — 첫 참조(reference) 도메인 테이블(Story 1.6).

- `categories` 테이블: 서비스 카테고리(청소/이사 등). 고객 요청(Epic 2)·고수 카테고리(Epic 3)가
  공통으로 참조하는 시드 데이터.
- 읽기 전용 조회 + 시드만 담당 — 생성/수정/삭제(FR24)는 관리자 Epic 6 범위.
- 공통 기반은 base mixin 상속(UUIDv7 PK, created/updated/deleted_at) — User와 동일.

⚠️ `is_seed` 컬럼 없음(의도적 부재): 카테고리는 "잠금 방지"(FR21, 시드 관리자) 대상이 아니므로
users의 is_seed를 복제하지 않는다. enum 컬럼도 전혀 없다(→ 마이그레이션에 enum drop 보정 불요).
"""

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """서비스 카테고리 단일 테이블(참조 도메인)."""

    __tablename__ = "categories"

    # unique+index는 의도적 추가(epic AC 컬럼 리터럴엔 name만 명시). 근거: ① 멱등 시드의
    # get_by_name 선검사, ② 중복 카테고리 방지. 한국어 카테고리명은 strip만 정규화(소문자화 안 함).
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    # 비활성화(FR24, Epic 6)용 플래그. User.is_active와 동일 패턴 복제.
    # 조회는 is_active=true AND deleted_at IS NULL 둘 다 필터(repository에서).
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
