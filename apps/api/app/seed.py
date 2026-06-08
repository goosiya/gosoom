"""시드 관리자 생성 스크립트 — `uv run python -m app.seed`로 실행.

설계 근거(왜 마이그레이션이 아니라 스크립트인가):
시드를 Alembic 체인에 넣고 admin 크리덴셜을 env에서 강제로 읽으면, 크리덴셜 없는
CI·fresh clone·`upgrade head` 멱등 회귀가드(1.2)가 전부 깨진다. 시드를 별도 멱등
스크립트로 분리해 스키마(upgrade head)와 데이터 시드를 직교시킨다.

멱등: 이미 같은 이메일의 시드 관리자가 있으면 skip. `is_seed=True`로 FR21 잠금 방지 표식.
미설정(SEED_ADMIN_*) 시 명확한 한국어 에러 출력 후 비정상 종료(앱 크래시 아님 — 독립 스크립트).
"""

import asyncio
import sys

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.category import Category
from app.models.user import User, UserRole
from app.repositories.categories import CategoryRepository
from app.repositories.users import UserRepository

# 기본 서비스 카테고리(고정·비밀 아닌 참조값이라 env 불요 — 결정 사항 #4).
# Epic 2(요청 생성)·3(고수 카테고리)이 빈 의존성 없이 동작하기 위한 시드 집합.
DEFAULT_CATEGORIES = ["청소", "정리수납", "이사", "인테리어", "수리", "설치"]


async def seed_admin(session: AsyncSession) -> str:
    """주어진 세션에 시드 관리자 1개를 멱등 생성하고 commit. 반환: 결과 메시지.

    SEED_ADMIN_EMAIL/PASSWORD 미설정 시 ValueError(호출측이 처리). 테스트는 이 함수를
    롤백 세션으로 직접 호출한다(실 커밋 없이 멱등 검증).
    """
    if not settings.seed_admin_email or not settings.seed_admin_password:
        raise ValueError(
            "SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD가 설정되지 않았습니다. "
            "apps/api/.env에 시드 관리자 크리덴셜을 추가하세요."
        )

    # 저장 이메일도 소문자 정규화 — signup/get_by_email과 동일 경계.
    email = settings.seed_admin_email.strip().lower()

    repo = UserRepository(session)
    existing = await repo.get_by_email(email)
    if existing is not None:
        # 해당 이메일을 일반 계정(customer/pro)이 선점한 경우 조용히 skip하면
        # 관리자가 영영 생성되지 않으면서 "이미 존재"로 오인된다 → 명확히 실패.
        if not existing.is_seed or existing.user_role is not UserRole.ADMIN:
            raise ValueError(
                f"'{email}'은(는) 이미 일반 계정으로 사용 중입니다. "
                "SEED_ADMIN_EMAIL을 다른 주소로 설정하세요."
            )
        return f"시드 관리자 이미 존재 — skip ({email})"

    admin = User(
        email=email,
        password_hash=hash_password(settings.seed_admin_password),
        display_name=settings.seed_admin_display_name,
        user_role=UserRole.ADMIN,
        is_seed=True,
        is_active=True,
    )
    try:
        await repo.create(admin)
        await session.commit()
    except IntegrityError as exc:
        # 선검사 통과 후 insert가 유니크 인덱스를 위반(예: 소프트삭제된 동일 이메일 행 잔존,
        # 동시 실행 race)할 수 있다 → 트레이스백 대신 명확한 에러로 변환.
        await session.rollback()
        raise ValueError(
            f"시드 관리자 생성 실패('{email}') — 이미 사용 중인 이메일일 수 있습니다."
        ) from exc
    return f"시드 관리자 생성 완료 ({email})"


async def seed_categories(session: AsyncSession) -> str:
    """기본 카테고리를 멱등 시드하고 commit. 반환: 결과 메시지(신규/기존 개수).

    각 이름에 대해 get_by_name 선검사 → 존재하면 skip, 없으면 생성. 2회 실행해도 카테고리는
    중복 없이 정확히 DEFAULT_CATEGORIES 집합만 존재한다(AC2 멱등). env/시크릿 불요 —
    항상 동작해야 한다(Epic 2/3 의존성, 관리자 시드와의 핵심 차이).
    """
    repo = CategoryRepository(session)
    created = 0
    skipped = 0
    for name in DEFAULT_CATEGORIES:
        normalized = name.strip()
        existing = await repo.get_by_name(normalized)
        if existing is not None:
            skipped += 1
            continue
        session.add(Category(name=normalized, is_active=True))
        created += 1

    try:
        await session.commit()
    except IntegrityError as exc:
        # 선검사 통과 후 insert가 유니크 인덱스를 위반(동시 실행/소프트삭제 잔존 행)할 수 있다 →
        # 트레이스백 대신 명확한 한국어 에러로 변환(seed_admin 패턴).
        await session.rollback()
        raise ValueError(
            "카테고리 시드 실패 — 이미 사용 중인 카테고리명이 있을 수 있습니다."
        ) from exc
    return f"카테고리 시드: 신규 {created}개 / 기존 {skipped}개 skip"


async def main() -> None:
    """실 DB 세션을 열어 카테고리·관리자를 시드한다.

    카테고리 시드는 env 불요라 항상 선행·독립 실행한다 — 관리자 시드가 SEED_ADMIN_* 부재로
    실패해도 카테고리(Epic 2/3 의존성)는 막히지 않도록 admin 실패를 경고로 격하한다.
    """
    async with SessionLocal() as session:
        print(await seed_categories(session))  # env 불요 — 항상 실행
        try:
            print(await seed_admin(session))  # SEED_ADMIN_* 필요
        except ValueError as exc:
            print(f"[시드 경고] 관리자 시드 건너뜀: {exc}", file=sys.stderr)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ValueError as exc:
        print(f"[시드 실패] {exc}", file=sys.stderr)
        sys.exit(1)
