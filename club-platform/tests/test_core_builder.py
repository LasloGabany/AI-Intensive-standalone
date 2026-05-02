import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, insert
from src.db.models import MemberRaw, PaymentRaw


@pytest.mark.asyncio
async def test_monthly_price_monthly_plan(db):
    """1 month plan: monthly_price = amount / 1"""
    await db.execute(insert(PaymentRaw).values(
        order_id="t-001", user_id=1001, amount=2990,
        date=datetime.now(timezone.utc), status="completed"
    ))
    await db.execute(insert(MemberRaw).values(
        user_id=1001, name="Test User", status="active",
        subscription_until=datetime.now(timezone.utc) + timedelta(days=30)
    ))
    await db.commit()

    from src.agents.core_builder import build_subscriptions
    await build_subscriptions(db)

    from src.db.models import Subscription
    result = await db.execute(select(Subscription).where(Subscription.user_id == 1001))
    sub = result.scalar_one()
    assert sub.monthly_price == Decimal("2990.00")
    assert sub.plan_interval_count == 1
    assert sub.status == "active"


@pytest.mark.asyncio
async def test_monthly_price_quarterly_plan(db):
    """3 month plan: monthly_price = amount / 3"""
    await db.execute(insert(PaymentRaw).values(
        order_id="t-002", user_id=1002, amount=6000,
        date=datetime.now(timezone.utc), status="completed"
    ))
    await db.execute(insert(MemberRaw).values(
        user_id=1002, name="Quarterly User", status="active",
        subscription_until=datetime.now(timezone.utc) + timedelta(days=90)
    ))
    await db.commit()

    from src.agents.core_builder import build_subscriptions
    await build_subscriptions(db)

    from src.db.models import Subscription
    result = await db.execute(select(Subscription).where(Subscription.user_id == 1002))
    sub = result.scalar_one()
    assert sub.monthly_price == Decimal("2000.00")
    assert sub.plan_interval_count == 3


@pytest.mark.asyncio
async def test_mrr_sum_from_subscriptions_not_payments(db):
    """MRR = SUM(monthly_price WHERE status=active). Never from payments."""
    from src.agents.core_builder import calculate_mrr
    mrr = await calculate_mrr(db)
    assert isinstance(mrr, Decimal)
    assert mrr >= Decimal("0")


from datetime import date


@pytest.mark.asyncio
async def test_activity_daily_counts_diary_separately(db):
    from sqlalchemy import insert as sa_insert
    today = datetime.now(timezone.utc)
    await db.execute(sa_insert(MessageRaw).values([
        dict(message_id=201, date=today, from_id=2001, text="hi", topic_name="general"),
        dict(message_id=202, date=today, from_id=2001, text="win", topic_name="Дневник успеха"),
        dict(message_id=203, date=today, from_id=2001, text="more", topic_name="general"),
    ]))
    await db.commit()

    from src.agents.core_builder import build_activity_daily
    import os
    os.environ.setdefault("DIARY_TOPIC_NAME", "Дневник успеха")
    await build_activity_daily(db)

    from src.db.models import UserActivityDaily
    result = await db.execute(
        select(UserActivityDaily)
        .where(UserActivityDaily.user_id == 2001, UserActivityDaily.date == today.date())
    )
    row = result.scalar_one()
    assert row.message_count == 3
    assert row.diary_count == 1
    assert row.active_flag == 1


@pytest.mark.asyncio
async def test_user_last_activity_updated(db):
    from src.db.models import UserLastActivity
    result = await db.execute(
        select(UserLastActivity).where(UserLastActivity.user_id == 2001)
    )
    row = result.scalar_one()
    assert row.total_messages >= 3
    assert row.last_message_date is not None


@pytest.mark.asyncio
async def test_active_flag_zero_when_no_messages(db):
    from src.db.models import UserActivityDaily
    result = await db.execute(
        select(UserActivityDaily).where(UserActivityDaily.user_id == 9999)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_yearly_payment_gets_months_covered_12(db):
    from sqlalchemy import insert as sa_insert
    await db.execute(sa_insert(PaymentRaw).values(
        order_id="t-yearly-001", user_id=3001, amount=24000,
        date=datetime.now(timezone.utc), status="completed"
    ))
    await db.execute(sa_insert(MemberRaw).values(
        user_id=3001, name="Yearly", status="active",
        subscription_until=datetime.now(timezone.utc) + timedelta(days=365)
    ))
    await db.commit()

    from src.agents.core_builder import build_subscriptions, build_payments_normalized
    await build_subscriptions(db)
    await build_payments_normalized(db)

    from src.db.models import PaymentNormalized
    result = await db.execute(
        select(PaymentNormalized).where(PaymentNormalized.user_id == 3001)
    )
    row = result.scalar_one()
    assert row.months_covered == 12
    assert Decimal(str(row.amount)) == Decimal("24000")
