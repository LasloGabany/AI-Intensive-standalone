from __future__ import annotations
import json
import logging
from datetime import date, timedelta
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.config import settings
from src.db.models import MessageRaw, AnalyzedOutput

logger = logging.getLogger(__name__)

PROMPT_VERSION = "1.0"

INSIGHTS_SCHEMA = """{
  "totalMessages": int,
  "analysisDate": "YYYY-MM-DD",
  "topics": [{"title":"","mentions":0,"description":"","aiInsight":"","quotes":["",""]}],
  "hiddenNeeds": [{"impact":"high|medium|low","title":"","signal":""}],
  "recommendations": [{"rank":1,"title":"","description":"","priority":"high|medium","effort":""}],
  "engagementDrivers": [{"title":"","description":""}]
}"""


async def analyze_insights(db: AsyncSession, days: int = 30) -> dict:
    """
    Run LLM analysis on recent messages.
    LLM is NOT used for numeric KPI metrics (PRD §6.8).
    Results stored with prompt_version for reproducibility.
    """
    from src.api.settings_service import get_setting
    api_key = await get_setting(db, "anthropic_api_key", settings.anthropic_api_key)
    client = AsyncAnthropic(api_key=api_key)
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(MessageRaw.text)
        .where(MessageRaw.date >= since, MessageRaw.text != None)
        .order_by(func.random())
        .limit(500)
    )
    messages = [r[0] for r in result if r[0] and len(r[0]) > 5]
    if not messages:
        logger.warning("No messages found for analysis period — skipping.")
        return {}

    prompt = (
        f"Ты — аналитик онлайн-сообществ. Проанализируй {len(messages)} сообщений участниц клуба.\n"
        f"Верни строго JSON без markdown по схеме:\n{INSIGHTS_SCHEMA}\n\n"
        "Правила:\n"
        "- Темы ранжируй по числу упоминаний\n"
        "- 3 реальные цитаты на каждую тему (дословно из текста)\n"
        "- aiInsight — неочевидный вывод для владельца, не пересказ темы\n\n"
        "СООБЩЕНИЯ:\n" + "\n".join(messages[:300])
    )

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        if not response.content:
            logger.warning("LLM returned empty content list — skipping.")
            return {}
        raw = response.content[0].text
        start, end = raw.find("{"), raw.rfind("}") + 1
        data = json.loads(raw[start:end])
    except Exception as exc:
        logger.warning("LLM call or JSON parsing failed: %s", exc)
        return {}

    stmt = pg_insert(AnalyzedOutput).values(
        analysis_type="insights",
        period="latest",
        json_data=data,
        prompt_version=PROMPT_VERSION,
    ).on_conflict_do_update(
        index_elements=["analysis_type", "period"],
        set_=dict(json_data=data, prompt_version=PROMPT_VERSION, created_at=func.now()),
    )

    try:
        await db.execute(stmt)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return data


async def run(db: AsyncSession):
    await analyze_insights(db)
