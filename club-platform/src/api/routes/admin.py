from __future__ import annotations
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import _COOKIE_NAME, create_token, require_admin
from src.api.settings_service import get_setting, save_settings
from src.db.connection import get_db
from src.config import settings
from src.scheduler import AGENT_JOBS, _DEFAULT_SCHEDULES, scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="src/api/templates")

_KEY_FIELDS = [
    "anthropic_api_key", "telegram_bot_token", "telegram_chat_id",
    "getcourse_api_key", "getcourse_account", "diary_topic_id",
]

_AGENT_NAMES = {
    "collector_tg": "collector-tg",
    "collector_gc": "collector-gc",
    "core_builder": "core-builder",
    "etl": "etl",
    "analyzer": "analyzer",
}


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(request, "login.html", {"error": error})


@router.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == settings.admin_password:
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(_COOKIE_NAME, create_token(), httponly=True, max_age=86400)
        return response
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Неверный логин или пароль"},
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
    return templates.TemplateResponse(request, "admin.html", {
        "keys": keys, "agents": agents, "flash": flash,
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
            from src.scheduler import reschedule_job
            reschedule_job(key, cron)
        except Exception as exc:
            logger.warning("Could not reschedule %s: %s", key, exc)
    await save_settings(db, to_save)
    return RedirectResponse(url="/admin?flash=Расписание+сохранено", status_code=303)
