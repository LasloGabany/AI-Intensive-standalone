from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.connection import get_db
from src.db.models import Cohort, RetentionFact
from src.api import cache

router = APIRouter()


@router.get("/api/retention")
async def get_retention(db: AsyncSession = Depends(get_db)):
    cached = cache.get("retention")
    if cached:
        return cached
    cohorts = (await db.execute(select(Cohort).order_by(Cohort.cohort_month))).scalars().all()
    facts = (await db.execute(
        select(RetentionFact).order_by(RetentionFact.cohort_month, RetentionFact.month_offset)
    )).scalars().all()
    fact_map: dict = {}
    for f in facts:
        key = f.cohort_month.isoformat()
        fact_map.setdefault(key, []).append(float(f.retention_subscription or 0))
    result = [
        {"label": c.cohort_month.strftime("%b %y"), "n": c.cohort_size,
         "values": fact_map.get(c.cohort_month.isoformat(), [])}
        for c in cohorts
    ]
    data = {"cohorts": result}
    cache.set("retention", data)
    return data
