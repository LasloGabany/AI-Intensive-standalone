from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.connection import get_db
from src.api.routes import kpi, retention, health, finance, insights
from src.scheduler import start as start_scheduler


@asynccontextmanager
async def lifespan(app):
    start_scheduler()
    yield


app = FastAPI(title="Club Platform API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

for router in (kpi.router, retention.router, health.router, finance.router, insights.router):
    app.include_router(router)


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
