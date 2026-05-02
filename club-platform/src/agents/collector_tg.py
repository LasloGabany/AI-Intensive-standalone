from __future__ import annotations
import httpx
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.config import settings
from src.db.models import MessageRaw, MemberRaw


async def upsert_messages(db: AsyncSession, messages: list[dict]) -> int:
    if not messages:
        return 0
    stmt = pg_insert(MessageRaw).values(messages)
    stmt = stmt.on_conflict_do_nothing(index_elements=["message_id"])
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def upsert_member(db: AsyncSession, user: dict) -> None:
    stmt = pg_insert(MemberRaw).values(
        user_id=user["id"],
        name=f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        username=user.get("username"),
        chat_member=True,
    ).on_conflict_do_update(
        index_elements=["user_id"],
        set_={
            "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "username": user.get("username"),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    await db.execute(stmt)
    await db.commit()


async def fetch_updates(db: AsyncSession, offset: int = 0) -> list[dict]:
    from src.api.settings_service import get_setting
    token = await get_setting(db, "telegram_bot_token", settings.telegram_bot_token)
    tg_api = f"https://api.telegram.org/bot{token}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{tg_api}/getUpdates",
            params={"offset": offset, "limit": 100, "timeout": 0}
        )
        r.raise_for_status()
        return r.json().get("result", [])


async def run(db: AsyncSession, checkpoint: int = 0) -> int:
    """Fetch messages since checkpoint, upsert into messages_raw. Returns new checkpoint."""
    updates = await fetch_updates(db, offset=checkpoint)
    to_insert = []
    new_checkpoint = checkpoint
    for update in updates:
        msg = update.get("message") or update.get("channel_post")
        if not msg:
            new_checkpoint = max(new_checkpoint, update["update_id"] + 1)
            continue
        if msg.get("from"):
            await upsert_member(db, msg["from"])
        sender_id = (msg.get("from") or {}).get("id") or (msg.get("sender_chat") or {}).get("id")
        if not sender_id:
            continue
        topic_id = msg.get("message_thread_id")
        topic_name = settings.diary_topic_name if (topic_id and topic_id == settings.diary_topic_id) else None
        to_insert.append({
            "message_id": msg["message_id"],
            "date": datetime.fromtimestamp(msg["date"], tz=timezone.utc),
            "from_id": sender_id,
            "text": msg.get("text") or msg.get("caption"),
            "chat_id": msg["chat"]["id"],
            "topic_id": topic_id,
            "topic_name": topic_name,
        })
        new_checkpoint = max(new_checkpoint, update["update_id"] + 1)
    await upsert_messages(db, to_insert)
    return new_checkpoint
