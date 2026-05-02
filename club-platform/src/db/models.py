from __future__ import annotations

from datetime import datetime
from datetime import date as date_type
from typing import Optional
from sqlalchemy import BigInteger, Text, Numeric, Boolean, JSON, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column
from src.db.connection import Base


class MessageRaw(Base):
    __tablename__ = "messages_raw"
    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    date: Mapped[datetime] = mapped_column(nullable=False, index=True)
    from_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    text: Mapped[Optional[str]] = mapped_column(Text)
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    topic_id: Mapped[Optional[int]] = mapped_column(Integer)
    topic_name: Mapped[Optional[str]] = mapped_column(Text)
    ingested_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class PaymentRaw(Base):
    __tablename__ = "payments_raw"
    order_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    date: Mapped[datetime] = mapped_column(nullable=False, index=True)
    status: Mapped[Optional[str]] = mapped_column(Text)
    raw_json: Mapped[Optional[dict]] = mapped_column(JSON)
    ingested_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class MemberRaw(Base):
    __tablename__ = "members_raw"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    username: Mapped[Optional[str]] = mapped_column(Text)
    join_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text)
    subscription_until: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    chat_member: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_json: Mapped[Optional[dict]] = mapped_column(JSON)
    ingested_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    current_period_start: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    billing_anchor_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    cancel_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    plan_interval: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_interval_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amount_last_payment: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    monthly_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class UserActivityDaily(Base):
    __tablename__ = "user_activity_daily"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    date: Mapped[date_type] = mapped_column(primary_key=True, index=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    diary_count: Mapped[int] = mapped_column(Integer, default=0)
    replies_count: Mapped[int] = mapped_column(Integer, default=0)
    passive_events_count: Mapped[int] = mapped_column(Integer, default=0)
    active_flag: Mapped[int] = mapped_column(SmallInteger, default=0)


class UserLastActivity(Base):
    __tablename__ = "user_last_activity"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    first_message_date: Mapped[Optional[date_type]] = mapped_column(nullable=True)
    last_message_date: Mapped[Optional[date_type]] = mapped_column(nullable=True)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class PaymentNormalized(Base):
    __tablename__ = "payments_normalized"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    payment_date: Mapped[date_type] = mapped_column(nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    period_start: Mapped[Optional[date_type]] = mapped_column(nullable=True)
    period_end: Mapped[Optional[date_type]] = mapped_column(nullable=True)
    months_covered: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class KpiSnapshot(Base):
    __tablename__ = "kpi_snapshot"
    date: Mapped[date_type] = mapped_column(primary_key=True)
    active_subscriptions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mrr: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    chat_active_30: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chat_active_7: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chat_never_wrote: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chat_silent_paying: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Cohort(Base):
    __tablename__ = "cohorts"
    cohort_month: Mapped[date_type] = mapped_column(primary_key=True)
    cohort_size: Mapped[int] = mapped_column(Integer)
    first_payment_date: Mapped[Optional[date_type]] = mapped_column(nullable=True)


class RetentionFact(Base):
    __tablename__ = "retention_fact"
    cohort_month: Mapped[date_type] = mapped_column(primary_key=True)
    month_offset: Mapped[int] = mapped_column(Integer, primary_key=True)
    users_active: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    users_paid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retention_subscription: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    retention_billing: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    retention_engagement: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)


class UserHealth(Base):
    __tablename__ = "user_health"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    silent_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tenure_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    monthly_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    activity_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    risk_segment: Mapped[Optional[str]] = mapped_column(Text, index=True, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class MrrDailySnapshot(Base):
    __tablename__ = "mrr_daily_snapshot"
    date: Mapped[date_type] = mapped_column(primary_key=True)
    mrr: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    active_users: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class ChurnEvent(Base):
    __tablename__ = "churn_events"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    churn_date: Mapped[date_type] = mapped_column(primary_key=True)
    tenure_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_activity: Mapped[Optional[date_type]] = mapped_column(nullable=True)


class ExpansionEvent(Base):
    __tablename__ = "expansion_events"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_date: Mapped[date_type] = mapped_column(primary_key=True)
    old_mrr: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    new_mrr: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)


class RetentionByActivity(Base):
    __tablename__ = "retention_by_activity"
    activity_bucket: Mapped[str] = mapped_column(Text, primary_key=True)
    cohort_month: Mapped[date_type] = mapped_column(primary_key=True)
    retention_30d: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    retention_90d: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)


class ChurnProbability(Base):
    __tablename__ = "churn_probability"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    probability_30d: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    contributing_factors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class ArpuBySegment(Base):
    __tablename__ = "arpu_by_segment"
    activity_segment: Mapped[str] = mapped_column(Text, primary_key=True)
    avg_revenue: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    user_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_tenure: Mapped[Optional[float]] = mapped_column(Numeric(6, 1), nullable=True)


class AnalyzedOutput(Base):
    __tablename__ = "analyzed_output"
    analysis_type: Mapped[str] = mapped_column(Text, primary_key=True)
    period: Mapped[str] = mapped_column(Text, primary_key=True)
    json_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    prompt_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class PlatformSetting(Base):
    __tablename__ = "platform_settings"
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
