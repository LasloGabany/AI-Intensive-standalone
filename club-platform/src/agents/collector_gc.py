from __future__ import annotations
import httpx
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.config import settings
from src.db.models import PaymentRaw, MemberRaw


GC_BASE = f"https://{settings.getcourse_account}.getcourse.ru/pl/api"


async def fetch_orders(page: int = 1) -> list[dict]:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"{GC_BASE}/account/orders",
            params={"key": settings.getcourse_api_key, "page": page, "per_page": 100}
        )
        r.raise_for_status()
        data = r.json()
        return data.get("orders", data.get("items", []))


async def upsert_payments(db: AsyncSession, payments: list[dict]) -> int:
    if not payments:
        return 0
    rows = []
    for p in payments:
        try:
            rows.append({
                "order_id": str(p["order_id"]),
                "user_id": int(p["user_id"]),
                "amount": float(p["amount"]),
                "date": datetime.fromisoformat(str(p["date"]).replace("Z", "+00:00")),
                "status": str(p.get("status", "completed")),
                "raw_json": p,
            })
        except (KeyError, ValueError):
            continue
    if not rows:
        return 0
    stmt = pg_insert(PaymentRaw).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["order_id"])
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def upsert_members_from_gc(db: AsyncSession, users: list[dict]) -> int:
    if not users:
        return 0
    rows = [{
        "user_id": int(u["id"]),
        "name": str(u.get("name", "")),
        "status": str(u.get("subscription_status", "expired")),
        "subscription_until": u.get("subscription_until"),
        "raw_json": u,
    } for u in users if u.get("id")]
    if not rows:
        return 0
    stmt = pg_insert(MemberRaw).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id"],
        set_={
            "status": stmt.excluded.status,
            "subscription_until": stmt.excluded.subscription_until,
            "updated_at": datetime.now(timezone.utc),
        }
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def run(db: AsyncSession) -> int:
    """Paginate through all GetCourse orders, upsert into payments_raw."""
    page, total = 1, 0
    while True:
        orders = await fetch_orders(page)
        if not orders:
            break
        total += await upsert_payments(db, orders)
        if len(orders) < 100:
            break
        page += 1
    return total
