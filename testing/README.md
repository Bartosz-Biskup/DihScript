# Fixer testing tool

Internal web app for testing the script-fixer pipeline (the `/fix` endpoint) and
the LLM behind it. Runs as a standalone FastAPI app, fully separate from the main
app: its own process, its own SQLite database (no alembic), its own prompts.

## Running

Start the main app (it must be reachable for tests to run):

```bash
PYTHONPATH=src uvicorn api.main:app --port 8000
```

Start the testing tool:

```bash
.venv/bin/uvicorn testing.main:app --port 8001
```

Open http://127.0.0.1:8001/testing/.

## What it does

- **Manual** — full form with every option of `POST /fix` (email, mode, length,
  script, target audience, CTA). Clicking *Run test* calls the real `/fix`
  endpoint, then asks a judge LLM (separate prompt) to rate the fixed script.
  You can save the input + fixed script + verdict into the local database.
- **Automatic** — upload a JSON file with up to 1000 inputs plus one group name
  and one subscriber email. Clicking *Start run* executes every input through the
  same fix + judge flow as a background job, strictly one test at a time, with a
  progress bar and per-run results saved as they finish.
- **Browse** — groups are shown collapsed; open a group to page through its runs
  (up to 100+ without flooding the UI). Every run shows the original script, the
  fixed script, the fixer's changes, and the judge's verdict. A group-level
  "what went wrong" LLM summary is generated on demand with a button.
  Manual runs are listed separately as individual records.

## Automatic input JSON format

An array of items, one per test. Each item has everything from `PromptFixRequest`
except the email (one email is used for the whole group):

```json
[
  {"mode": "watch", "script": "so i found this hack...", "length": 30},
  {"mode": "sell", "script": "want bigger arms?", "length": 60,
   "target_audience": "young gym beginners", "call_to_action": "follow for part 2"}
]
```

`mode` defaults to `watch`, `length` defaults to `30` (`30|60|90`). In `sell` mode
`target_audience` and `call_to_action` are required; in `watch` mode they are
ignored.

## Configuration (env vars)

| Variable          | Default                          | Meaning                                   |
| ----------------- | -------------------------------- | ----------------------------------------- |
| `MAIN_API_URL`    | `http://127.0.0.1:8000`          | Base URL of the main app                  |
| `JUDGE_MODEL`     | `LLM_MODEL` or `gpt-4o-mini`     | Model that rates the results              |
| `TESTING_DB_URL`  | `sqlite:///<testing/data/testing.db>` | Where results are stored              |
| `TESTING_DATA_DIR`| `<testing/data>`                 | Directory for the default database file   |

The judge prompt lives in [`prompts/judge.txt`](prompts/judge.txt) and the group
summary prompt in [`prompts/group_summary.txt`](prompts/group_summary.txt).

## Notes

- One job runs at a time, process-wide. Starting a group while another job runs
  returns 409, and manual runs return 409 while an automatic job is running.
- The main app's `/fix` requires the email to be a real subscriber; every test
  bumps that subscriber's `run_count` in the main app's database.
- If a fixer call fails (network error, unknown email), that run is marked
  `failed` with the error and the group continues.
- If the fixer itself returns an `error` field, the judge is skipped for that run
  (token saving) and the verdict stays empty.
- On startup, groups left in `running` state by a crash are reset to `pending`.
