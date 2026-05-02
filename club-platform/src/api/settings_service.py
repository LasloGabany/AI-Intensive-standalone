from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.db.models import PlatformSetting


async def get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    row = await db.get(PlatformSetting, key)
    return row.value if row else default


async def save_settings(db: AsyncSession, data: dict[str, str]) -> None:
    for key, value in data.items():
        stmt = pg_insert(PlatformSetting).values(key=key, value=str(value)).on_conflict_do_update(
            index_elements=["key"],
            set_=dict(value=str(value)),
        )
        await db.execute(stmt)
    await db.commit()
