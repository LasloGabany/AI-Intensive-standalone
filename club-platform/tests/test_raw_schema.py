import pytest
from sqlalchemy import text

@pytest.mark.asyncio
async def test_messages_raw_has_required_columns(engine):
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='messages_raw'"
        ))
        cols = {row[0] for row in result}
    assert {'message_id','date','from_id','text','chat_id',
            'topic_id','topic_name','ingested_at'} <= cols

@pytest.mark.asyncio
async def test_payments_raw_has_required_columns(engine):
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='payments_raw'"
        ))
        cols = {row[0] for row in result}
    assert {'order_id','user_id','amount','date','status','raw_json','ingested_at'} <= cols

@pytest.mark.asyncio
async def test_members_raw_has_required_columns(engine):
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='members_raw'"
        ))
        cols = {row[0] for row in result}
    assert {'user_id','name','username','join_date','status',
            'subscription_until','chat_member','raw_json','ingested_at','updated_at'} <= cols
