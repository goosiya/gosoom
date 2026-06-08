"""require_role 역할 가드 검증 — 격리 테스트 앱(AC3/AC6).

⚠️ 가짜 프로덕션 보호 엔드포인트를 prod 앱에 만들지 않는다. 테스트 모듈 안에서 최소 FastAPI()
앱을 만들고 더미 보호 라우트를 붙여 가드만 검증한다. 동일 envelope를 적용하려면
register_exception_handlers(test_app)를 반드시 호출하고(미호출 시 AppError→500),
get_db는 test_app.dependency_overrides로 롤백 세션(db_session)을 주입한다.

검증:
- 역할 허용(AC3): admin→/admin-only 200, customer→/pro-or-customer 200.
- 역할 거부(AC3): customer→/admin-only 403, admin→/pro-or-customer 403.
- 401→403 순서(AC3): 토큰 누락→/admin-only는 403이 아니라 401(get_current_user 선행).
"""

from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import create_access_token
from app.deps import require_role
from app.main import register_exception_handlers
from app.models.user import User, UserRole


def _build_test_app(db_session: AsyncSession) -> FastAPI:
    """더미 보호 라우트 2개를 가진 격리 앱 — 동일 핸들러 + 롤백 세션 주입."""
    test_app = FastAPI()
    # 미호출 시 AppError(401/403)가 envelope로 변환되지 않고 500이 된다 — 함정 #5.
    register_exception_handlers(test_app)

    @test_app.get("/admin-only")
    async def _admin_only(
        _user: User = Depends(require_role(UserRole.ADMIN)),
    ) -> dict[str, bool]:
        return {"ok": True}

    @test_app.get("/pro-or-customer")
    async def _pro_or_customer(
        _user: User = Depends(require_role(UserRole.CUSTOMER, UserRole.PRO)),
    ) -> dict[str, bool]:
        return {"ok": True}

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    test_app.dependency_overrides[get_db] = _override_get_db
    return test_app


async def _seed_user(db: AsyncSession, email: str, role: UserRole) -> User:
    """지정 역할 사용자를 savepoint 내부에 직접 시드(signup은 admin 불가 → 직접 insert)."""
    user = User(
        email=email,
        password_hash="x",  # 로그인하지 않으므로 형식 무관(non-null만 충족).
        display_name="가드테스트",
        user_role=role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---- AC3: 역할 허용 ----


async def test_admin_allowed_on_admin_only(db_session: AsyncSession) -> None:
    """admin 토큰 → /admin-only 200(AC3)."""
    admin = await _seed_user(db_session, "guard-admin@example.com", UserRole.ADMIN)
    token = create_access_token(admin.id, admin.user_role)
    test_app = _build_test_app(db_session)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/admin-only", headers=_auth(token))
    assert resp.status_code == 200, resp.text


async def test_customer_allowed_on_pro_or_customer(db_session: AsyncSession) -> None:
    """customer 토큰 → /pro-or-customer 200(AC3)."""
    user = await _seed_user(db_session, "guard-cust@example.com", UserRole.CUSTOMER)
    token = create_access_token(user.id, user.user_role)
    test_app = _build_test_app(db_session)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/pro-or-customer", headers=_auth(token))
    assert resp.status_code == 200, resp.text


# ---- AC3: 역할 거부 ----


async def test_customer_forbidden_on_admin_only(db_session: AsyncSession) -> None:
    """customer 토큰 → /admin-only 403 forbidden(AC3)."""
    user = await _seed_user(db_session, "guard-cust2@example.com", UserRole.CUSTOMER)
    token = create_access_token(user.id, user.user_role)
    test_app = _build_test_app(db_session)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/admin-only", headers=_auth(token))
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


async def test_admin_forbidden_on_pro_or_customer(db_session: AsyncSession) -> None:
    """admin 토큰 → /pro-or-customer 403(허용 집합에 admin 없음)(AC3)."""
    admin = await _seed_user(db_session, "guard-admin2@example.com", UserRole.ADMIN)
    token = create_access_token(admin.id, admin.user_role)
    test_app = _build_test_app(db_session)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/pro-or-customer", headers=_auth(token))
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


# ---- AC3: 401→403 순서(인증 선행) ----


async def test_missing_token_yields_401_not_403(db_session: AsyncSession) -> None:
    """토큰 누락으로 /admin-only → 403이 아니라 401(get_current_user가 먼저 차단)(AC3).

    require_role가 get_current_user 위에 합성되므로 인증이 역할 검사보다 선행함을 증명.
    """
    test_app = _build_test_app(db_session)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/admin-only")
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "not_authenticated"
