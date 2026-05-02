# Admin Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a protected admin panel to club-platform FastAPI backend with login/logout, API key management stored in PostgreSQL, and manual agent control with editable cron schedules.

**Architecture:** New `/admin/*` router served via Jinja2 HTML templates. JWT stored in httpOnly cookie guards all admin routes. API keys and agent schedules persist in a new `platform_settings` table; agents read keys from DB at runtime with fallback to `.env`.

**Tech Stack:** FastAPI, Jinja2, python-jose[cryptography], SQLAlchemy 2.0 async, APScheduler, PostgreSQL, Alembic

---

## File Structure

**New files:**
- `club-platform/src/api/auth.py` — JWT create/verify, `require_admin` dependency
- `club-platform/src/api/settings_service.py` — `get_setting()` / `save_settings()` DB helpers
- `club-platform/src/api/routes/admin.py` — all `/admin/*` routes
- `club-platform/src/api/templates/login.html` — login page
- `club-platform/src/api/templates/admin.html` — main admin page (keys + agents tabs)
- `club-platform/alembic/versions/002_platform_settings.py` — migration

**Modified files:**
- `club-platform/src/db/models.py` — add `PlatformSetting` model
- `club-platform/src/config.py` — add `admin_password`, `admin_secret_key`
- `club-platform/pyproject.toml` — add `jinja2`, `python-jose[cryptography]`
- `club-platform/src/scheduler.py` — expose `scheduler` + add `reschedule_job()`
- `club-platform/src/api/main.py` — add Jinja2, include admin router, load schedules in lifespan
- `club-platform/src/agents/collector_tg.py` — read token from DB via `get_setting()`
- `club-platform/src/agents/collector_gc.py` — read key from DB via `get_setting()`
- `club-platform/src/agents/analyzer.py` — read key from DB via `get_setting()`
- `club-platform/tests/test_admin.py` — new test file

---

### Task 1: PlatformSetting model + Alembic migration

**Files:**
- Modify: `club-platform/src/db/models.py`
- Create: `club-platform/alembic/versions/002_platform_settings.py`
- Test: `club-platform/tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# club-platform/tests/test_admin.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd club-platform
pytest tests/test_admin.py -v
```
Expected: FAIL — `PlatformSetting` not defined, table doesn't exist.

- [ ] **Step 3: Add PlatformSetting model to models.py**

Append to `club-platform/src/db/models.py` (after the last existing model):

