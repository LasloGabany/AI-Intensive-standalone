# Task Queue

> Агент: читай задачи сверху вниз. Берёшь первую [ ]. Делаешь в отдельном worktree. Создаёшь PR. Помечаешь [done].
> Если задача непонятна или зависит от незавершённой — помечай [blocked] с причиной.
> Детальные инструкции по каждой задаче: docs/superpowers/plans/2026-05-03-admin-panel-build.md

---

## Admin Panel (последовательные — каждая зависит от предыдущей)

- [done] **Task 1** — PlatformSetting model + Alembic migration `002_platform_settings.py` → файлы: `src/db/models.py`, `alembic/versions/002_platform_settings.py`, `tests/test_admin.py`
- [done] **Task 2** — config.py admin fields + jinja2/python-jose в pyproject.toml → файлы: `src/config.py`, `pyproject.toml`
- [done] **Task 3** — JWT auth utilities (`create_token`, `verify_token`, `require_admin`) → файл: `src/api/auth.py`
- [done] **Task 4** — Settings service (`get_setting` / `save_settings`) → файл: `src/api/settings_service.py`
- [done] **Task 5** — HTML templates (`login.html` + `admin.html`) → папка: `src/api/templates/`
- [done] **Task 6** — Admin router: login, logout, API keys page → файл: `src/api/routes/admin.py`
- [done] **Task 7** — Admin router: run-agent + schedule routes + `AGENT_JOBS` в scheduler.py
- [done] **Task 8** — Wire admin в main.py + load schedules on startup → файл: `src/api/main.py`
- [done] **Task 9** — Agents читают ключи из DB: `collector_tg.py`, `collector_gc.py`, `analyzer.py`
- [done] **Task 10** — Final smoke test: `pytest tests/ -v`, `python3 -c "from src.api.main import app"`, push — PR #2 merged ✓

---

## Backlog (добавляй сюда новые задачи)

- [ ] FastAPI эндпоинт GET /clubs/{id}/members — список участников клуба с пагинацией
- [ ] Таблица участников в admin panel — отдельная вкладка "Участники" в admin.html

---

## Completed

<!-- [done] задачи переносятся сюда автоматически -->
