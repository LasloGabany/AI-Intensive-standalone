import pytest
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport
from src.api.main import app

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

@pytest.mark.asyncio
async def test_get_setting_returns_default_when_missing(db):
    from src.api.settings_service import get_setting
    val = await get_setting(db, "nonexistent_key", default="fallback")
    assert val == "fallback"

@pytest.mark.asyncio
async def test_save_and_get_setting(db):
    from src.api.settings_service import get_setting, save_settings
    await save_settings(db, {"my_key": "my_value"})
    val = await get_setting(db, "my_key")
    assert val == "my_value"

@pytest.mark.asyncio
async def test_save_settings_overwrites(db):
    from src.api.settings_service import get_setting, save_settings
    await save_settings(db, {"ow_key": "first"})
    await save_settings(db, {"ow_key": "second"})
    val = await get_setting(db, "ow_key")
    assert val == "second"

@pytest.mark.asyncio
async def test_admin_login_page_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/admin/login")
    assert r.status_code == 200
    assert "Вход" in r.text

@pytest.mark.asyncio
async def test_admin_login_wrong_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/admin/login", data={"username": "admin", "password": "wrong"})
    assert r.status_code == 200
    assert "Неверный" in r.text

@pytest.mark.asyncio
async def test_admin_redirects_to_login_when_not_authenticated():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False) as c:
        r = await c.get("/admin")
    assert r.status_code in (307, 302)
    assert "/admin/login" in r.headers.get("location", "")

@pytest.mark.asyncio
async def test_run_unknown_agent_returns_404():
    from src.api.auth import create_token, _COOKIE_NAME
    token = create_token()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.cookies.set(_COOKIE_NAME, token)
        r = await c.post("/admin/run/nonexistent_agent")
    assert r.status_code == 404

@pytest.mark.asyncio
async def test_run_known_agent_returns_started():
    from src.api.auth import create_token, _COOKIE_NAME
    from unittest.mock import patch, AsyncMock
    token = create_token()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.cookies.set(_COOKIE_NAME, token)
        with patch("src.api.routes.admin._run_agent_task", new_callable=AsyncMock):
            r = await c.post("/admin/run/collector_tg")
    assert r.status_code == 200
    assert r.json()["status"] == "started"
