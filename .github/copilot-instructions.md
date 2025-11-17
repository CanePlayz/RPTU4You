# RPTU4You Copilot Instructions

## Architecture & Services
- Django lives in `frontend/` with the custom `news` app, project config under `rptu4you/`, and entry orchestration in `entrypoint.py` (runs migrations, seeds vocab, syncs `news/data/public_events.json`).
- Docker compose (`docker-compose-dev.yml`) spins up Postgres 18 (`db`), Redis 7, the Django app, Celery worker/beat/Flower, a `webscraper` container, and Portainer; everything shares the `backend` network.
- `news.models` defines the full domain (custom `User`, multilingual `Quelle` hierarchy, `News`, `Text`, `CalendarEvent`, `OpenAITokenUsage`). Translation fields are managed via `modeltranslation` (`news/translation.py`).
- Static assets live under `frontend/static` and `templates`; Tailwind 4 is built via `frontend/tailwind/package.json` and copied into `static/css/tailwind-built.css` inside the Dockerfile’s Node→Python multi-stage build.
- `webscraper/` (APS cheduler + individual scrapers) posts gzip-compressed payloads to Django at `http://django:8000/api/news/` using the shared `API_KEY` and polls `/api/news/rundmail/date` to only ingest new Rundmail batches.

## Startup & Daily Workflows
- Local bring-up/shutdown and server deploy commands are centralized in `commands.txt`; the default dev loop is `docker compose -f docker-compose-dev.yml up -d --build --force-recreate` and shutdown via `docker compose -f docker-compose-dev.yml down --volumes --remove-orphans`.
- DB backup/restore snippets (local + server) also live in `commands.txt`; prefer those instead of inventing new pg_dump/psql commands because they reset schemas and handle SSH piping correctly.
- `.env` must provide IMAP/SMTP, `API_KEY`, `OPENAI_API_KEY`, and Django superuser variables—`frontend/entrypoint.py` relies on them before it starts Gunicorn or `runserver`.
- Tailwind changes require rerunning `npm run build:css` inside `frontend/tailwind/`; the Docker build already performs this step, so local edits should mimic the same command to avoid drift.
- Health checks live under `news/views/system.py` (`/health`, `/db-connections/`, `/set-language/`), which the scraper and server monitoring rely on—keep responses lightweight and JSON.

## Data Ingest & OpenAI Processing
- `news/views/receive_news.py` owns the ingestion endpoint: it validates the `API-Key`, decompresses JSON, creates/looks up `Quelle` records (with special Rundmail handling), then calls OpenAI cleanup, translation, and categorization helpers.
- The OpenAI helpers under `news/views/processing/**` share token accounting logic via `reserve_tokens`/`release_tokens` and persist quota usage in `OpenAITokenUsage`; always respect the `token_limit` arguments when extending these calls.
- Trusted users (`news/views/trusted.py`) and manual workflows reuse `process_news_entry`, so changes to ingestion must keep both scraper and user submissions working.
- Celery tasks in `news/tasks.py` backfill cleanup/categorization/translations using `ThreadPoolExecutor` plus the `close_db_connection` decorator to avoid lingering DB handles—mirror that pattern when adding new background tasks.
- `news/my_logging.py` provides a single `get_logger` helper so that log formatting stays consistent with the Django logging config defined in `rptu4you/settings.py`.

## Domain Data & Filtering
- `news/util/categories.json` is the single source of truth for content/audience/location categories plus static sources; `entrypoint.py` syncs it into the DB (transactions per section) and the scraper/UI read from it via `news/util/category_registry.py`.
- Filter metadata for the news pages is generated in `news/util/filter_objects.py` and consumed by `news/views/utils.py`; filters operate on slug identifiers while queries use the `filter_field` metadata—keep new filterable models in sync with this pipeline.
- Emoji-rich labels in forms (`news/forms.py`) and filter chips come from the registry; when adding a language or emoji, update the JSON first and rerun the entrypoint seeding.
- User preference storage (`PreferencesForm`) expects Rundmail sources to remain synthetic identifiers (`rundmail`, `sammel_rundmail`); don’t convert them into real `Quelle` rows.
- Public calendar seeds pulled from `news/data/public_events.json` rely on dedupe keys `(title.lower(), start)` in `entrypoint.py`; keep that format if you extend the JSON schema.

## Calendar Subsystem
- REST endpoints in `news/views/calendar.py` drive the `static/js/calendar.js` UI; `/api/calendar-events/` handles both list and create, while `/api/calendar-events/<id>/` supports GET/PUT/DELETE plus whole-series edits via the `all_in_group` flag.
- Recurrence is modeled through `repeat`, `repeat_until`, and a shared `group` value (`_generate_group_value`) so bulk edits/deletes can find entire series—honor `MAX_SERIES_OCCURRENCES` (50) when generating events.
- ICS import/export (`import_ics`, `export_ics`) relies on the `icalendar` library; keep datetime parsing timezone-aware using `_coerce_iso_datetime` and `_ensure_future` helpers before persisting events.
- Auth rules: unauthenticated users only see `is_global=True` events, while owners or staff can mutate personal entries; guard new endpoints the same way to avoid exposing private data.

## External Integrations & Security
- `API_KEY` gates both ingestion and the Rundmail date probe, OpenAI access lives in `OPENAI_API_KEY`, and email notifications for Trusted applications use `EMAIL_JACOB`/IMAP credentials—never hardcode those values in code or fixtures.
- Mail sending in `trusted.py` uses Django’s mail backend with a background thread; if you introduce new notification flows, reuse that pattern so HTTP requests stay non-blocking.
- `webscraper/scheduler.py` waits on `/health` before kicking off APScheduler jobs; if you change the health endpoint path or auth, update the scraper too.
- Ports exposed by Docker: Django `8000`, Flower `5555`, Portainer `9000`; document any new services/ports inside the compose file so ops scripts keep working.
- Admin access is locked down by `news.middleware.AdminAccessRestrictionMiddleware`, and logged-in users auto-redirect to their preferred language via `UserPreferredLanguageMiddleware`—respect these behaviors when adding routes.
