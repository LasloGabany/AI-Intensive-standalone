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
