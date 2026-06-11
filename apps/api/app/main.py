"""gosoom 통합 API 진입점 (FastAPI).

모든 클라이언트(user-web, admin-web, mobile)는 `/api/v1`만 경유한다(패턴 A, AR8).
- CORSMiddleware: 명시 오리진만 허용(운영 `*` 금지, AR14).
- 전역 예외 핸들러: AppError/검증실패/HTTPException/미처리 예외를 표준 envelope로 일관 변환(AR12).
- `GET /api/v1/health`: DB 연결(`SELECT 1`)을 포함, 정상 200 / DB 실패 503 반환(AC1).
"""

from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.exceptions import AppError
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.categories import router as categories_router
from app.routers.chat import router as chat_router
from app.routers.pros import router as pros_router
from app.routers.quotes import router as quotes_router
from app.routers.service_requests import router as service_requests_router
from app.routers.users import router as users_router

def register_exception_handlers(app: FastAPI) -> None:
    """표준 에러 envelope {code, message, detail?} 핸들러 등록 (AR12).

    테스트는 격리 앱에 동일 핸들러를 붙여 검증한다(prod 라우트 오염 방지).
    """

    @app.exception_handler(AppError)
    async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        # detail에 UUID/datetime 등 비-JSON 네이티브 값이 와도 안전하도록 인코딩.
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(exc.to_envelope()),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # 검증 실패도 동일 envelope로 변환(detail에 필드별 오류 포함)
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "message": "요청 값이 올바르지 않습니다.",
                "detail": jsonable_encoder(exc.errors()),
            },
        )

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(
        _request: Request, exc: HTTPException
    ) -> JSONResponse:
        # 라우팅/HTTP 레벨 오류(404 등)도 동일 envelope로 일관 변환.
        # detail이 문자열이면 message로, 구조화 값이면 detail 필드로 보존(str() 강제 변환 금지).
        if isinstance(exc.detail, str):
            message: str = exc.detail
            extra_detail: Any | None = None
        else:
            message = "요청을 처리할 수 없습니다."
            extra_detail = exc.detail
        body: dict[str, Any] = {"code": f"http_{exc.status_code}", "message": message}
        if extra_detail is not None:
            body["detail"] = jsonable_encoder(extra_detail)
        # WWW-Authenticate 등 HTTPException이 동반한 헤더를 보존
        return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(
        _request: Request, _exc: Exception
    ) -> JSONResponse:
        # 미처리 예외(DB 다운 등)도 표준 envelope로 변환. 내부 상세는 노출하지 않는다(AR12).
        return JSONResponse(
            status_code=500,
            content={"code": "internal_error", "message": "서버 내부 오류가 발생했습니다."},
        )


app = FastAPI(title="gosoom API", version="0.0.0")

# CORS — 파싱된 명시 오리진 list만 허용(AR14)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


# ---- 라우터: /api/v1 ----

router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=None)
async def health(
    session: AsyncSession = Depends(get_db),
) -> dict[str, str] | JSONResponse:
    """DB 연결(`SELECT 1`)을 포함한 헬스체크 (AC1). DB 실패 시 503."""
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "error", "db": "fail"})
    return {"status": "ok", "db": "ok"}


app.include_router(router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(service_requests_router)
app.include_router(pros_router)
app.include_router(quotes_router)
app.include_router(chat_router)
app.include_router(admin_router)
