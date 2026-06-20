# Current Checkpoint

## Last Updated

2026-06-20

## Current Status

- Phase 0: Completed
- Phase 1: Completed
- Phase 2: Not started

The repository now has a working, offline-first analytics MVP with a canonical
TikTok post schema, deterministic metrics and signals, an LLM-ready Markdown
summary, and a deterministic manual content-plan stub.

## Current Branch / Worktree

- Branch: `codex/implement-phase-1-backend-mvp`
- Worktree: `/Users/lingyunzhao/.codex/worktrees/21ae/TikTok Content Strategy Agent`

This path is environment-specific. A future session should confirm its active
branch and repository root before editing.

## What Works Now

- Reads up to the requested number of synthetic TikTok records from CSV.
- Validates required headers and normalises records into one canonical shape.
- Rejects invalid timestamps, URLs, percentages, counts, durations, platforms,
  and duplicate post IDs.
- Calculates per-post engagement, watch, and optional region metrics.
- Compares format and topic performance.
- Produces deterministic, dataset-relative rule-based signals.
- Generates an LLM-ready Markdown performance brief.
- Generates a deterministic JSON content-plan stub through the `manual`
  provider.
- Handles zero-view records without division errors.
- Runs using Python 3.10+ and the standard library only.
- Makes no network requests or external API calls.

The static frontend remains a concept and does not consume the generated
outputs.

## Phase 1 Summary

Phase 1 strengthened the original scaffold without introducing external
services. It added:

- a canonical, typed TikTok post record
- strict CSV header and row validation
- updated synthetic sample data
- richer per-post and aggregate metrics
- format-level and topic-level comparisons
- six explainable performance signals
- top-performing and weak-performing post rankings
- audience-region notes
- a more useful LLM-ready `metrics_summary.md`
- expanded offline tests
- documentation for the schema, thresholds, limitations, and roadmap status

The existing public CLI contract and deterministic
`content_plan_stub.json` output were preserved.

## Canonical TikTok Post Schema

Required CSV fields:

```text
post_id
platform
published_at
format
topic
hook
caption
duration_seconds
views
likes
comments
shares
```

Optional CSV fields:

```text
post_url
saves
average_watch_time_seconds
completion_rate
top_region
target_region
top_region_view_percentage
notes
```

Important validation rules:

- `platform` must be `tiktok`.
- `published_at` must be an ISO 8601 datetime.
- `duration_seconds` must be greater than zero.
- View and engagement count fields must be non-negative whole numbers.
- Percentage fields must be between 0 and 1.
- `post_url`, when supplied, must be an absolute HTTP(S) URL.
- Optional blank values remain unavailable rather than being invented.
- Post IDs must be unique within the analysed records.

The detailed source of truth is
[`canonical-schema.md`](canonical-schema.md).

## Metrics Supported

```text
like_rate           = likes / views
comment_rate        = comments / views
share_rate          = shares / views
save_rate           = saves / views, when saves are available
engagement_rate     = (likes + comments + shares + available saves) / views
average_watch_ratio = average_watch_time_seconds / duration_seconds
```

When views are zero, view-based rates are `0.0`.

`region_match_score` is available only when `top_region`, `target_region`, and
`top_region_view_percentage` exist:

- matching top and target regions: `top_region_view_percentage`
- different top and target regions: `1 - top_region_view_percentage`

The region score is a conservative proxy because the current schema records
only the largest observed region share, not a complete regional distribution.

Aggregate analysis now includes:

- dataset totals and averages
- top-performing and weak-performing posts
- format performance
- topic performance
- signal counts and affected post IDs
- region-field coverage and average region match score

## Rule-Based Signals Supported

- `high_view_low_engagement`
- `low_view_high_save`
- `good_hook_weak_retention`
- `wrong_region_distribution`
- `repeat_candidate`
- `pause_candidate`

Dataset averages define the relative high/low thresholds for views, like rate,
save rate, engagement rate, and supported retention. Weak retention means
`average_watch_ratio < 50%`; wrong-region distribution means
`region_match_score < 50%`.

These signals are deterministic observations and testing prompts. They are not
causal findings or performance guarantees.

## Commands Verified

The complete offline test suite passed:

```bash
python3 -m unittest discover -v
```

Result: 8 tests passed.

The public sample pipeline command also completed successfully:

```bash
python3 -m src.backend.pipeline --mode export_only --input examples/sample_recent_posts.csv --limit 10
```

Both commands were verified from the repository root on 2026-06-20.

## Generated Outputs

The sample pipeline generates:

