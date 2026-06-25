# Current Checkpoint

## Last updated

2026-06-25

## Current branch

`feature/phase-6-ai-analyst-chat`

## Current phase

Phase 6B Minimal FastAPI Analyst Server + UI Integration is implemented.

Phase 6A introduced an offline/manual analyst chat in the static frontend using
local rules over `outputs/latest/dashboard_data.json`. Phase 6B moves analyst
chat behind a minimal FastAPI server so the browser can call backend analyst
logic and optional LLM providers without exposing API keys.

The dashboard remains grounded in `outputs/latest/dashboard_data.json`. The
pipeline still writes that file, and the server reads it for both
`GET /api/dashboard-data` and `POST /api/analyst-chat`.

## Changed files

Backend and tests:

- `src/backend/analyst.py`
- `src/backend/analyst_chat.py`
- `src/backend/server.py`
- `tests/test_analyst.py`
- `tests/test_server.py`
- `tests/test_pipeline.py`

Frontend:

- `src/frontend/index.html`
- `src/frontend/styles.css`
- `src/frontend/app.js`
- `src/frontend/README.md`

Documentation and dependencies:

- `README.md`
- `docs/current-checkpoint.md`
- `requirements.txt`

No Airtable ingestion, metrics algorithms, strategy generation transport,
publishing code, TikTok upload placeholder, media generation, scheduling,
database, or authentication architecture was changed.

## Phase 6B API

Run the pipeline first:

```bash
python3 -m src.backend.pipeline --mode export_only --source csv \
  --input examples/sample_recent_posts.csv --limit 10 --provider manual
```

Then start the server:

```bash
python3 -m src.backend.server
```

Open:

```text
http://127.0.0.1:8000/
```

Endpoints:

- `GET /api/health`
- `GET /api/dashboard-data`
- `POST /api/analyst-chat`

`POST /api/analyst-chat` accepts:

```json
{
  "question": "Which posts performed best recently?",
  "provider": "manual"
}
```

Supported analyst providers:

- `manual`: deterministic local rules, no external API
- `openai`: opt-in, server-side `OPENAI_API_KEY`
- `claude`: opt-in, server-side `CLAUDE_API_KEY`

All providers return:

- `summary`
- `evidence`
- `recommendation`
- `suggested_next_action`
- `limitations`
- `provider`
- `llm_called`

## Analyst grounding

The analyst module loads `outputs/latest/dashboard_data.json`, validates the
expected dashboard fields, and compacts the payload into a safe context before
any LLM call. The safe context excludes raw Airtable responses, post URLs,
source captions, notes, credentials, request headers, and secrets.

OpenAI and Claude analyst providers reuse the existing standard-library HTTP
pattern from `llm_strategy.py`, require valid JSON responses, and validate the
structured answer before returning it to the frontend. The frontend never sees
API keys and never calls provider APIs directly.

## Commands verified

Dependencies were installed into ignored local `.venv/` because the system
Python is externally managed:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Full test suite:

```bash
.venv/bin/python -m unittest discover -v
```

Result: 40 tests passed.

Sample pipeline:

```bash
.venv/bin/python -m src.backend.pipeline --mode export_only --source csv \
  --input examples/sample_recent_posts.csv --limit 10 --provider manual
```

Result: completed successfully and generated the five existing demo outputs
plus `outputs/latest/dashboard_data.json`. No external API was called.

Additional checks passed:

```bash
.venv/bin/python -m compileall src tests
.venv/bin/python -m json.tool outputs/latest/dashboard_data.json
git diff --check
```

FastAPI unit tests covered `GET /api/health`, `GET /api/dashboard-data`, and
`POST /api/analyst-chat` in manual mode. A live curl smoke check against the
temporary server could not be completed because the approval system rejected
the local curl requests due to usage-limit policy after the server started.
The temporary server was stopped cleanly.

## Known issues and limits

- Manual analyst mode is deterministic and handles a small set of common
  question intents.
- OpenAI and Claude analyst modes are implemented but were not called live
  during verification.
- The safe LLM context is intentionally compact; it cannot answer questions
  needing impressions, traffic source, follower status, current trend/audio
  metadata, or TikTok distribution diagnostics.
- Browser and backend no longer share local analyst rules; the frontend depends
  on the FastAPI server for chat answers.
- The test run emitted a FastAPI/Starlette deprecation warning about the test
  client using `httpx`; tests still passed.

## Next recommended task

Manually open `http://127.0.0.1:8000/`, test the five manual questions, and then
optionally test OpenAI/Claude with server-side `.env` keys. Do not call paid
providers unless a fresh live-provider result is intentional.

Suggested commit:

```text
Add FastAPI analyst chat server
```
