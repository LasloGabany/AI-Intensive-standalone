from __future__ import annotations
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src.db.connection import SessionLocal
from src.agents import collector_tg, collector_gc, core_builder, etl, analyzer

scheduler = AsyncIOScheduler()
_tg_checkpoint = 0


async def run_collectors():
    global _tg_checkpoint
    async with SessionLocal() as db:
        _tg_checkpoint = await collector_tg.run(db, checkpoint=_tg_checkpoint)
        await collector_gc.run(db)


async def run_core_builder():
    async with SessionLocal() as db:
        await core_builder.build_subscriptions(db)
        await core_builder.build_activity_daily(db)
        await core_builder.build_payments_normalized(db)


async def run_kpi_etl():
    async with SessionLocal() as db:
        await etl.build_kpi_snapshot(db)
        await etl.build_mrr_snapshot(db)
        await etl.build_user_health(db)


async def run_full_etl():
    async with SessionLocal() as db:
        await etl.build_cohorts(db)
        await etl.build_retention(db)
        await etl.build_churn_events(db)
        await etl.build_arpu_by_segment(db)
        await etl.build_churn_probability(db)


async def run_analyzer():
    async with SessionLocal() as db:
        await analyzer.run(db)


def start():
    scheduler.add_job(run_collectors,   CronTrigger(hour="*/6"))
    scheduler.add_job(run_core_builder, CronTrigger(hour="*/2"))
    scheduler.add_job(run_kpi_etl,      CronTrigger(hour="*/2", minute=30))
    scheduler.add_job(run_full_etl,     CronTrigger(hour=4))
    scheduler.add_job(run_analyzer,     CronTrigger(hour=3))
    scheduler.start()
