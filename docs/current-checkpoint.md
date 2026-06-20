# Current Checkpoint

## Last updated

2026-06-20

## Current branch

`feature/phase-3-airtable-ingestion`

The branch was verified clean at Phase 2 merge commit `003e242` before Phase 3
work began.

## Phase status

- Phase 0: Completed
- Phase 1: Completed
- Phase 2: Completed and merged
- Phase 3: Implemented and verified offline

Phase 3 adds optional Airtable ingestion while preserving CSV as the default.
The Airtable adapter reads configuration only from environment variables, maps
canonical field names, paginates up to `--limit`, and does not expose secrets
or private Airtable identifiers in generated reports.

Local development now loads those variables from an ignored repository-root
`.env` file through `python-dotenv`. Existing shell variables take precedence.

## Changed files

Implementation and tests:

- `src/backend/ingest/__init__.py`
- `src/backend/ingest/airtable.py`
- `src/backend/pipeline.py`
- `src/backend/exporters.py`
- `src/backend/normalise.py`
- `tests/test_pipeline.py`
- `requirements.txt`

Configuration and documentation:

- `.env.example`
- `README.md`
- `docs/setup-notes.md`
- `docs/current-checkpoint.md`

## Commands verified

```bash
python3 -m unittest discover -v
```

Result: 12 tests passed and the `.env` integration test was skipped because
dependency installation was not approved in this environment. Airtable HTTP
behaviour is mocked; tests make no external API calls.

```bash
python3 -m src.backend.pipeline --mode export_only --input examples/sample_recent_posts.csv --limit 10
```

Result: completed successfully and generated all five expected demo outputs.

```bash
env -u AIRTABLE_API_KEY -u AIRTABLE_BASE_ID -u AIRTABLE_TABLE_ID -u AIRTABLE_VIEW_ID \
  python3 -m src.backend.pipeline --source airtable --limit 1
```

Result: exited clearly with the names of all missing variables and no secret
values.

```bash
python3 -m py_compile src/backend/*.py src/backend/ingest/*.py tests/test_pipeline.py
git diff --check
```

Result: completed successfully.

## Generated outputs

The unchanged CSV command generated:

```text
outputs/demo/metrics_summary.md
outputs/demo/content_plan.json
outputs/demo/script.md
outputs/demo/caption.txt
outputs/demo/hashtags.txt
```

These paths remain ignored by Git.

## Known limitations

- A live Airtable request was not run because no real credentials or private
  data were used.
- Airtable fields must use the canonical names documented in
  `docs/canonical-schema.md`.
- Airtable configuration uses stable table (`tbl...`) and view (`viw...`) IDs.
- Airtable is opt-in and requires network access plus all four `AIRTABLE_*`
  environment variables.
- No OpenAI, DeepSeek, media generation, TikTok upload, scheduling, or
  publishing capability was added.

## Next recommended task

Review Phase 3 with a private test base outside the default test suite, then
commit and open a pull request only when explicitly requested.
