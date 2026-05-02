from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import kpi, retention, health, finance, insights
from src.api.routes import admin as admin_router
from src.scheduler import start as start_scheduler, scheduler, reschedule_job, _DEFAULT_SCHEDULES
from src.api.settings_service import get_setting

logger = logging.getLogger(__name__)


async def _load_schedules_from_db() -> None:
    from src.db.connection import SessionLocal
    async with SessionLocal() as db:
        for key, default in _DEFAULT_SCHEDULES.items():
            cron = await get_setting(db, f"schedule_{key}", default)
            if cron != default:
                try:
                    reschedule_job(key, cron)
                except Exception as exc:
                    logger.warning("Could not apply saved schedule for %s: %s", key, exc)


@asynccontextmanager
async def lifespan(app):
    try:
        start_scheduler()
    except Exception:
        pass  # skip in test context
    try:
        await _load_schedules_from_db()
    except Exception as exc:
        logger.warning("Could not load schedules from DB on startup: %s", exc)
    yield


app = FastAPI(title="Club Platform API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

for router in (kpi.router, retention.router, health.router, finance.router, insights.router):
    app.include_router(router)

app.include_router(admin_router.router)


@app.get("/api/dashboard")
async def get_dashboard(
    kpi_data: dict = Depends(kpi.get_kpi),
    ret_data: dict = Depends(retention.get_retention),
    fin_data: dict = Depends(finance.get_finance),
    ins_data: dict = Depends(insights.get_insights),
    hlt_data: dict = Depends(health.get_health),
):
    return {
        "KPI": kpi_data,
        "RETENTION": ret_data,
        "FINANCES": fin_data,
        "INSIGHTS": ins_data,
        "EMOTIONS_DATA": ins_data.get("emotions", {}),
        "SILENT_DATA": hlt_data.get("silent", []),
        "LEADERBOARD_DATA": hlt_data.get("leaderboard", []),
        "ACTIVITY_DATA": hlt_data.get("activity", {}),
    }
