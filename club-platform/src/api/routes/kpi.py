from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.connection import get_db
from src.db.models import KpiSnapshot
from src.api import cache

router = APIRouter()


@router.get("/api/kpi")
async def get_kpi(db: AsyncSession = Depends(get_db)):
    cached = cache.get("kpi")
    if cached:
        return cached
    result = await db.execute(select(KpiSnapshot).order_by(KpiSnapshot.date.desc()).limit(1))
    kpi = result.scalar_one_or_none()
    data = {
        "active_subscriptions": kpi.active_subscriptions if kpi else 0,
        "mrr": float(kpi.mrr) if kpi and kpi.mrr else 0,
        "chat_active_30": kpi.chat_active_30 if kpi else 0,
        "chat_active_7": kpi.chat_active_7 if kpi else 0,
        "chat_never_wrote": kpi.chat_never_wrote if kpi else 0,
        "chat_silent_paying": kpi.chat_silent_paying if kpi else 0,
        "updated_at": kpi.date.isoformat() if kpi else None,
    }
    cache.set("kpi", data)
    return data
