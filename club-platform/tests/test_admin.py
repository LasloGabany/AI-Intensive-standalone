import pytest
from sqlalchemy import text

@pytest.mark.asyncio
async def test_platform_settings_table_exists(db):
    result = await db.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name='platform_settings'")
    )
    cols = {r[0] for r in result.fetchall()}
    assert "key" in cols
    assert "value" in cols
    assert "updated_at" in cols

@pytest.mark.asyncio
async def test_platform_setting_upsert(db):
    from src.db.models import PlatformSetting
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    stmt = pg_insert(PlatformSetting).values(key="test_key", value="test_val").on_conflict_do_update(
        index_elements=["key"], set_=dict(value="test_val")
    )
    await db.execute(stmt)
    await db.commit()
    row = await db.get(PlatformSetting, "test_key")
    assert row is not None
    assert row.value == "test_val"


def test_create_and_verify_token():
    from src.api.auth import create_token, verify_token
    token = create_token()
    payload = verify_token(token)
    assert payload is not None
    assert payload.get("sub") == "admin"

def test_verify_invalid_token():
    from src.api.auth import verify_token
    assert verify_token("not-a-token") is None

def test_verify_token_wrong_secret(monkeypatch):
    from src.api import auth
    token = auth.create_token()
    monkeypatch.setattr(auth, "_SECRET", "wrong-secret")
    assert auth.verify_token(token) is None
