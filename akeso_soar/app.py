"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from akeso_soar.api.auth import router as auth_router
from akeso_soar.api.users import router as users_router
from akeso_soar.config import settings
from akeso_soar.db import engine
from akeso_soar.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("akeso_soar.startup", env=settings.app_env)
    yield
    await engine.dispose()
    logger.info("akeso_soar.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AkesoSOAR",
        description="Security Orchestration, Automation, and Response Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(users_router)

    @app.get("/api/v1/health")
    async def health_check():
        db_status = "disconnected"
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                db_status = "connected"
        except Exception:
            logger.warning("health_check.db_failed")

        return {"status": "ok" if db_status == "connected" else "degraded", "database": db_status}

    return app
