# Current Checkpoint

## Last updated

2026-06-21

## Current branch

`feature/phase-4-llm-strategy-provider`

## Current phase

Phase 4 is implemented and verified offline.

The deterministic analytics pipeline remains unchanged in responsibility:
Python performs ingestion, canonical normalisation, metric calculation,
rule-based signals, and metrics-summary generation. Strategy generation can now
use the deterministic `manual` provider or explicitly selected `openai` and
`claude` providers.

LLM providers receive only a compact aggregate summary, selected canonical post
signals, the required plan shape, and public brand guidance. Raw records,
captions, URLs, timestamps, notes, credentials, and private files are excluded.
Python validates provider JSON and retains ownership of evidence IDs and
`analysis_basis` metadata before writing outputs.

## Changed files

Implementation and tests:

- `src/backend/llm_strategy.py`
- `src/backend/strategy_agent.py`
- `src/backend/pipeline.py`
- `src/backend/exporters.py`
- `tests/test_pipeline.py`

Prompt and configuration:

- `prompts/content_strategy.md`
- `.env.example`

Documentation:

- `README.md`
- `docs/CONTEXT.md`
- `docs/architecture.md`
- `docs/content-plan-schema.md`
- `docs/project-brief.md`
- `docs/roadmap.md`
- `docs/setup-notes.md`
- `docs/current-checkpoint.md`

## Commands verified

```bash
python3 -m unittest discover -v
```

Result: 25 tests passed. One existing Airtable `.env` integration test was
skipped because `python-dotenv` is not installed in the Codex runtime. Provider
HTTP behaviour and invalid-output handling are mocked; no paid API was called.

```bash
python3 -m src.backend.pipeline --mode export_only --source csv \
  --input examples/sample_recent_posts.csv --limit 10 --provider manual
```

Result: completed successfully and generated all five expected outputs.

```bash
env -u OPENAI_API_KEY -u OPENAI_MODEL python3 -m src.backend.pipeline \
  --mode export_only --source csv --input examples/sample_recent_posts.csv \
  --limit 10 --provider openai
```

Result: stopped before network access with a clear `OPENAI_API_KEY` error.

```bash
env -u CLAUDE_API_KEY -u CLAUDE_MODEL python3 -m src.backend.pipeline \
  --mode export_only --source csv --input examples/sample_recent_posts.csv \
  --limit 10 --provider claude
```

Result: stopped before network access with a clear `CLAUDE_API_KEY` error.

```bash
python3 -m py_compile src/backend/*.py src/backend/ingest/*.py tests/test_pipeline.py
git diff --check
```

Result: completed successfully.

The generated manual plan was parsed as JSON and all five output files were
confirmed non-empty. A repository secret-pattern scan found only the obvious
placeholder values in `.env.example`.

The README usage section was subsequently expanded with environment setup,
copy-ready commands for CSV/Airtable combined with manual/OpenAI/Claude, the
available CLI options, generated outputs, and credential safety guidance. The
documented options were checked against `python3 -m src.backend.pipeline --help`.

## Generated outputs

```text
outputs/demo/metrics_summary.md
outputs/demo/content_plan.json
outputs/demo/script.md
outputs/demo/caption.txt
outputs/demo/hashtags.txt
```

These paths remain ignored by Git.

## Known issues and limits

- No live OpenAI or Claude request was made because explicit approval was not
  given.
- Live account access, billing, selected model availability, and provider-side
  output quality remain unverified.
- LLM output fails clearly on invalid JSON, missing fields, wrong types,
  malformed hashtags, or unknown evidence post IDs; it does not silently fall
  back to manual output.
- TikTok upload, media generation, frontend work, and publishing remain out of
  scope and unchanged.

## Next recommended task

Review the Phase 4 diff. If desired, run one explicitly approved private smoke
test per configured provider, inspect the generated drafts, then commit the
branch. Do not push or merge without a separate instruction.
