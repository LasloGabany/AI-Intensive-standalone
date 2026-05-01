# Club Data Pipeline — Design Spec
_Дата: 2026-05-01_

## Цель

Построить 3-слойный data pipeline, который автоматически собирает сырые данные из Telegram и GetCourse, нормализует их, вычисляет все метрики дашборда и отдаёт их через FastAPI endpoint. Dashboard `index.html` получает данные динамически вместо захардкоженных констант.

---

## Стек

| Компонент | Решение |
|-----------|---------|
| Рантайм агентов | Railway (Python) |
| База данных | PostgreSQL (Railway managed) |
| Агенты | Python + Anthropic Agent SDK |
| LLM анализ | Claude API (claude-sonnet-4-6) |
| API endpoint | FastAPI (always-on на Railway) |
| Dashboard | `club-dashboard/index.html` (уже построен) |
| Источники данных | Telegram Bot API, GetCourse API |

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        RAILWAY                              │
│                                                             │
│  ┌──────────────────┐   ┌─────────────────────────────┐   │
│  │   CLAUDE AGENTS  │   │        PostgreSQL            │   │
│  │                  │   │                             │   │
│  │  collector-tg    │──▶│  RAW LAYER                  │   │
│  │  collector-gc    │──▶│  ├── messages_raw            │   │
│  │                  │   │  ├── payments_raw            │   │
│  │  core-builder    │──▶│  └── members_raw             │   │
│  │                  │   │                             │   │
│  │  analyzer (LLM)  │──▶│  CORE LAYER                 │   │
│  │                  │   │  ├── subscriptions           │   │
│  │  etl             │──▶│  ├── payments_normalized     │   │
│  │                  │   │  ├── user_activity_daily     │   │
│  │  FastAPI api     │◀──│  └── user_last_activity      │   │
│  └────────┬─────────┘   │                             │   │
│           │             │  MART LAYER                 │   │
│           │             │  ├── kpi_snapshot            │   │
│           │             │  ├── retention_fact          │   │
│           │             │  ├── user_health             │   │
│           │             │  ├── user_activity_score     │   │
│           │             │  ├── mrr_daily_snapshot      │   │
│           │             │  ├── churn_events            │   │
│           │             │  ├── cohorts                 │   │
│           │             │  ├── retention_by_activity   │   │
│           │             │  ├── churn_probability       │   │
│           │             │  ├── arpu_by_segment         │   │
│           │             │  └── analyzed_output         │   │
│           │             └─────────────────────────────┘   │
└───────────┼─────────────────────────────────────────────────┘
            │ JSON
            ▼
    index.html → fetch('/api/dashboard') → initAll()
