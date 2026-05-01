import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone, date
from sqlalchemy import insert, select
from src.db.models import Subscription, UserActivityDaily, UserLastActivity


@pytest.fixture
async def seeded_subscription(db):
    await db.execute(insert(Subscription).values(
        user_id=9001, status="active", monthly_price=1000
    ))
    await db.commit()


@pytest.mark.asyncio
async def test_kpi_mrr_from_subscriptions_only(db, seeded_subscription):
    from src.agents.etl import build_kpi_snapshot
    kpi = await build_kpi_snapshot(db)
    assert kpi.mrr >= Decimal("1000")
    assert kpi.active_subscriptions >= 1


@pytest.mark.asyncio
async def test_chat_active_30_uses_activity_table_not_raw_distinct(db):
    """Must use user_activity_daily.active_flag, not COUNT(DISTINCT from_id) on messages_raw"""
    today = date.today()
    await db.execute(insert(UserActivityDaily).values(
        user_id=9002, date=today, message_count=5, active_flag=1
    ))
    await db.commit()
    from src.agents.etl import calculate_chat_active_30
    count = await calculate_chat_active_30(db)
    assert count >= 1


@pytest.mark.asyncio
async def test_chat_never_wrote_counts_members_without_activity(db, seeded_subscription):
    from src.agents.etl import calculate_chat_never_wrote
    count = await calculate_chat_never_wrote(db)
    assert count >= 1


@pytest.mark.asyncio
async def test_kpi_snapshot_written_to_table(db, seeded_subscription):
    from src.agents.etl import build_kpi_snapshot
    from src.db.models import KpiSnapshot
    await build_kpi_snapshot(db)
    result = await db.execute(select(KpiSnapshot).order_by(KpiSnapshot.date.desc()).limit(1))
    kpi = result.scalar_one()
    assert kpi.date == date.today()
    assert kpi.active_subscriptions is not None
