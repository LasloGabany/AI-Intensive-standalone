# Лендинг «Интенсив для психологов» (clubromanova)

Next.js App Router + TypeScript. Светлый luxury-дизайн. Контент перенесён из
Tilda-экспорта (`AI Intensive.html`). Реализует **Landing UI MVP** из
`PRD-yromanova-landing.md`.

## Запуск

```bash
npm install
npm run dev      # http://localhost:3000
npm run build && npm start
```

## Что сделано (этот заход — Landing UI MVP)

- **Дизайн-система** (`app/globals.css`): тёплая палитра oklch, шрифты
  Cormorant Garamond (display) + Manrope (body), токены spacing/motion,
  compositor-friendly анимации, `prefers-reduced-motion`.
- **10 секций** (`app/page.tsx`): hero, боли, метод «Вытащи из меня», 3 дня,
  fit/not-fit, эксперты, отзывы, формат, value-stack, CTA-форма.
- **Лид-форма** (`components/LeadForm.tsx` → `app/api/lead/route.ts`):
  client → свой `/api/lead` (не прямой POST в GetCourse).
  - server-side валидация (имя/email), honeypot, per-IP rate-limit (5/мин),
    no-PII логи. Дружелюбные ошибки, success-состояние на своём домене.
- **A11y/семантика**: `<header>/<main>/<footer>`, заголовки, списки, focus-ring,
  reduced-motion. **Адаптив**: проверено 390 / 1440.

Проверено локально (preview): hero, все секции (snapshot), мобильный вид,
матрица `/api/lead` (200/400/400/200-drop/400/429), happy-path формы → 200.

## P2 — Forms + GetCourse proxy (готово, TDD)

- `lib/getcourse.ts` — `buildParams` (base64 import-формат), `submitLead`
  (POST `/pl/api/users`, ретрай на 5xx/сеть, без ретрая на 4xx/business-error),
  `safeLogLine` (без PII).
- `app/api/lead/route.ts` — env-gated: `GC_ACCOUNT`+`GC_API_KEY` → GetCourse;
  нет → accept-stub (dev). FR-4: при отказе после ретраев и заданном
  `LEAD_REPLAY_DIR` → private JSONL replay queue + `202 { queued: true }`;
  без `LEAD_REPLAY_DIR` → 502 + zero-PII лог-маркер `gc-fail-needs-replay`.
- `lib/lead-replay-queue.ts` — append-only `pending.jsonl` очередь с правами 0700/0600.
- Тесты: `lib/getcourse.test.ts` (7), `lib/lead-replay-queue.test.ts` (2).

### GetCourse env

```
GC_ACCOUNT=clubromanova
GC_API_KEY=<secret key из GetCourse>   # /pl/api/users
GC_GROUP=Интенсив                       # опц., группа пользователя
LEAD_REPLAY_DIR=/secure/leads/replay     # durable JSONL queue при отказе GetCourse
PUBLIC_SITE_URL=https://example.com       # canonical URL для metadata/privacy
PRIVACY_OPERATOR_NAME=<legal operator>    # юр. лицо / ИП / оператор данных
PRIVACY_CONTACT_EMAIL=privacy@example.com # запросы по персональным данным
MANAGED_LEAD_QUEUE_CONFIRMED=true         # true только если queue подходит для infra
DKIM_CONFIRMED=true                       # DNS/email readiness
DMARC_CONFIRMED=true                      # DNS/email readiness
DOMAIN_RENEWAL_CONFIRMED=true             # домен продлён и под контролем
NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX             # опц., Google Analytics после consent
NEXT_PUBLIC_YM_ID=12345678                 # опц., Яндекс Метрика после consent
KEYSTATIC_ADMIN_ENABLED=false              # prod admin disabled by default
KEYSTATIC_ADMIN_USER=<editor>              # required only when KEYSTATIC_ADMIN_ENABLED=true
KEYSTATIC_ADMIN_PASSWORD=<strong password> # required only when KEYSTATIC_ADMIN_ENABLED=true
```



### Production readiness check

Перед запуском прод-окружения:

```bash
npm run prod:check
```

Скрипт проверяет обязательные env, privacy contact, GetCourse, replay queue и
ручные подтверждения DNS/email/domain. Он не печатает значения секретов: только
`set/missing/confirmed`.

Перед cutover можно запустить полный launch gate:

```bash
npm run launch:check
```

`launch:check` объединяет production readiness, unit/integration tests, Next build
и secret scan.

Для serverless или нескольких инстансов file-backed `LEAD_REPLAY_DIR` нельзя
считать достаточным без отдельного managed storage решения. В таком случае
`MANAGED_LEAD_QUEUE_CONFIRMED=true` ставится только после подключения KV/Redis/S3
или другого общего хранилища для replay queue.

### Replay queued leads

Если GetCourse недоступен, `/api/lead` при `LEAD_REPLAY_DIR` сохраняет заявку в
`pending.jsonl`. Операторские команды не печатают raw PII в stdout.

```bash
npm run replay:leads -- --list --dir "$LEAD_REPLAY_DIR"
npm run replay:leads -- --dry-run --replay --limit 10 --dir "$LEAD_REPLAY_DIR"
GC_ACCOUNT=clubromanova GC_API_KEY=<secret> npm run replay:leads -- --replay --limit 10 --dir "$LEAD_REPLAY_DIR"
npm run replay:leads -- --mark-processed <id> --note "handled manually" --dir "$LEAD_REPLAY_DIR"
npm run replay:leads -- --mark-failed <id> --note "duplicate" --dir "$LEAD_REPLAY_DIR"
```