```text
outputs/demo/metrics_summary.md
outputs/demo/content_plan_stub.json
```

`outputs/` is intentionally ignored by Git because future local runs may
contain private analytics or strategy material.

## Security Notes

- No external APIs are currently called.
- The MVP does not connect to Airtable, TikTok, OpenAI, DeepSeek, or any other
  external service.
- Do not commit secrets, `.env` files, credentials, tokens, account names,
  private URLs, customer data, real analytics, or real generated strategy.
- Keep real data and generated private material only in ignored paths:
  `data/raw/`, `data/processed/`, `outputs/`, and `logs/`.
- Only clearly fictional synthetic data belongs under `examples/`.
- Future provider or publishing work must remain explicitly opt-in and
  human-reviewed.

## Files Changed

Main Phase 1 implementation files:

- `src/backend/schema.py`
- `src/backend/csv_source.py`
- `src/backend/normalise.py`
- `src/backend/metrics.py`
- `src/backend/exporters.py`
- `src/backend/strategy_agent.py`
- `examples/sample_recent_posts.csv`
- `tests/test_pipeline.py`

Main Phase 1 documentation files:

- `AGENTS.md`
- `README.md`
- `docs/canonical-schema.md`
- `docs/CONTEXT.md`
- `docs/architecture.md`
- `docs/project-brief.md`
- `docs/roadmap.md`
- `docs/setup-notes.md`
- `docs/current-checkpoint.md`

## Known Limitations

- Only local CSV ingestion is implemented.
- The region match score is a proxy, not a complete regional analysis.
- Group comparisons use a small recent dataset and may contain single-post
  groups.
- Signals use simple averages and fixed thresholds rather than statistical
  significance.
- `completion_rate` is validated and retained but is not yet used by a rule.
- The manual content plan remains a deterministic stub; it does not yet turn
  all Phase 1 signals into a structured strategy.
- OpenAI and DeepSeek provider names are reserved but not implemented.
- TikTok authentication, upload, scheduling, and publishing remain out of
  scope.

## Next Recommended Phase

Phase 2: Manual Strategy Mode

The next phase should convert Phase 1 metrics and signals into a useful,
deterministic, human-reviewable content plan. It must remain offline and must
not add Airtable, external LLM calls, media generation, or TikTok publishing.

## Suggested Next Codex Prompt

```text
Implement Phase 2 only: deterministic manual strategy mode.

Start by reading AGENTS.md, README.md, docs/current-checkpoint.md,
docs/canonical-schema.md, docs/architecture.md, docs/roadmap.md, and the current
backend/tests. Treat the repository as the source of truth.

Use the existing Phase 1 metrics and rule-based signals to replace the fixed
manual content-plan stub with a stable, documented content-plan schema and
deterministic recommendations. Recommendation reasons must point to specific
metrics or signals. Preserve the current offline sample command, require human
review, add tests, and update affected documentation.

Do not add Airtable, OpenAI, DeepSeek, external APIs, media generation, TikTok
authentication, upload, scheduling, or publishing. Do not commit changes.

Run:
python3 -m unittest discover -v
python3 -m src.backend.pipeline --mode export_only --input examples/sample_recent_posts.csv --limit 10

Inspect the generated outputs and update docs/current-checkpoint.md before
finishing.
```

## Suggested Commit Message

```text
feat: complete phase 1 backend analytics
```

## Before Stopping or When Usage Is Low

Update this file before pausing, before context is lost, when Codex usage is
running low, or after meaningful changes.

`AGENTS.md` now makes this checkpoint update mandatory at the end of every
meaningful task, before handing control back, before continuing a task that is
becoming long, after completing a phase, and before a long-running session may
lose context.

Future Codex sessions should record:

- the current branch and worktree
- completed and pending phases
- meaningful implementation and documentation changes
- commands actually verified
- generated output expectations
- known failures, blockers, or unverified behaviour
- the safest next task and any explicit non-goals

Do not rely on chat history alone for project continuity.

## Latest Documentation Update

The checkpoint and handoff workflow was added to `AGENTS.md`.

- Current phase: Phase 1 completed; Phase 2 not started.
- Changed files: `AGENTS.md`, `docs/current-checkpoint.md`.
- Verified commands: documentation claims inspected; `git diff --check`.
- Generated outputs: unchanged; the expected files remain
  `outputs/demo/metrics_summary.md` and
  `outputs/demo/content_plan_stub.json`.
- Known issues: none introduced by this documentation-only change.
- Next recommended task: Phase 2 manual strategy mode.
