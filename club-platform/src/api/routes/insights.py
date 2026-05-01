from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.connection import get_db
from src.db.models import AnalyzedOutput
from src.api import cache

router = APIRouter()


@router.get("/api/insights")
async def get_insights(db: AsyncSession = Depends(get_db)):
    cached = cache.get("insights")
    if cached:
        return cached
    ins = (await db.execute(
        select(AnalyzedOutput)
        .where(AnalyzedOutput.analysis_type == "insights")
        .order_by(AnalyzedOutput.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    emo = (await db.execute(
        select(AnalyzedOutput)
        .where(AnalyzedOutput.analysis_type == "emotions")
        .order_by(AnalyzedOutput.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    data = {**(ins.json_data if ins else {}), "emotions": emo.json_data if emo else {}}
    cache.set("insights", data)
    return data
