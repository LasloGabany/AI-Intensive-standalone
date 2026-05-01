import pytest
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_upsert_messages_deduplicates_by_message_id(db):
    from src.agents.collector_tg import upsert_messages
    messages = [
        {"message_id": 101, "date": datetime.now(timezone.utc), "from_id": 1001,
         "text": "hello", "chat_id": -100123, "topic_id": 1, "topic_name": "general"},
        {"message_id": 101, "date": datetime.now(timezone.utc), "from_id": 1001,
         "text": "hello", "chat_id": -100123, "topic_id": 1, "topic_name": "general"},
    ]
    count = await upsert_messages(db, messages)
    assert count == 1  # second insert ignored by ON CONFLICT DO NOTHING


@pytest.mark.asyncio
async def test_upsert_payments_deduplicates_by_order_id(db):
    from src.agents.collector_gc import upsert_payments
    payments = [
        {"order_id": "GC-001", "user_id": 5001, "amount": 2990,
         "date": "2026-04-01T00:00:00Z", "status": "completed"},
        {"order_id": "GC-001", "user_id": 5001, "amount": 2990,
         "date": "2026-04-01T00:00:00Z", "status": "completed"},
    ]
    count = await upsert_payments(db, payments)
    assert count == 1
