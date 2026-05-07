# Admin Panel — Design Spec
_Дата: 2026-05-03_

## Цель

Добавить защищённую страницу настроек (админку) в существующий `club-platform` FastAPI backend. Один пользователь. Две функции: ввод API ключей и управление агентами.

---

## Стек

| Компонент | Решение |
|-----------|---------|
| Роутер | FastAPI `/admin/*` внутри существующего `main.py` |
| Шаблоны | Jinja2 (HTML страницы, отдаются сервером) |
| Авторизация | JWT в httpOnly cookie, 24ч |
| Хранение ключей | PostgreSQL таблица `platform_settings` |
| Управление агентами | APScheduler API (в памяти) + `platform_settings` (персистентность) |

---

## Файловая структура

```
src/
├── api/
│   ├── routes/
│   │   └── admin.py          ← новый роутер
│   ├── templates/
│   │   ├── login.html        ← страница входа
│   │   └── admin.html        ← основная страница (ключи + агенты)
│   └── main.py               ← добавить admin.router + Jinja2
├── db/
│   └── models.py             ← добавить модель PlatformSetting
└── config.py                 ← добавить admin_password + admin_secret_key
```

---

## База данных

### Новая таблица `platform_settings`

```sql
CREATE TABLE platform_settings (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

Хранит:
- `anthropic_api_key`
- `telegram_bot_token`
- `telegram_chat_id`
- `getcourse_api_key`
- `getcourse_account`
- `diary_topic_id`
- `schedule_collector_tg` (cron-строка, default: `0 */6 * * *`)
- `schedule_collector_gc` (cron-строка, default: `0 */6 * * *`)
- `schedule_core_builder` (cron-строка, default: `0 */2 * * *`)
- `schedule_etl` (cron-строка, default: `0 4 * * *`)
- `schedule_analyzer` (cron-строка, default: `0 3 * * *`)

---

## Авторизация

- `ADMIN_PASSWORD` и `ADMIN_SECRET_KEY` задаются как переменные окружения в Timeweb — единственный способ изменить пароль
- Логин фиксированный: `admin`
- `POST /admin/login` — проверяет пароль, выдаёт JWT в httpOnly cookie (24ч)
- Все `/admin/*` маршруты проверяют cookie через FastAPI dependency `require_admin`
- Если cookie нет или истёк — редирект на `/admin/login`
- `GET /admin/logout` — удаляет cookie, редирект на `/admin/login`

### Новые поля в `config.py`

```python
admin_password: str = "changeme"
admin_secret_key: str = "change-this-secret"
```

---

## Страницы

### `/admin/login` (GET + POST)

- Форма: поля логин и пароль
- POST проверяет логин == `"admin"` и пароль == `settings.admin_password`
- При успехе — JWT cookie + редирект на `/admin`
- При ошибке — та же страница с сообщением "Неверный логин или пароль"

### `/admin` (GET) — вкладка API Ключи

- Читает все ключи из `platform_settings`
- Показывает замаскированными (первые 6 символов + `••••••••`)
- Кнопка "Показать" раскрывает конкретное поле
- Форма сохранения: `POST /admin/settings` — обновляет все ключи в `platform_settings`
- После сохранения агенты используют новые ключи при следующем запуске (читают из БД)

### `/admin` (GET) — вкладка Агенты

Для каждого из 5 агентов:
- **Статус**: `ok` / `idle` / `error` + время последнего запуска (из `agent_runs` или `platform_settings`)
- **Расписание**: редактируемое cron-поле, сохраняется через `POST /admin/schedule`
- **Кнопка "Запустить"**: `POST /admin/run/{agent_name}` — немедленный запуск агента

### `POST /admin/run/{agent_name}`

Принимает `agent_name` ∈ `{collector_tg, collector_gc, core_builder, etl, analyzer}`.
Запускает соответствующую функцию `run(db)` в фоновом задании FastAPI (`BackgroundTasks`).
Возвращает JSON `{"status": "started"}`.

### `POST /admin/schedule`

Принимает cron-строки для каждого агента.
Обновляет APScheduler в памяти через `scheduler.reschedule_job()`.
Сохраняет новые значения в `platform_settings`.

---

## Загрузка ключей агентами

Агенты читают ключи из `platform_settings` при каждом запуске:

```python
async def get_setting(db, key: str, default: str = "") -> str:
    row = await db.get(PlatformSetting, key)
    return row.value if row else default
```

Если ключ отсутствует в БД — fallback на `settings` (pydantic из `.env`). Это позволяет запустить систему до первого входа в админку.

---

## Расписание при перезапуске

При старте FastAPI (`lifespan`):
1. Читает расписание из `platform_settings`
2. Если записи есть — применяет их к APScheduler
3. Если нет — использует дефолтные значения из `scheduler.py`

---

## Главные ограничения

| Ограничение | Решение |
|-------------|---------|
| Один пользователь | Логин захардкожен как `admin`, нет регистрации |
| Пароль через env | `ADMIN_PASSWORD` в Timeweb, не меняется через UI |
| Нет шифрования ключей в БД | Ключи хранятся как plaintext в `platform_settings`. Достаточно для одного пользователя, БД закрыта извне |
| Нет rate-limit на логин | Приемлемо для внутреннего инструмента одного пользователя |
