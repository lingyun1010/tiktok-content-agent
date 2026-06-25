# Current Checkpoint

## Last updated

2026-06-25

## Current branch

`feature/phase-6-ai-analyst-chat`

## Current phase

Phase 6A AI Analyst Chat MVP is implemented locally.

The dashboard still uses `outputs/latest/dashboard_data.json` as its single
source of truth. The Phase 6A chat panel appears inside the existing static
dashboard and answers questions from the same validated dashboard payload that
renders the page.

No backend API server was added for this MVP. The chat uses deterministic local
analysis in the browser, and a matching Python helper validates the structured
answer shape in automated tests. OpenAI, Claude, Airtable, metrics algorithms,
publishing code, image generation, scheduling, and TikTok upload logic were not
changed.

## Changed files

Backend and tests:

- `src/backend/analyst_chat.py`
- `tests/test_pipeline.py`

Frontend:

- `src/frontend/index.html`
- `src/frontend/styles.css`
- `src/frontend/app.js`

Documentation:

- `README.md`
- `docs/current-checkpoint.md`

## Phase 6A chat behaviour

The chat panel:

- is hidden when `outputs/latest/dashboard_data.json` is missing or invalid,
  because the existing dashboard missing-output state remains active
- reads from the in-memory dashboard payload loaded by `src/frontend/app.js`
- supports simple natural-language questions about strongest/repeat posts,
  retention/watch performance, pause/weak posts, and general run summary
- returns four structured fields: `summary`, `evidence`, `recommendation`, and
  `suggested_next_action`
- has basic loading, empty-question, error, and clear states
- makes no network or provider call

The backend helper in `src/backend/analyst_chat.py` mirrors the same Phase 6A
manual-analysis contract for test coverage and future API/provider extraction.

## Commands verified

```bash
python3 -m unittest discover -v
```

Result: 27 tests passed. One existing optional `python-dotenv` test was skipped
because the package is unavailable in the Codex runtime.

```bash
python3 -m src.backend.pipeline --mode export_only --source csv \
  --input examples/sample_recent_posts.csv --limit 10 --provider manual
```

Result: completed successfully and generated the five existing demo outputs
plus `outputs/latest/dashboard_data.json`. No external API was called.

Additional checks passed:

```bash
python3 -m json.tool outputs/latest/dashboard_data.json
python3 -m compileall src tests
git diff --check
```

Static serving smoke check passed after an approved local-only server run:

```bash
python3 -m http.server 8000
curl -I http://localhost:8000/src/frontend/
curl -I http://localhost:8000/src/frontend/app.js
curl -I http://localhost:8000/outputs/latest/dashboard_data.json
```

Result: all three HTTP requests returned `200 OK`; the temporary server was
stopped after verification.

JavaScript syntax was not checked with `node --check` because `node` is not
installed in this Codex runtime.

## Known issues and limits

- The Phase 6A chat is deterministic/manual, not a live LLM analyst.
- The chat intentionally handles only a small set of common question intents.
- The browser and Python helper currently duplicate the manual answer rules at
  a small scale. A future API-based phase can centralise this logic.
- The dashboard still needs to be served over localhost so it can fetch
  `outputs/latest/dashboard_data.json`.
- `outputs/latest/dashboard_data.json` remains ignored and overwritten by each
  successful pipeline run.

## Next recommended task

Run the offline test suite and sample pipeline. If verified, commit the Phase
6A MVP. A later Phase 6B can add a tiny local API or opt-in OpenAI/Claude
analyst provider using the same structured response fields.

Suggested commit:

```text
Add local AI analyst chat MVP
```
