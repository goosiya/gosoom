"""공통 테스트 헬퍼 — 실 DB 픽스처에서 ORM 객체 생성.

여러 테스트 파일에 중복 복사되던 헬퍼를 단일 소스로 통합. 각 테스트 파일은
이 모듈에서 필요한 함수를 임포트해 사용한다.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.category import Category
from app.models.pro_category import ProCategory
from app.models.quote import Quote, QuoteStatus
from app.models.service_request import ServiceRequest, ServiceRequestStatus
from app.models.user import User, UserRole


async def _make_pro(db: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("secret"),
        display_name="고수유저",
        user_role=UserRole.PRO,
        is_active=True,
        is_seed=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _make_customer(db: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("secret"),
        display_name="고객유저",
        user_role=UserRole.CUSTOMER,
        is_active=True,
        is_seed=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _make_admin(db: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("secret"),
        display_name="관리자유저",
        user_role=UserRole.ADMIN,
        is_active=True,
        is_seed=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _make_category(
    db: AsyncSession,
    name: str = "청소",
    *,
    is_active: bool = True,
) -> Category:
    cat = Category(name=name, is_active=is_active)
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return cat


async def _make_service_request(
    db: AsyncSession,
    customer: User,
    category: Category,
    status: ServiceRequestStatus = ServiceRequestStatus.OPEN,
    region: str = "서울",
    description: str = "테스트 요청입니다.",
) -> ServiceRequest:
    sr = ServiceRequest(
        customer_id=customer.id,
        category_id=category.id,
        region=region,
        description=description,
        status=status,
    )
    db.add(sr)
    await db.flush()
    await db.refresh(sr)
    return sr


async def _make_quote(
    db: AsyncSession,
    pro: User,
    request: ServiceRequest,
    price: int = 10000,
    message: str = "테스트 견적",
    status: QuoteStatus = QuoteStatus.PENDING,
) -> Quote:
    quote = Quote(
        service_request_id=request.id,
        pro_id=pro.id,
        price=price,
        message=message,
        status=status,
    )
    db.add(quote)
    await db.flush()
    await db.refresh(quote)
    return quote


async def _assign_pro_categories(
    db: AsyncSession, pro: User, categories: list[Category]
) -> None:
    """PRO에게 카테고리 목록을 일괄 할당."""
    for cat in categories:
        row = ProCategory(user_id=pro.id, category_id=cat.id)
        db.add(row)
    await db.flush()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.user_role)
    return {"Authorization": f"Bearer {token}"}
