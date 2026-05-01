from __future__ import annotations
from datetime import date as date_type, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, not_, exists
from dateutil.relativedelta import relativedelta
from src.db.models import (
    Subscription, UserActivityDaily, UserLastActivity,
    MemberRaw, KpiSnapshot, PaymentNormalized, Cohort, RetentionFact
)


async def calculate_chat_active_30(db: AsyncSession) -> int:
    today = date_type.today()
    result = await db.execute(
        select(func.count(func.distinct(UserActivityDaily.user_id)))
        .where(
            UserActivityDaily.active_flag == 1,
            UserActivityDaily.date >= today - timedelta(days=30),
        )
    )
    return result.scalar() or 0


async def calculate_chat_active_7(db: AsyncSession) -> int:
    today = date_type.today()
    result = await db.execute(
        select(func.count(func.distinct(UserActivityDaily.user_id)))
        .where(
            UserActivityDaily.active_flag == 1,
            UserActivityDaily.date >= today - timedelta(days=7),
        )
    )
    return result.scalar() or 0


async def calculate_chat_never_wrote(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(MemberRaw.user_id))
        .where(
            not_(exists(
                select(UserLastActivity.user_id)
                .where(UserLastActivity.user_id == MemberRaw.user_id)
            ))
        )
    )
    return result.scalar() or 0


async def calculate_chat_silent_paying(db: AsyncSession) -> int:
    threshold = date_type.today() - timedelta(days=30)
    result = await db.execute(
        select(func.count(Subscription.user_id))
        .outerjoin(UserLastActivity, UserLastActivity.user_id == Subscription.user_id)
        .where(
            Subscription.status == "active",
            (UserLastActivity.last_message_date < threshold) |
            (UserLastActivity.last_message_date == None)
        )
    )
    return result.scalar() or 0


async def build_kpi_snapshot(db: AsyncSession) -> KpiSnapshot:
    mrr_result = await db.execute(
        select(func.coalesce(func.sum(Subscription.monthly_price), 0))
        .where(Subscription.status == "active")
    )
    active_result = await db.execute(
        select(func.count()).where(Subscription.status == "active")
    )
    kpi = KpiSnapshot(
        date=date_type.today(),
        active_subscriptions=active_result.scalar() or 0,
        mrr=Decimal(str(mrr_result.scalar() or 0)),
        chat_active_30=await calculate_chat_active_30(db),
        chat_active_7=await calculate_chat_active_7(db),
        chat_never_wrote=await calculate_chat_never_wrote(db),
        chat_silent_paying=await calculate_chat_silent_paying(db),
    )
    await db.merge(kpi)
    await db.commit()
    return kpi


async def build_cohorts(db: AsyncSession) -> int:
    rows = await db.execute(
        select(
            func.date_trunc('month', PaymentNormalized.payment_date).label("cohort_month"),
            func.count(func.distinct(PaymentNormalized.user_id)).label("size"),
            func.min(PaymentNormalized.payment_date).label("first"),
        ).group_by(func.date_trunc('month', PaymentNormalized.payment_date))
    )
    count = 0
    for r in rows:
        cohort_month = r.cohort_month
        if hasattr(cohort_month, 'date'):
            cohort_month = cohort_month.date()
        cohort_month = cohort_month.replace(day=1)
        await db.merge(Cohort(
            cohort_month=cohort_month,
            cohort_size=r.size,
            first_payment_date=r.first,
        ))
        count += 1
    await db.commit()
    return count


async def build_retention(db: AsyncSession) -> int:
    cohorts = await db.execute(select(Cohort))
    today = date_type.today().replace(day=1)
    count = 0
    for cohort in cohorts.scalars():
        cohort_users_result = await db.execute(
            select(func.distinct(PaymentNormalized.user_id))
            .where(
                func.date_trunc('month', PaymentNormalized.payment_date) ==
                cohort.cohort_month
            )
        )
        user_ids = [r[0] for r in cohort_users_result]
        if not user_ids:
            continue
        check_month = cohort.cohort_month
        offset = 0
        while check_month <= today:
            next_month = check_month + relativedelta(months=1)
            sub_n = (await db.execute(
                select(func.count(func.distinct(Subscription.user_id)))
                .where(Subscription.user_id.in_(user_ids), Subscription.status == "active")
            )).scalar() or 0
            bill_n = (await db.execute(
                select(func.count(func.distinct(PaymentNormalized.user_id)))
                .where(
                    PaymentNormalized.user_id.in_(user_ids),
                    PaymentNormalized.payment_date >= check_month,
                    PaymentNormalized.payment_date < next_month,
                )
            )).scalar() or 0
            eng_n = (await db.execute(
                select(func.count(func.distinct(UserActivityDaily.user_id)))
                .where(
                    UserActivityDaily.user_id.in_(user_ids),
                    UserActivityDaily.date >= check_month,
                    UserActivityDaily.date < next_month,
                    UserActivityDaily.active_flag == 1,
                )
            )).scalar() or 0
            size = max(cohort.cohort_size, 1)
            await db.merge(RetentionFact(
                cohort_month=cohort.cohort_month,
                month_offset=offset,
                users_active=eng_n,
                users_paid=bill_n,
                retention_subscription=round(sub_n / size * 100, 2),
                retention_billing=round(bill_n / size * 100, 2),
                retention_engagement=round(eng_n / size * 100, 2),
            ))
            count += 1
            check_month = next_month
            offset += 1
    await db.commit()
    return count
