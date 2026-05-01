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