```

---

## Слой RAW

Хранит данные как пришли. Никакой логики — только очистка null и базовые типы.

```sql
CREATE TABLE messages_raw (
  message_id    BIGINT PRIMARY KEY,
  date          TIMESTAMPTZ NOT NULL,
  from_id       BIGINT NOT NULL,
  text          TEXT,
  chat_id       BIGINT,
  topic_id      INTEGER,
  topic_name    TEXT,
  ingested_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payments_raw (
  order_id      TEXT PRIMARY KEY,
  user_id       BIGINT NOT NULL,
  amount        NUMERIC(12,2) NOT NULL,
  date          TIMESTAMPTZ NOT NULL,
  status        TEXT,
  raw_json      JSONB,
  ingested_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE members_raw (
  user_id       BIGINT PRIMARY KEY,
  name          TEXT,
  username      TEXT,
  join_date     TIMESTAMPTZ,
  status        TEXT,
  subscription_until TIMESTAMPTZ,
  chat_member   BOOLEAN DEFAULT TRUE,
  raw_json      JSONB,
  ingested_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);
```

**Правило:** collector агенты только пишут в RAW. Upsert по primary key — нет дублей.

---

## Слой CORE

Нормализованные канонические таблицы. Строит `core-builder` каждые 2ч инкрементально.

```sql
-- Одна строка = один пользователь сейчас
-- MRR считается только отсюда, никогда из payments
CREATE TABLE subscriptions (
  user_id               BIGINT PRIMARY KEY,
  status                TEXT NOT NULL, -- active | canceled | past_due | expired
  current_period_start  TIMESTAMPTZ,
  current_period_end    TIMESTAMPTZ,
  monthly_price         NUMERIC(10,2),
  plan_type             TEXT, -- monthly | quarterly | yearly
  tenure_days           INTEGER,
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

-- Нормализованные платежи (годовые → 12 строк по 1 мес или months_covered=12)
CREATE TABLE payments_normalized (
  id              SERIAL PRIMARY KEY,
  user_id         BIGINT NOT NULL,
  payment_date    DATE NOT NULL,
  amount          NUMERIC(12,2),
  months_covered  INTEGER DEFAULT 1
);

-- Критически важная таблица: user × день
-- Все active7/active30/streak считаются через простой SUM по этой таблице
CREATE TABLE user_activity_daily (
  user_id       BIGINT NOT NULL,
  date          DATE NOT NULL,
  message_count INTEGER DEFAULT 0,
  diary_count   INTEGER DEFAULT 0,
  replies_count INTEGER DEFAULT 0,
  active_flag   SMALLINT DEFAULT 0, -- 0 или 1
  PRIMARY KEY (user_id, date)
);

-- Инкрементально обновляется при каждом новом сообщении
CREATE TABLE user_last_activity (
  user_id             BIGINT PRIMARY KEY,
  first_message_date  DATE,
  last_message_date   DATE,
  total_messages      INTEGER DEFAULT 0,
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Слой MART

Готовые метрики для дашборда. Строит `etl` раз в сутки в 04:00.

```sql
-- Снимок KPI на каждый день
CREATE TABLE kpi_snapshot (
  date                  DATE PRIMARY KEY,
  active_subscriptions  INTEGER,
  mrr                   NUMERIC(12,2),
  chat_active_30        INTEGER,
  chat_active_7         INTEGER,
  chat_never_wrote      INTEGER,
  chat_silent_paying    INTEGER
);

-- Когорты: один раз создаются, не меняются
CREATE TABLE cohorts (
  cohort_month        DATE PRIMARY KEY,
  cohort_size         INTEGER,
  first_payment_date  DATE
);

-- Retention: одна строка = когорта × смещение в месяцах
CREATE TABLE retention_fact (
  cohort_month          DATE NOT NULL,
  month_offset          INTEGER NOT NULL,
  users_active          INTEGER,
  users_paid            INTEGER,
  retention_subscription NUMERIC(5,2),
  retention_billing      NUMERIC(5,2),
  PRIMARY KEY (cohort_month, month_offset)
);

-- Здоровье пользователя — операционный инструмент для куратора
CREATE TABLE user_health (
  user_id          BIGINT PRIMARY KEY,
  silent_days      INTEGER,
  tenure_days      INTEGER,
  monthly_price    NUMERIC(10,2),
  activity_score   NUMERIC(6,2),
  -- risk_score = silent_days*0.4 + (1/activity_score)*0.3 + (tenure_days/30)*0.3
  risk_score       NUMERIC(6,2),
  risk_segment     TEXT, -- expired | ghost | high_risk | medium | healthy
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Скор активности с весами (антиспам)
CREATE TABLE user_activity_score (
  user_id     BIGINT NOT NULL,
  date        DATE NOT NULL,
  -- score = message_count*1 + diary_count*3 + replies_count*2
  score_daily NUMERIC(8,2),
  score_30d   NUMERIC(10,2),
  PRIMARY KEY (user_id, date)
);

-- Финансовые таблицы
CREATE TABLE mrr_daily_snapshot (
  date         DATE PRIMARY KEY,
  mrr          NUMERIC(12,2),
  active_users INTEGER
);

CREATE TABLE churn_events (
  user_id       BIGINT NOT NULL,
  churn_date    DATE NOT NULL,
  tenure_days   INTEGER,
  last_activity DATE,
  PRIMARY KEY (user_id, churn_date)
);

CREATE TABLE expansion_events (
  user_id     BIGINT NOT NULL,
  event_date  DATE NOT NULL,
  old_mrr     NUMERIC(10,2),
  new_mrr     NUMERIC(10,2),
  PRIMARY KEY (user_id, event_date)
);

-- Связки (самое ценное — то чего нет у большинства клубов)

-- Activity → Retention: 0 сообщений → 22%, 1-5 → 48%, 5+ → 71%
CREATE TABLE retention_by_activity (
  activity_bucket  TEXT NOT NULL, -- '0' | '1-5' | '5-20' | '20+'
  cohort_month     DATE NOT NULL,
  retention_30d    NUMERIC(5,2),
  retention_90d    NUMERIC(5,2),
  PRIMARY KEY (activity_bucket, cohort_month)
);

-- Silent → Churn probability
CREATE TABLE churn_probability (
  user_id               BIGINT PRIMARY KEY,
  probability_30d       NUMERIC(5,2),
  contributing_factors  JSONB,
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

-- Activity → Revenue
CREATE TABLE arpu_by_segment (
  activity_segment  TEXT PRIMARY KEY, -- ghost | low | medium | high
  avg_revenue       NUMERIC(10,2),
  user_count        INTEGER,
  avg_tenure        NUMERIC(6,1)
);

-- LLM-анализ (из agent-analyzer)
CREATE TABLE analyzed_output (
  analysis_type  TEXT NOT NULL, -- insights | emotions | mechanics
  period         TEXT NOT NULL, -- '2026-05' или 'latest'
  json_data      JSONB NOT NULL,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (analysis_type, period)
);
```

---

## Формулы расчётов (ETL)

### KPI
```python
active_subscriptions = COUNT WHERE subscriptions.status = 'active'
mrr                  = SUM(subscriptions.monthly_price) WHERE status = 'active'
chat_active_30       = SUM(active_flag) WHERE date >= today-30  # из user_activity_daily
chat_active_7        = SUM(active_flag) WHERE date >= today-7
chat_never_wrote     = COUNT members WHERE user_id NOT IN user_last_activity
chat_silent_paying   = COUNT subscriptions WHERE status='active'
                       AND last_message_date < today-30  # JOIN user_last_activity
```

### RETENTION
```python
cohort_month         = DATE_TRUNC('month', first_payment_date)
retention_sub[M+N]  = users_active_in_month / cohort_size * 100
retention_bill[M+N] = users_paid_in_month   / cohort_size * 100
```

### USER HEALTH
```python
risk_score  = silent_days * 0.4 + (1 / activity_score) * 0.3 + (tenure_days/30) * 0.3

risk_segment:
  expired   → subscriptions.status != 'active'
  ghost     → total_messages = 0
  high_risk → silent_days >= 30 AND tenure_days > 60
  medium    → silent_days >= 14
  healthy   → иначе
```

### LEADERBOARD
```python
# Из user_activity_score
score_30d      = SUM(score_daily) WHERE date >= today-30
total_messages = user_last_activity.total_messages
diary_messages = SUM(diary_count) FROM user_activity_daily

# streak: последовательные дни с active_flag=1, начиная с сегодня
current_streak = consecutive days ending today WHERE active_flag=1

# Массив 30 булевых
activity_last_30 = [active_flag FOR date IN (today-30 .. today)]
```

### ACTIVITY HEATMAP
```python
# Все даты хранятся в UTC, конвертируем в UTC+3 при агрегации
heatmap[weekday][hour] = COUNT(messages) WHERE
                         EXTRACT(DOW FROM date AT TIME ZONE 'Europe/Moscow') = weekday
                         AND EXTRACT(HOUR FROM date AT TIME ZONE 'Europe/Moscow') = hour
```

### FINANCES
```python
revenue_by_month    = SUM(amount) GROUP BY DATE_TRUNC('month', payment_date)
orders_by_month     = COUNT(order_id) GROUP BY DATE_TRUNC('month', payment_date)

cohort_payments[C][M] = {
  orders:  COUNT(payments WHERE user cohort=C AND payment_month=M),
  revenue: SUM(amount WHERE user cohort=C AND payment_month=M)
}
```

---

## Агенты

| Агент | Расписание | Инструменты | Что делает |
|-------|-----------|-------------|-----------|
| `collector-tg` | каждые 6ч | Telegram Bot API → PostgreSQL | Читает новые сообщения с checkpoint, upsert в messages_raw и members_raw |
| `collector-gc` | каждые 6ч | GetCourse API → PostgreSQL | Читает новые заказы, upsert в payments_raw и members_raw |
| `core-builder` | каждые 2ч | PostgreSQL → PostgreSQL | RAW → CORE, инкрементально от последнего processed_at |
| `analyzer` | 03:00 daily | PostgreSQL + Claude API | Читает messages за период → LLM анализ → пишет в analyzed_output |
| `etl` | 04:00 daily | PostgreSQL → PostgreSQL | CORE + analyzed_output → все MART таблицы |
| `api` | always-on | PostgreSQL → HTTP | FastAPI читает MART → JSON для дашборда |

---

## FastAPI Endpoint

```
GET /api/dashboard
→ Читает последний kpi_snapshot, retention_fact, user_health,
  user_activity_score, analyzed_output, mrr_daily_snapshot,
  cohorts, churn_events, arpu_by_segment
→ Собирает в структуру DATA ZONE
→ Возвращает JSON

GET /api/health
→ Статус агентов, время последнего запуска каждого
```

Ответ `/api/dashboard` совпадает по структуре с текущими DATA ZONE константами в `index.html` — дашборд не требует изменений кроме замены захардкоженных данных на `fetch()`.

---

## Dashboard интеграция

```js
// Заменяет захардкоженные константы в DATA ZONE
async function loadData() {
  const res = await fetch('https://your-app.railway.app/api/dashboard');
  const data = await res.json();
  Object.assign(window, data); // KPI, RETENTION, FINANCES...
  initAll();
}

document.addEventListener('DOMContentLoaded', loadData);
```

---

## Порядок реализации

| Шаг | Что строим | Результат |
|-----|-----------|---------|
| 1 | PostgreSQL + схема всех таблиц | База готова |
| 2 | `subscriptions` + `user_activity_daily` из тестовых данных | CORE работает |
| 3 | KPI пересчитан только из CORE | MRR всегда точный |
| 4 | `collector-tg` + `collector-gc` | Данные текут автоматически |
| 5 | `core-builder` (инкрементальный) | RAW → CORE без перегрузки |
| 6 | `etl` + все MART таблицы | Полный дашборд |
| 7 | `analyzer` (LLM) | INSIGHTS/EMOTIONS/MECHANICS автоматически |
| 8 | FastAPI endpoint | Дашборд читает живые данные |
| 9 | Связки Activity→Retention, Silent→Churn | Продвинутая аналитика |

---

## Главные риски

| Риск | Митигация |
|------|---------|
| Расчёты из RAW напрямую | Запрещено архитектурно — только через CORE |
| MRR неправильный | Считается исключительно из `subscriptions.monthly_price` |
| Дубли при повторном ingestion | Upsert по primary key на всех RAW таблицах |
| Тяжёлые DISTINCT запросы | `user_activity_daily` с `active_flag` убирает их полностью |
| Перегрузка при полном пересчёте | `core-builder` инкрементальный по `ingested_at` |
