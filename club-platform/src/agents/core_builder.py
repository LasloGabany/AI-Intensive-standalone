from __future__ import annotations
from decimal import Decimal
from datetime import datetime, timezone
from datetime import date as _date_type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func, cast
from sqlalchemy.types import Integer as SAInteger, Date
from src.db.models import MemberRaw, PaymentRaw, Subscription, MessageRaw, UserActivityDaily, UserLastActivity, PaymentNormalized
from src.config import settings


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


async def build_activity_daily(db: AsyncSession, since: _date_type | None = None) -> int:
    """
    Aggregate messages_raw → user_activity_daily.
    Incremental: only processes messages since `since` date.
    active_flag = 1 if message_count > 0. Never use COUNT(DISTINCT) on raw.
    """
    if since is None:
        since = _date_type(2000, 1, 1)

    rows = await db.execute(
        select(
            cast(func.date_trunc('day', MessageRaw.date), Date).label("day"),
            MessageRaw.from_id,
            func.count().label("total"),
            func.sum(
                cast(MessageRaw.topic_name == settings.diary_topic_name, SAInteger)
            ).label("diary"),
        )
        .where(cast(func.date_trunc('day', MessageRaw.date), Date) >= since)
        .group_by(
            cast(func.date_trunc('day', MessageRaw.date), Date),
            MessageRaw.from_id,
        )
    )

    count = 0
    for row in rows:
        await db.merge(UserActivityDaily(
            user_id=row.from_id,
            date=row.day,
            message_count=row.total,
            diary_count=row.diary or 0,
            active_flag=1 if row.total > 0 else 0,
        ))
        count += 1

    # Update user_last_activity from all messages (not just `since`)
    agg = await db.execute(
        select(
            MessageRaw.from_id,
            func.min(cast(func.date_trunc('day', MessageRaw.date), Date)).label("first"),
            func.max(cast(func.date_trunc('day', MessageRaw.date), Date)).label("last"),
            func.count().label("total"),
        ).group_by(MessageRaw.from_id)
    )
    for u in agg:
        await db.merge(UserLastActivity(
            user_id=u.from_id,
            first_message_date=u.first,
            last_message_date=u.last,
            total_messages=u.total,
        ))

    await db.commit()
    return count


async def build_payments_normalized(db: AsyncSession) -> int:
    await db.execute(text("DELETE FROM payments_normalized"))
    await db.commit()
    subs = await db.execute(select(Subscription))
    count = 0
    for sub in subs.scalars():
        payment = await db.execute(
            select(PaymentRaw)
            .where(PaymentRaw.user_id == sub.user_id, PaymentRaw.status == "completed")
            .order_by(PaymentRaw.date.desc())
            .limit(1)
        )
        p = payment.scalar_one_or_none()
        if not p:
            continue
        pay_date = p.date.date() if hasattr(p.date, 'date') else p.date
        norm = PaymentNormalized(
            user_id=sub.user_id,
            payment_date=pay_date,
            amount=p.amount,
            months_covered=sub.plan_interval_count or 1,
            source="getcourse",
        )
        db.add(norm)
        count += 1
    await db.commit()
    return count
