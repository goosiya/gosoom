"""에러 envelope 일관성 테스트 (AC3).

prod main.py를 오염시키지 않기 위해, 동일 예외 핸들러(`register_exception_handlers`)를
붙인 격리 앱에 테스트 전용 라우트를 등록해 세 경로(AppError / 검증실패 / HTTPException)가
모두 `{code, message, detail?}` envelope로 변환되는지 검증한다.
"""

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import AppError
from app.main import register_exception_handlers


def _build_app() -> FastAPI:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/boom")
    async def _boom() -> None:
        raise AppError(
            code="teapot", message="나는 주전자입니다", status_code=418, detail={"x": 1}
        )

    @test_app.get("/needs-q")
    async def _needs_q(q: int) -> dict[str, int]:
        return {"q": q}

    @test_app.get("/http-error")
    async def _http_error() -> None:
        raise HTTPException(status_code=404, detail="찾을 수 없습니다")

    return test_app


@pytest.fixture
async def err_client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=_build_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_app_error_envelope(err_client: AsyncClient) -> None:
    res = await err_client.get("/boom")
    assert res.status_code == 418
    body = res.json()
    assert body["code"] == "teapot"
    assert body["message"] == "나는 주전자입니다"  # 한국어 노출 가능(NFR2)
    assert body["detail"] == {"x": 1}


async def test_validation_error_envelope(err_client: AsyncClient) -> None:
    # 필수 쿼리 q 누락 → RequestValidationError → 422 envelope
    res = await err_client.get("/needs-q")
    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "validation_error"
    assert "message" in body
    assert "detail" in body


async def test_http_exception_envelope(err_client: AsyncClient) -> None:
    res = await err_client.get("/http-error")
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == "http_404"
    assert body["message"] == "찾을 수 없습니다"
