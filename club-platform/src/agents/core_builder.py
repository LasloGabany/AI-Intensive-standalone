from __future__ import annotations
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from src.db.models import MemberRaw, PaymentRaw, Subscription


def _detect_interval_count(subscription_until: datetime | None, payment_date: datetime) -> int:
    """Infer months covered from subscription end date and payment date."""
    if not subscription_until:
        return 1
    delta_days = (subscription_until - payment_date).days
    if delta_days > 300:
        return 12
    if delta_days > 60:
        return 3
    return 1


async def build_subscriptions(db: AsyncSession) -> int:
    """
    Upsert subscriptions from members_raw + payments_raw.
    monthly_price = amount_last_payment / plan_interval_count.
    MRR is ONLY calculated from this table.
    """
    members = await db.execute(select(MemberRaw))
    count = 0
    for m in members.scalars():
        last_pay_result = await db.execute(
            select(PaymentRaw)
            .where(PaymentRaw.user_id == m.user_id, PaymentRaw.status == "completed")
            .order_by(PaymentRaw.date.desc())
            .limit(1)
        )
        payment = last_pay_result.scalar_one_or_none()

        interval_count = None
        monthly_price = None
        if payment and m.subscription_until:
            pay_date = payment.date if payment.date.tzinfo else payment.date.replace(tzinfo=timezone.utc)
            sub_until = m.subscription_until if m.subscription_until.tzinfo else m.subscription_until.replace(tzinfo=timezone.utc)
            interval_count = _detect_interval_count(sub_until, pay_date)
            monthly_price = Decimal(str(payment.amount)) / interval_count

        sub = Subscription(
            user_id=m.user_id,
            status=m.status or "expired",
            current_period_end=m.subscription_until,
            plan_interval_count=interval_count,
            amount_last_payment=payment.amount if payment else None,
            monthly_price=monthly_price,
            source="getcourse",
        )
        await db.merge(sub)
        count += 1
    await db.commit()
    return count


async def calculate_mrr(db: AsyncSession) -> Decimal:
    """MRR = SUM(monthly_price) WHERE status='active'. Never from payments_raw."""
    result = await db.execute(
        text("SELECT COALESCE(SUM(monthly_price), 0) FROM subscriptions WHERE status='active'")
    )
    return Decimal(str(result.scalar()))
