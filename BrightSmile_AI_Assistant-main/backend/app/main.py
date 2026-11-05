from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, auth, cases, health, predictions
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.dependencies import get_storage
from app.services.predictor import load_predictor

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    load_predictor()  # load model exactly once at startup
    get_storage()  # forces init_schema() to run before any request arrives
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix=settings.api_v1_prefix)
    app.include_router(health.router, prefix=settings.api_v1_prefix)
    app.include_router(predictions.router, prefix=settings.api_v1_prefix)
    app.include_router(cases.router, prefix=settings.api_v1_prefix)
    app.include_router(admin.router, prefix=settings.api_v1_prefix)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error('"unhandled error" path=%s error_type=%s' % (request.url.path, type(exc).__name__))
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "detail": "an unexpected error occurred"},
        )

    return app


app = create_app()
