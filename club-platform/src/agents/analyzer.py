from __future__ import annotations
import json
from datetime import date, timedelta
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.config import settings
from src.db.models import MessageRaw, AnalyzedOutput

PROMPT_VERSION = "1.0"
client = AsyncAnthropic(api_key=settings.anthropic_api_key)

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
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(MessageRaw.text)
        .where(MessageRaw.date >= since, MessageRaw.text != None)
        .order_by(func.random())
        .limit(500)
    )
    messages = [r[0] for r in result if r[0] and len(r[0]) > 5]
    if not messages:
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

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text
    start, end = raw.find("{"), raw.rfind("}") + 1
    data = json.loads(raw[start:end])

    await db.merge(AnalyzedOutput(
        analysis_type="insights",
        period="latest",
        json_data=data,
        prompt_version=PROMPT_VERSION,
    ))
    await db.commit()
    return data


async def run(db: AsyncSession):
    await analyze_insights(db)
