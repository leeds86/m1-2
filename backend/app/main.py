import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.api_core.exceptions import GoogleAPIError

from app.config import Settings
from app.errors import AppError
from app.limiter import RateLimiter
from app.providers import OpenAIResponder, UpbitClient
from app.routers import chat, conversations, data


def create_app(settings=None, store=None, ai_client=None, market_client=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application):
        yield
        client = application.state.market_client
        if isinstance(client, UpbitClient):
            client.client.close()

    application = FastAPI(title="Coin Context API", version="1.0.0",
                          description="업비트 완료 일봉·기술지표를 근거로 설명하는 코인 분석 AI 비서", lifespan=lifespan)
    application.state.settings = settings
    application.state.store = store
    application.state.market_client = market_client or UpbitClient()
    application.state.ai_client = ai_client or (OpenAIResponder(settings.openai_api_key, settings.openai_model,
                                                              base_url=settings.openai_base_url)
                                                if settings.openai_api_key else None)
    application.state.limiter = RateLimiter()
    application.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins),
                               allow_methods=["GET", "POST", "PUT", "DELETE"],
                               allow_headers=["Content-Type", "X-Client-Id"])

    @application.exception_handler(AppError)
    async def app_error(request: Request, error: AppError):
        return JSONResponse(status_code=error.status, content={"detail": error.detail})

    async def storage_error(request: Request, error):
        return JSONResponse(status_code=503, content={"detail": "저장소 처리에 실패했습니다. 연결·서비스 계정 권한을 확인하세요."})

    application.add_exception_handler(GoogleAPIError, storage_error)
    application.add_exception_handler(sqlite3.Error, storage_error)

    @application.get("/health", tags=["상태"])
    def health():
        return {"status": "ok", "storage": settings.storage_backend,
                "ai_configured": bool(application.state.ai_client),
                "firebase_configured": bool(settings.firebase_json or settings.firebase_path)}

    application.include_router(data.router)
    application.include_router(conversations.router)
    application.include_router(chat.router)
    return application


app = create_app()