```python
class PlatformSetting(Base):
    __tablename__ = "platform_settings"
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 4: Create Alembic migration**

Create `club-platform/alembic/versions/002_platform_settings.py`:

```python
"""platform_settings table

Revision ID: 002
Revises: 001
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'platform_settings',
        sa.Column('key', sa.Text, primary_key=True),
        sa.Column('value', sa.Text, nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade():
    op.drop_table('platform_settings')
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_admin.py -v
```
Expected: PASS (both tests green — table created by conftest Base.metadata.create_all).

- [ ] **Step 6: Commit**

```bash
git add src/db/models.py alembic/versions/002_platform_settings.py tests/test_admin.py
git commit -m "feat: PlatformSetting model + migration"
```

---

### Task 2: config.py + pyproject.toml dependencies

**Files:**
- Modify: `club-platform/src/config.py`
- Modify: `club-platform/pyproject.toml`

- [ ] **Step 1: Add admin fields to config.py**

Replace the entire `club-platform/src/config.py` with:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: int = 0
    getcourse_api_key: str = ""
    getcourse_account: str = ""
    diary_topic_name: str = "Дневник успеха"
    diary_topic_id: int = 0
    admin_password: str = "changeme"
    admin_secret_key: str = "change-this-secret-key-32-chars!!"

    class Config:
        env_file = ".env"

settings = Settings()
```

Note: `anthropic_api_key`, `telegram_*`, `getcourse_*` now have empty string defaults so the app starts even without `.env` values — real values come from `platform_settings` DB table.

- [ ] **Step 2: Add jinja2 and python-jose to pyproject.toml**

In `club-platform/pyproject.toml`, find the `dependencies` list and add two entries:

```toml
dependencies = [
    "asyncpg>=0.29",
    "sqlalchemy[asyncio]>=2.0",
    "alembic>=1.13",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "anthropic>=0.25",
    "httpx>=0.27",
    "apscheduler>=3.10",
    "python-dotenv>=1.0",
    "pydantic-settings>=2.2",
    "python-dateutil>=2.9",
    "jinja2>=3.1",
    "python-jose[cryptography]>=3.3",
]
```

- [ ] **Step 3: Install new dependencies**

```bash
pip install -e .
```
Expected: `Successfully installed jinja2-... python-jose-...`

- [ ] **Step 4: Commit**

```bash
git add src/config.py pyproject.toml
git commit -m "feat: admin config fields + jinja2/python-jose deps"
```

---

### Task 3: Auth utilities (JWT)

**Files:**
- Create: `club-platform/src/api/auth.py`
- Test: `club-platform/tests/test_admin.py`

- [ ] **Step 1: Write the failing tests**

Append to `club-platform/tests/test_admin.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_admin.py::test_create_and_verify_token -v
```
Expected: FAIL — `src.api.auth` module not found.

- [ ] **Step 3: Create src/api/auth.py**

```python
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Cookie, HTTPException, status
from fastapi.responses import RedirectResponse
from src.config import settings

_SECRET = settings.admin_secret_key
_ALGORITHM = "HS256"
_EXPIRE_HOURS = 24
_COOKIE_NAME = "admin_token"


def create_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_EXPIRE_HOURS)
    return jwt.encode({"sub": "admin", "exp": expire}, _SECRET, algorithm=_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except JWTError:
        return None


def require_admin(admin_token: Optional[str] = Cookie(default=None)):
    if not admin_token or not verify_token(admin_token):
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/admin/login"},
        )
    return True
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_admin.py::test_create_and_verify_token tests/test_admin.py::test_verify_invalid_token tests/test_admin.py::test_verify_token_wrong_secret -v
```
Expected: all 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/auth.py tests/test_admin.py
git commit -m "feat: JWT auth utilities for admin panel"
```

---

### Task 4: Settings service (get_setting / save_settings)

**Files:**
- Create: `club-platform/src/api/settings_service.py`
- Test: `club-platform/tests/test_admin.py`

- [ ] **Step 1: Write the failing tests**

Append to `club-platform/tests/test_admin.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_admin.py::test_get_setting_returns_default_when_missing -v
```
Expected: FAIL — `src.api.settings_service` not found.

- [ ] **Step 3: Create src/api/settings_service.py**

```python
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_admin.py::test_get_setting_returns_default_when_missing tests/test_admin.py::test_save_and_get_setting tests/test_admin.py::test_save_settings_overwrites -v
```
Expected: all 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/settings_service.py tests/test_admin.py
git commit -m "feat: settings_service — get/save platform_settings"
```

---

### Task 5: HTML templates (login + admin pages)

**Files:**
- Create: `club-platform/src/api/templates/login.html`
- Create: `club-platform/src/api/templates/admin.html`

- [ ] **Step 1: Create login.html**

Create `club-platform/src/api/templates/login.html`:

```html
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Вход — Club Admin</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#0f1117; color:#e1e4e8; display:flex; align-items:center; justify-content:center; min-height:100vh; }
.card { background:#1c1f26; border:1px solid #2d3139; border-radius:12px; padding:40px; width:380px; }
h1 { font-size:20px; font-weight:600; margin-bottom:6px; }
p { font-size:13px; color:#8b949e; margin-bottom:28px; }
label { display:block; font-size:13px; color:#8b949e; margin-bottom:6px; }
.field { margin-bottom:16px; }
input[type=text], input[type=password] { width:100%; background:#0f1117; border:1px solid #2d3139; border-radius:8px; padding:10px 14px; color:#e1e4e8; font-size:14px; outline:none; }
input:focus { border-color:#58a6ff; }
button { width:100%; background:#238636; color:#fff; border:none; border-radius:8px; padding:11px; font-size:14px; font-weight:500; cursor:pointer; margin-top:8px; }
button:hover { background:#2ea043; }
.error { background:#2d1117; border:1px solid #f85149; border-radius:8px; padding:10px 14px; font-size:13px; color:#f85149; margin-bottom:16px; }
</style>
</head>
<body>
<div class="card">
  <h1>🔐 Вход в админку</h1>
  <p>Club Platform — панель управления</p>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="post" action="/admin/login">
    <div class="field"><label>Логин</label><input type="text" name="username" value="admin" /></div>
    <div class="field"><label>Пароль</label><input type="password" name="password" autofocus /></div>
    <button type="submit">Войти</button>
  </form>
</div>
</body>
</html>
```

- [ ] **Step 2: Create admin.html**

Create `club-platform/src/api/templates/admin.html`:

```html
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Admin — Club Platform</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#0f1117; color:#e1e4e8; }
.sidebar { position:fixed; left:0; top:0; bottom:0; width:220px; background:#161b22; border-right:1px solid #2d3139; padding:24px 16px; display:flex; flex-direction:column; }
.logo { font-size:15px; font-weight:600; padding:8px 12px; margin-bottom:24px; color:#58a6ff; }
.nav a { display:flex; align-items:center; gap:10px; padding:9px 12px; border-radius:8px; font-size:14px; color:#8b949e; text-decoration:none; margin-bottom:2px; }
.nav a:hover, .nav a.active { background:#1f2937; color:#e1e4e8; }
.logout { margin-top:auto; }
.logout a { color:#f85149 !important; }
.main { margin-left:220px; padding:32px 40px; }
.page-title { font-size:22px; font-weight:600; margin-bottom:6px; }
.page-sub { font-size:14px; color:#8b949e; margin-bottom:32px; }
.card { background:#1c1f26; border:1px solid #2d3139; border-radius:12px; padding:24px; margin-bottom:24px; }
.card-title { font-size:15px; font-weight:600; margin-bottom:4px; }
.card-sub { font-size:13px; color:#8b949e; margin-bottom:20px; }
.grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
.field label { display:block; font-size:12px; color:#8b949e; margin-bottom:6px; font-weight:500; }
.field input { width:100%; background:#0f1117; border:1px solid #2d3139; border-radius:8px; padding:9px 12px; color:#e1e4e8; font-size:13px; font-family:monospace; outline:none; }
.field input:focus { border-color:#58a6ff; }
.field-row { display:flex; gap:8px; }
.field-row input { flex:1; }
.btn-show { background:none; border:1px solid #2d3139; color:#8b949e; border-radius:8px; padding:0 12px; font-size:12px; cursor:pointer; white-space:nowrap; }
.btn-primary { background:#238636; color:#fff; border:none; border-radius:8px; padding:10px 24px; font-size:13px; font-weight:500; cursor:pointer; margin-top:4px; }
.btn-primary:hover { background:#2ea043; }
.agents-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:12px; }
.agent-card { background:#0f1117; border:1px solid #2d3139; border-radius:10px; padding:16px; }
.agent-name { font-size:13px; font-weight:600; margin-bottom:8px; }
.status { display:inline-flex; align-items:center; gap:5px; font-size:11px; color:#8b949e; margin-bottom:4px; }
.dot { width:6px; height:6px; border-radius:50%; background:#8b949e; }
.dot.ok { background:#3fb950; }
.dot.error { background:#f85149; }
.last-run { font-size:11px; color:#8b949e; margin-bottom:12px; }
.cron-label { font-size:11px; color:#8b949e; margin-bottom:4px; }
.cron-input { width:100%; background:#161b22; border:1px solid #2d3139; border-radius:6px; padding:6px 8px; color:#58a6ff; font-size:12px; font-family:monospace; margin-bottom:8px; outline:none; }
.btn-run { width:100%; background:#1f2937; border:1px solid #2d3139; color:#e1e4e8; border-radius:6px; padding:7px; font-size:12px; cursor:pointer; }
.btn-run:hover { background:#238636; border-color:#238636; }
.flash { background:#0d2818; border:1px solid #3fb950; border-radius:8px; padding:10px 16px; font-size:13px; color:#3fb950; margin-bottom:20px; }
.tab-section { display:none; }
.tab-section.active { display:block; }
</style>
</head>
<body>
<div class="sidebar">
  <div class="logo">⚙️ Club Admin</div>
  <nav class="nav">
    <a href="#" class="active" onclick="showTab('keys',this)">🔑 API Ключи</a>
    <a href="#" onclick="showTab('agents',this)">🤖 Агенты</a>
  </nav>
  <div class="logout nav"><a href="/admin/logout">← Выйти</a></div>
</div>

<div class="main">
  {% if flash %}<div class="flash">{{ flash }}</div>{% endif %}

  <!-- API KEYS TAB -->
  <div class="tab-section active" id="tab-keys">
    <div class="page-title">API Ключи</div>
    <div class="page-sub">Сохраняются в базе данных. Агенты читают при каждом запуске.</div>
    <form method="post" action="/admin/settings">
      <div class="card">
        <div class="card-title">Anthropic (Claude API)</div>
        <div class="card-sub">Используется для анализа инсайтов и эмоций клуба</div>
        <div class="field">
          <label>API KEY</label>
          <div class="field-row">
            <input type="password" name="anthropic_api_key" id="f_anthropic" value="{{ keys.anthropic_api_key }}" />
            <button type="button" class="btn-show" onclick="toggle('f_anthropic')">Показать</button>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">Telegram</div>
        <div class="card-sub">Бот для сбора сообщений из клубного чата</div>
        <div class="grid-2">
          <div class="field">
            <label>BOT TOKEN</label>
            <div class="field-row">
              <input type="password" name="telegram_bot_token" id="f_tg_token" value="{{ keys.telegram_bot_token }}" />
              <button type="button" class="btn-show" onclick="toggle('f_tg_token')">Показать</button>
            </div>
          </div>
          <div class="field"><label>CHAT ID</label><input type="text" name="telegram_chat_id" value="{{ keys.telegram_chat_id }}" /></div>
          <div class="field"><label>DIARY TOPIC ID (опционально)</label><input type="text" name="diary_topic_id" value="{{ keys.diary_topic_id }}" /></div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">GetCourse</div>
        <div class="card-sub">Данные о платежах и подписках</div>
        <div class="grid-2">
          <div class="field">
            <label>API KEY</label>
            <div class="field-row">
              <input type="password" name="getcourse_api_key" id="f_gc_key" value="{{ keys.getcourse_api_key }}" />
              <button type="button" class="btn-show" onclick="toggle('f_gc_key')">Показать</button>
            </div>
          </div>
          <div class="field"><label>ACCOUNT</label><input type="text" name="getcourse_account" value="{{ keys.getcourse_account }}" /></div>
        </div>
      </div>
      <button type="submit" class="btn-primary">💾 Сохранить все ключи</button>
    </form>
  </div>

  <!-- AGENTS TAB -->
  <div class="tab-section" id="tab-agents">
    <div class="page-title">Агенты</div>
    <div class="page-sub">Запуск вручную и настройка расписания (cron)</div>
    <div class="card">
      <form method="post" action="/admin/schedule" id="scheduleForm">
        <div class="agents-grid">
          {% for agent in agents %}
          <div class="agent-card">
            <div class="agent-name">{{ agent.name }}</div>
            <div class="status"><span class="dot {{ agent.status_class }}"></span>{{ agent.status_label }}</div>
            <div class="last-run">Последний: {{ agent.last_run }}</div>
            <div class="cron-label">Расписание (cron)</div>
            <input class="cron-input" name="{{ agent.key }}" value="{{ agent.schedule }}" />
            <button type="button" class="btn-run" onclick="runAgent('{{ agent.key }}')">▶ Запустить</button>
          </div>
          {% endfor %}
        </div>
        <button type="submit" class="btn-primary" style="margin-top:16px">💾 Сохранить расписание</button>
      </form>
    </div>
  </div>
</div>

<script>
function showTab(name, el) {
  document.querySelectorAll('.tab-section').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav a').forEach(a => a.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  el.classList.add('active');
}
function toggle(id) {
  const el = document.getElementById(id);
  el.type = el.type === 'password' ? 'text' : 'password';
}
async function runAgent(key) {
  const btn = event.target;
  btn.textContent = '⏳ Запуск...';
  btn.disabled = true;
  try {
    const r = await fetch('/admin/run/' + key, {method:'POST'});
    const d = await r.json();
    btn.textContent = d.status === 'started' ? '✅ Запущен' : '❌ Ошибка';
  } catch {
    btn.textContent = '❌ Ошибка';
  }
  setTimeout(() => { btn.textContent = '▶ Запустить'; btn.disabled = false; }, 3000);
}
</script>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add src/api/templates/
git commit -m "feat: login.html and admin.html templates"
```

---

### Task 6: Admin router — login, logout, keys page

**Files:**
- Create: `club-platform/src/api/routes/admin.py`
- Test: `club-platform/tests/test_admin.py`

- [ ] **Step 1: Write the failing tests**

Append to `club-platform/tests/test_admin.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app

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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_admin.py::test_admin_login_page_returns_200 -v
```
Expected: FAIL — `/admin/login` route not found (404).

- [ ] **Step 3: Create src/api/routes/admin.py**

```python
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.connection import get_db
from src.config import settings
from src.api.auth import create_token, require_admin, _COOKIE_NAME
from src.api.settings_service import get_setting, save_settings
from src.scheduler import scheduler, AGENT_JOBS

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="src/api/templates")

_KEY_FIELDS = [
    "anthropic_api_key", "telegram_bot_token", "telegram_chat_id",
    "getcourse_api_key", "getcourse_account", "diary_topic_id",
]

_DEFAULT_SCHEDULES = {
    "collector_tg":  "0 */6 * * *",
    "collector_gc":  "0 */6 * * *",
    "core_builder":  "0 */2 * * *",
    "etl":           "0 4 * * *",
    "analyzer":      "0 3 * * *",
}

_AGENT_NAMES = {
    "collector_tg":  "collector-tg",
    "collector_gc":  "collector-gc",
    "core_builder":  "core-builder",
    "etl":           "etl",
    "analyzer":      "analyzer",
}


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
async def login_submit(username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == settings.admin_password:
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(_COOKIE_NAME, create_token(), httponly=True, max_age=86400)
        return response
    return templates.TemplateResponse(
        "login.html",
        {"request": {}, "error": "Неверный логин или пароль"},
        status_code=200,
    )


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(_COOKIE_NAME)
    return response


@router.get("", response_class=HTMLResponse)
async def admin_home(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
    flash: Optional[str] = None,
):
    keys = {k: await get_setting(db, k) for k in _KEY_FIELDS}
    agents = []
    for key, name in _AGENT_NAMES.items():
        schedule = await get_setting(db, f"schedule_{key}", _DEFAULT_SCHEDULES[key])
        agents.append({
            "key": key,
            "name": name,
            "schedule": schedule,
            "status_class": "ok",
            "status_label": "Ожидает",
            "last_run": await get_setting(db, f"last_run_{key}", "—"),
        })
    return templates.TemplateResponse("admin.html", {
        "request": request, "keys": keys, "agents": agents, "flash": flash,
    })


@router.post("/settings")
async def save_api_keys(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
    anthropic_api_key: str = Form(""),
    telegram_bot_token: str = Form(""),
    telegram_chat_id: str = Form("0"),
    getcourse_api_key: str = Form(""),
    getcourse_account: str = Form(""),
    diary_topic_id: str = Form("0"),
):
    await save_settings(db, {
        "anthropic_api_key": anthropic_api_key,
        "telegram_bot_token": telegram_bot_token,
        "telegram_chat_id": telegram_chat_id,
        "getcourse_api_key": getcourse_api_key,
        "getcourse_account": getcourse_account,
        "diary_topic_id": diary_topic_id,
    })
    return RedirectResponse(url="/admin?flash=Ключи+сохранены", status_code=303)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_admin.py::test_admin_login_page_returns_200 tests/test_admin.py::test_admin_login_wrong_password tests/test_admin.py::test_admin_redirects_to_login_when_not_authenticated -v
```
Expected: all 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/routes/admin.py tests/test_admin.py
git commit -m "feat: admin router — login, logout, API keys page"
```

---

### Task 7: Agent run + schedule routes

**Files:**
- Modify: `club-platform/src/api/routes/admin.py`
- Modify: `club-platform/src/scheduler.py`
- Test: `club-platform/tests/test_admin.py`

- [ ] **Step 1: Write the failing tests**

Append to `club-platform/tests/test_admin.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_admin.py::test_run_unknown_agent_returns_404 -v
```
Expected: FAIL — route not defined yet.

- [ ] **Step 3: Expose AGENT_JOBS dict in scheduler.py**

Add to `club-platform/src/scheduler.py` after the imports:

```python
from src.db.connection import SessionLocal
from src.agents import collector_tg, collector_gc, core_builder, etl, analyzer

# Map agent key → async callable (used by admin panel for manual runs)
AGENT_JOBS: dict[str, callable] = {
    "collector_tg":  run_collectors,
    "collector_gc":  run_collectors,
    "core_builder":  run_core_builder,
    "etl":           run_full_etl,
    "analyzer":      run_analyzer,
}


def reschedule_job(job_id: str, cron_str: str) -> None:
    from apscheduler.triggers.cron import CronTrigger as CT
    parts = cron_str.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron: {cron_str}")
    minute, hour, day, month, dow = parts
    trigger = CT(minute=minute, hour=hour, day=day, month=month, day_of_week=dow)
    scheduler.reschedule_job(job_id, trigger=trigger)
```

Note: `AGENT_JOBS` references `run_collectors` etc. which are defined earlier in the same file. Place the `AGENT_JOBS` dict and `reschedule_job` function **after** all the `run_*` functions.

- [ ] **Step 4: Add run + schedule routes to admin.py**

Append to the end of `club-platform/src/api/routes/admin.py`:

```python
async def _run_agent_task(key: str) -> None:
    from datetime import datetime
    from src.db.connection import SessionLocal
    fn = AGENT_JOBS.get(key)
    if not fn:
        return
    try:
        await fn()
        async with SessionLocal() as db:
            await save_settings(db, {f"last_run_{key}": datetime.utcnow().strftime("%d.%m %H:%M")})
    except Exception as exc:
        logger.warning("Manual agent run failed for %s: %s", key, exc)


@router.post("/run/{agent_key}")
async def run_agent(
    agent_key: str,
    background_tasks: BackgroundTasks,
    _: bool = Depends(require_admin),
):
    if agent_key not in _AGENT_NAMES:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Unknown agent")
    background_tasks.add_task(_run_agent_task, agent_key)
    return JSONResponse({"status": "started"})


@router.post("/schedule")
async def update_schedule(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin),
):
    form = await request.form()
    to_save = {}
    for key in _DEFAULT_SCHEDULES:
        cron = form.get(key, _DEFAULT_SCHEDULES[key])
        to_save[f"schedule_{key}"] = cron
        try:
            scheduler.reschedule_job(key, trigger=__import__('apscheduler.triggers.cron', fromlist=['CronTrigger']).CronTrigger.from_crontab(cron))
        except Exception as exc:
            logger.warning("Could not reschedule %s: %s", key, exc)
    await save_settings(db, to_save)
    return RedirectResponse(url="/admin?flash=Расписание+сохранено", status_code=303)
```

Also add this import at the top of `admin.py` (after existing imports):

```python
from src.scheduler import AGENT_JOBS
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_admin.py::test_run_unknown_agent_returns_404 tests/test_admin.py::test_run_known_agent_returns_started -v
```
Expected: both PASS.

- [ ] **Step 6: Commit**

```bash
git add src/api/routes/admin.py src/scheduler.py tests/test_admin.py
git commit -m "feat: admin run-agent + schedule routes"
```

---

### Task 8: Wire admin into main.py + load schedules on startup

**Files:**
- Modify: `club-platform/src/api/main.py`
- Test: `club-platform/tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

Append to `club-platform/tests/test_admin.py`:

```python
@pytest.mark.asyncio
async def test_admin_root_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False) as c:
        r = await c.get("/admin")
    assert r.status_code in (302, 307)
```

- [ ] **Step 2: Replace main.py**

Replace the entire `club-platform/src/api/main.py` with:

```python
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.connection import get_db
from src.api.routes import kpi, retention, health, finance, insights
from src.api.routes import admin as admin_router
from src.scheduler import start as start_scheduler, scheduler, reschedule_job, _DEFAULT_SCHEDULES
from src.api.settings_service import get_setting

import logging
logger = logging.getLogger(__name__)


async def _load_schedules_from_db():
    from src.db.connection import SessionLocal
    async with SessionLocal() as db:
        for key, default in _DEFAULT_SCHEDULES.items():
            cron = await get_setting(db, f"schedule_{key}", default)
            if cron != default:
                try:
                    reschedule_job(key, cron)
                except Exception as exc:
                    logger.warning("Could not apply saved schedule for %s: %s", key, exc)


@asynccontextmanager
async def lifespan(app):
    start_scheduler()
    await _load_schedules_from_db()
    yield


app = FastAPI(title="Club Platform API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

for router in (kpi.router, retention.router, health.router, finance.router, insights.router):
    app.include_router(router)

app.include_router(admin_router.router)


@app.get("/api/dashboard")
async def get_dashboard(
    kpi_data: dict = Depends(kpi.get_kpi),
    ret_data: dict = Depends(retention.get_retention),
    fin_data: dict = Depends(finance.get_finance),
    ins_data: dict = Depends(insights.get_insights),
    hlt_data: dict = Depends(health.get_health),
):
    return {
        "KPI": kpi_data,
        "RETENTION": ret_data,
        "FINANCES": fin_data,
        "INSIGHTS": ins_data,
        "EMOTIONS_DATA": ins_data.get("emotions", {}),
        "SILENT_DATA": hlt_data.get("silent", []),
        "LEADERBOARD_DATA": hlt_data.get("leaderboard", []),
        "ACTIVITY_DATA": hlt_data.get("activity", {}),
    }
```

Also add `_DEFAULT_SCHEDULES` to `scheduler.py` (it's used by main.py above). Add this dict near the top of `scheduler.py` after imports:

```python
_DEFAULT_SCHEDULES = {
    "collector_tg":  "0 */6 * * *",
    "collector_gc":  "0 */6 * * *",
    "core_builder":  "0 */2 * * *",
    "etl":           "0 4 * * *",
    "analyzer":      "0 3 * * *",
}
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_admin.py -v
```
Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add src/api/main.py src/scheduler.py tests/test_admin.py
git commit -m "feat: wire admin router into main.py + load schedules on startup"
```

---

### Task 9: Update agents to read keys from DB

**Files:**
- Modify: `club-platform/src/agents/collector_tg.py`
- Modify: `club-platform/src/agents/collector_gc.py`
- Modify: `club-platform/src/agents/analyzer.py`

- [ ] **Step 1: Update collector_tg.py**

In `collector_tg.py`, remove the module-level `TG_API` constant and move it inside `fetch_updates`:

Replace:
```python
TG_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
```

With nothing (delete that line). Then in `fetch_updates(db, checkpoint)`, add at the top of the function:

```python
async def fetch_updates(db: AsyncSession, checkpoint: int) -> list[dict]:
    from src.api.settings_service import get_setting
    token = await get_setting(db, "telegram_bot_token", settings.telegram_bot_token)
    tg_api = f"https://api.telegram.org/bot{token}"
    # replace all uses of TG_API below with tg_api
    ...
```

Replace all remaining references to `TG_API` inside `fetch_updates` with `tg_api`.

- [ ] **Step 2: Update collector_gc.py**

In `collector_gc.py`, inside `fetch_orders(page)`, read key from DB:

```python
async def fetch_orders(db: AsyncSession, page: int) -> list[dict]:
    from src.api.settings_service import get_setting
    api_key = await get_setting(db, "getcourse_api_key", settings.getcourse_api_key)
    account = await get_setting(db, "getcourse_account", settings.getcourse_account)
    url = f"https://{account}.getcourse.ru/pl/api/account/deals"
    ...
```

Update the signature of `fetch_orders` to accept `db` and pass it through from `run(db)`.

- [ ] **Step 3: Update analyzer.py**

In `analyzer.py`, inside `analyze_insights`, replace the module-level client init with a per-call init reading from DB:

```python
async def analyze_insights(db: AsyncSession, days: int = 30) -> dict:
    from src.api.settings_service import get_setting
    from anthropic import AsyncAnthropic
    api_key = await get_setting(db, "anthropic_api_key", settings.anthropic_api_key)
    client = AsyncAnthropic(api_key=api_key)
    ...
```

Remove the module-level `client = AsyncAnthropic(...)` line.

- [ ] **Step 4: Run all tests**

```bash
pytest tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/agents/collector_tg.py src/agents/collector_gc.py src/agents/analyzer.py
git commit -m "feat: agents read API keys from platform_settings with env fallback"
```

---

### Task 10: Final smoke test + push

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```
Expected: all tests PASS, 0 failures.

- [ ] **Step 2: Verify imports resolve cleanly**

```bash
python3 -c "from src.api.main import app; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Push to GitHub**

```bash
git push origin feature/club-platform
```

- [ ] **Step 4: Verify PR on GitHub**

Open https://github.com/LasloGabany/AI-Intensive-standalone/pull/1 — confirm new commits appear.

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 0 | — | — |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**VERDICT:** NO REVIEWS YET
