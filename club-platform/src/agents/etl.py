from __future__ import annotations
from datetime import date as date_type, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, not_, exists
from src.db.models import (
    Subscription, UserActivityDaily, UserLastActivity,
    MemberRaw, KpiSnapshot
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
