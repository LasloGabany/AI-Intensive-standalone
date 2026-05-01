from __future__ import annotations
from datetime import date as date_type, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, not_, exists
from dateutil.relativedelta import relativedelta
from src.db.models import (
    Subscription, UserActivityDaily, UserLastActivity,
    MemberRaw, KpiSnapshot, PaymentNormalized, Cohort, RetentionFact, UserHealth
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


async def build_user_health(db: AsyncSession) -> int:
    today = date_type.today()
    subs = await db.execute(select(Subscription))
    count = 0
    for sub in subs.scalars():
        last = await db.execute(
            select(UserLastActivity).where(UserLastActivity.user_id == sub.user_id)
        )
        activity = last.scalar_one_or_none()
        total_messages = activity.total_messages if activity else 0
        last_msg = activity.last_message_date if activity else None
        first_msg = activity.first_message_date if activity else None

        silent_days = (today - last_msg).days if last_msg else 9999
        tenure_days = (today - first_msg).days if first_msg else 0

        score_res = await db.execute(
            select(func.coalesce(func.sum(UserActivityDaily.active_flag), 0))
            .where(
                UserActivityDaily.user_id == sub.user_id,
                UserActivityDaily.date >= today - timedelta(days=30),
            )
        )
        activity_score = float(score_res.scalar() or 0)
        # risk_score = supplementary metric, not sole decider (PRD §6.3)
        risk_score = round(
            silent_days * 0.4 + (1 / max(activity_score, 0.1)) * 0.3 + (tenure_days / 30) * 0.3,
            2
        )
        if sub.status != "active":
            segment = "expired"
        elif total_messages == 0:
            segment = "ghost"
        elif silent_days >= 30 and tenure_days > 60:
            segment = "high_risk"
        elif silent_days >= 14:
            segment = "medium"
        else:
            segment = "healthy"

        await db.merge(UserHealth(
            user_id=sub.user_id,
            silent_days=silent_days if silent_days < 9999 else None,
            tenure_days=tenure_days,
            monthly_price=sub.monthly_price,
            activity_score=activity_score,
            risk_score=risk_score,
            risk_segment=segment,
        ))
        count += 1
    await db.commit()
    return count
