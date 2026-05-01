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