Успешный replay переносит запись из `pending.jsonl` в `processed.jsonl`.
Неуспешная попытка остаётся в `pending.jsonl` и добавляет audit-запись в
`failed.jsonl`.


## P6 — Content Admin / Keystatic (готово, TDD)

Локальная админка доступна на:

```bash
npm run dev
open http://localhost:3000/keystatic
```

Редактируемый singleton: `content/settings/index.json`. Сейчас через админку можно менять
даты интенсива, hero/CTA тексты, цену/якорь и включать/выключать крупные секции
лендинга. Лендинг читает настройки через `lib/landing-settings.ts`; пустые строки и
невалидные toggle-значения откатываются к безопасным defaults из `lib/content.ts`.

Production access policy:

- В `development` `/keystatic` и `/api/keystatic` открыты для локальной работы.
- В `production` админка по умолчанию выключена и отдаёт 404.
- Чтобы включить production admin, нужно явно задать:

```bash
KEYSTATIC_ADMIN_ENABLED=true
KEYSTATIC_ADMIN_USER=<editor>
KEYSTATIC_ADMIN_PASSWORD=<strong password>
```

`npm run prod:check` проверяет, что включенная production admin защищена
логином/паролем, и не печатает секретные значения. Keystatic сейчас использует
`storage: { kind: "local" }`, поэтому для Vercel/serverless editing нужен переход на
GitHub storage или другой writable backend.

Тесты: `lib/landing-settings.test.ts` (5), `lib/admin-access.test.ts` (6),
`prod-readiness` admin cases (3).

## P5 — Launch QA / SEO / Analytics (готово, TDD)

- `lib/site.ts` — единый source of truth для canonical URL, title/description.
- `app/sitemap.ts`, `app/robots.ts`, metadata в `app/layout.tsx` — sitemap,
  robots, canonical и OpenGraph от `PUBLIC_SITE_URL`.
- `lib/analytics.ts`, `components/AnalyticsConsent.tsx` — public analytics IDs,
  consent banner, GA/Яндекс Метрика подключаются только после разрешения.
- CSP `connect-src` разрешает consented analytics beacons.
- Тесты: `lib/site.test.ts` (3), `lib/analytics.test.ts` (4),
  `lib/security-headers.test.ts` analytics case.

## P4 — Security hardening (готово, TDD)

- `lib/security-headers.ts` — `buildCsp` (script-src nonce+strict-dynamic,
  style-src 'self' 'unsafe-inline', upgrade-insecure в prod, unsafe-eval только
  dev), `securityHeaders` (HSTS/nosniff/X-Frame DENY/Referrer/Permissions).
- `proxy.ts` — per-request CSP nonce (Next 16 proxy), x-nonce → framework scripts.
- `app/global-error.tsx` — error-boundary.
- `scripts/secret-scan.sh` — gate: GetCourse-host/ключи не в client bundle.
- Тесты: `lib/security-headers.test.ts` (6). Гейт: `npm run gate`.

> **Tradeoff (НЕ-static рендер).** Страница = `export const dynamic =
> 'force-dynamic'`. Причина: CSP-nonce (NFR-1, §7 security gate — блокер релиза)
> требует динамического рендера, иначе static HTML несёт nonce-less скрипты,
> которые strict-dynamic CSP блокирует в prod. Security gate приоритетнее
> static-перфа (NFR-5, ниже по приоритету). Проверено: prod CSP без unsafe-eval,
> 22/22 скрипта с nonce, форма работает, 0 CSP-violations в консоли.
> Когда понадобится static/ISR — перейти на hash-based CSP или edge-кэш.

## Что НЕ сделано (отложено из PRD, требует прод-инфры)

- **DKIM/DMARC** (часть §7): DNS-записи, вне кода — нужен доступ к зоне (P0/P5).
- **Managed durable queue** для FR-4 replay: сейчас есть `LEAD_REPLAY_DIR` JSONL queue; для serverless/мульти-инстансов нужен KV/Redis/S3-backed storage.
- **P5 Cutover вне кода**: 301-карта на старом хостинге, DNS-перенос.
- **P6 prod editing storage**: Keystatic local storage работает локально/self-hosted; для Vercel/serverless нужен GitHub storage.
- **P0**: продление домена (exp 2026-06-23), выгрузка лидов Tilda.
- Тесты (`§11`): юнит/integration/e2e/visual — каркас не добавлен в этот заход.

## Структура

```
app/
  layout.tsx        шрифты + metadata
  page.tsx          сборка секций + settings + analytics consent
  robots.ts         robots.txt
  sitemap.ts        sitemap.xml
  globals.css       дизайн-токены
  api/lead/route.ts серверный приём лида (валидация/honeypot/rate-limit)
  api/keystatic/    Keystatic route handler
  keystatic/        Keystatic admin UI
components/
  Reveal.tsx        scroll-reveal (IntersectionObserver)
  LeadForm.tsx      client-форма
  AnalyticsConsent.tsx consent-gated analytics loader
  sections.css      стили секций
lib/content.ts      базовый копирайт/defaults
lib/landing-settings.ts Keystatic settings loader + normalization
content/settings/   editable landing singleton
```
