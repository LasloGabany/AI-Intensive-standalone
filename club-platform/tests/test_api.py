import pytest
import time
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_kpi_responds_under_300ms():
    from src.api.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        start = time.monotonic()
        r = await client.get("/api/kpi")
        elapsed = time.monotonic() - start
    assert r.status_code == 200
    assert elapsed < 0.3
    data = r.json()
    assert "active_subscriptions" in data
    assert "mrr" in data


@pytest.mark.asyncio
async def test_dashboard_returns_data_zone_shape():
    from src.api.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/dashboard")
    assert r.status_code == 200
    data = r.json()
    for key in ("KPI", "RETENTION", "FINANCES", "SILENT_DATA", "LEADERBOARD_DATA"):
        assert key in data, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_health_endpoint_returns_agent_statuses():
    from src.api.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        r = await client.get("/api/health")
    assert r.status_code == 200
    assert "agents" in r.json()
