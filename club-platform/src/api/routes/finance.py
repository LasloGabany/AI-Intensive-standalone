from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.connection import get_db
from src.db.models import MrrDailySnapshot
from src.api import cache

router = APIRouter()


@router.get("/api/finance")
async def get_finance(db: AsyncSession = Depends(get_db)):
    cached = cache.get("finance")
    if cached:
        return cached
    snaps = (await db.execute(select(MrrDailySnapshot).order_by(MrrDailySnapshot.date))).scalars().all()
    data = {
        "revenueByMonth": [
            {"month": s.date.strftime("%b %y"), "revenue": float(s.mrr or 0), "orders": s.active_users or 0}
            for s in snaps
        ],
        "cohorts": [],
    }
    cache.set("finance", data)
    return data
