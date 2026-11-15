# DihScript

AI-powered editor for short-form video scripts. Paste a TikTok script, pick a mode, and get back a tightened version with every change explained.

## What it does

DihScript runs your script through an LLM (DeepSeek) in one of two modes:

- **watch** — maximize watch time and views for the broadest possible audience. No call to action.
- **sell** — build trust and convert a specific niche. Requires a target audience and a call to action.

You pick a target length (**30**, **60** or **90** seconds) and get back:

- the fixed script
- editor notes
- a list of changes, each with a reason and the character range it applies to

## Tech stack

- **Backend** — FastAPI + SQLAlchemy/Alembic + MySQL, LLM via the DeepSeek API
- **Frontend** — vanilla HTML/CSS/JS (no framework), served from `web/`
- **Infrastructure** — Docker Compose (app + MySQL)

## Repository layout

- `src/` — FastAPI app (API, services, repositories, database)
- `migrations/` — Alembic migrations
- `prompts/` — LLM prompt templates
- `web/` — static frontend (HTML/CSS/JS)
- `tests/` — test suite

## API

| Method | Endpoint    | Body                                                             | Response                                                          |
| ------ | ----------- | ---------------------------------------------------------------- | ----------------------------------------------------------------- |
| POST   | `/fix`      | `{ mode, script, length, target_audience?, call_to_action?, email }` | `{ script, info, error, changes: [{ start_char, end_char, reason }] }` |
| POST   | `/subscriber` | `{ name, email }`                                              | `{ name, email, run_count }`                                      |

- `mode` is `"watch"` or `"sell"`
- `length` is `30`, `60` or `90`
- in `sell` mode `target_audience` and `call_to_action` are required

## Running locally

### 1. Configure

Copy the example environment and fill in real values:

```bash
cp .env.example .env
```

Required: a DeepSeek API key (`DEEPSEEK_API_KEY`) and database settings. `CORS_ORIGINS` must list the origin you serve the frontend from (e.g. `http://localhost:5500`).

### 2. Start the backend and database

```bash
docker compose up -d
```

This starts MySQL (`ta_database`) and the API (`ta_backend`) on `http://localhost:8000`. Alembic migrations run automatically on startup.

### 3. Serve the frontend

```bash
cd web
python3 -m http.server 5500
```

Open http://localhost:5500. Make sure `http://localhost:5500` is included in `CORS_ORIGINS`.

## Testing

```bash
pytest
```
