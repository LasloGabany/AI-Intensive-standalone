from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.connection import get_db
from src.db.models import UserHealth, MemberRaw
from src.api import cache

router = APIRouter()


@router.get("/api/health")
async def get_health(db: AsyncSession = Depends(get_db)):
    cached = cache.get("health")
    if cached:
        return cached
    rows = (await db.execute(
        select(UserHealth, MemberRaw)
        .join(MemberRaw, MemberRaw.user_id == UserHealth.user_id)
        .order_by(UserHealth.risk_score.desc())
    )).all()
    silent = [{
        "name": m.name or "",
        "username": m.username,
        "subscriptionActive": h.risk_segment not in ("expired",),
        "subscriptionUntil": m.subscription_until.isoformat() if m.subscription_until else None,
        "silentDays": h.silent_days,
        "risk": h.risk_segment,
        "postCount": 0,
        "miniApp": False,
    } for h, m in rows]
    data = {"agents": {"status": "ok"}, "silent": silent, "leaderboard": [], "activity": {}}
    cache.set("health", data)
    return data
