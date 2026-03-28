"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from akeso_soar.api.alerts import router as alerts_router
from akeso_soar.api.audit import router as audit_router
from akeso_soar.api.auth import router as auth_router
from akeso_soar.api.connectors import router as connectors_router
from akeso_soar.api.coverage import router as coverage_router
from akeso_soar.api.executions import router as executions_router
from akeso_soar.api.human_tasks import router as human_tasks_router
from akeso_soar.api.playbooks import router as playbooks_router
from akeso_soar.api.use_cases import router as use_cases_router
from akeso_soar.api.users import router as users_router
from akeso_soar.api.websocket import router as ws_router
from akeso_soar.config import settings
from akeso_soar.db import engine
from akeso_soar.logging import get_logger, setup_logging
from akeso_soar.services.alert_poller import start_poller, stop_poller

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("akeso_soar.startup", env=settings.app_env)
    start_poller()
    yield
    stop_poller()
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
    app.include_router(alerts_router)
    app.include_router(use_cases_router)
    app.include_router(playbooks_router)
    app.include_router(executions_router)
    app.include_router(audit_router)
    app.include_router(connectors_router)
    app.include_router(coverage_router)
    app.include_router(human_tasks_router)
    app.include_router(ws_router)

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
