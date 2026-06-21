# Current Checkpoint

## Last updated

2026-06-21

## Current branch

`feature/phase-5-frontend-dashboard`

## Current phase

Phase 5 dashboard data consistency is implemented and verified.

One pipeline run now produces one complete frontend contract at
`outputs/latest/dashboard_data.json`. The dashboard fetches only that file and
renders its dataset overview, safe normalised posts, metrics, signals, provider
plan, script, caption, hashtags, and review notes.

The frontend does not mix committed sample values with generated Airtable,
OpenAI, Claude, or manual results. When the JSON file is missing or invalid, all
dashboard visuals are hidden and the page shows only the pipeline commands
needed to generate it.

## Changed files

Backend and tests:

- `src/backend/exporters.py`
- `src/backend/pipeline.py`
- `tests/test_pipeline.py`

Frontend:

- `src/frontend/index.html`
- `src/frontend/styles.css`
- `src/frontend/app.js`
- `src/frontend/README.md`

Public demo files:

- `examples/sample_content_plan.json`
- `examples/sample_metrics_summary.md`

Documentation:

- `README.md`
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/setup-notes.md`
- `docs/current-checkpoint.md`

No metrics algorithm, Airtable ingestion, provider request logic, credentials,
publishing code, authentication, API server, or database was changed.

## Commands verified

```bash
python3 -m unittest discover -v
```

Result: 25 tests passed. One existing optional `python-dotenv` test was skipped
because the package is unavailable in the Codex runtime.

```bash
python3 -m src.backend.pipeline --mode export_only --source csv \
  --input examples/sample_recent_posts.csv --limit 10 --provider manual
```

Result: completed successfully and generated the five existing demo outputs
plus `outputs/latest/dashboard_data.json`. No external API was called.

Python compilation, JSON parsing, ignored-output checks, and
`git diff --check` also passed.

## Dashboard data contract

The JSON includes:

- UTC `generated_at`
- source and provider
- dataset overview
- safe normalised post summaries
- metrics-summary path and content
- validated content plan and path
- script, caption, hashtags, and human-review notes

It excludes raw Airtable responses, source post captions and URLs, notes,
credentials, request headers, secrets, and private debug data.

## Frontend verification

Using the documented local server:

```bash
python3 -m http.server 8000
```

Verified at `http://localhost:8000/src/frontend/`:

- the page loaded `outputs/latest/dashboard_data.json`
- all 10 normalised post rows rendered from the CSV pipeline run
- source, provider, metric cards, top post, signals, recommendation, and drafts
  matched the same payload
- there was no horizontal overflow or browser console error
- removing the JSON hid all dashboard visuals
- the missing state displayed `No pipeline output found.` and both example
  pipeline commands
- restoring the JSON restored the complete dashboard

## Generated outputs

```text
outputs/demo/metrics_summary.md
outputs/demo/content_plan.json
outputs/demo/script.md
outputs/demo/caption.txt
outputs/demo/hashtags.txt
outputs/latest/dashboard_data.json
```

All remain ignored by Git.

## Known issues and limits

- The browser page must be served over localhost; `file://` commonly blocks the
  JSON fetch.
- Reload the browser after each pipeline run.
- The latest run overwrites `outputs/latest/dashboard_data.json` by design.
- Publishing and media generation remain out of scope.

## Next recommended task

Run the desired Airtable/provider command, start the local server, and refresh
the dashboard. Do not call OpenAI or Claude again unless a fresh provider result
is intentionally required.

Suggested commit:

```text
Fix dashboard pipeline data consistency
```

Do not push or merge without a separate instruction.
