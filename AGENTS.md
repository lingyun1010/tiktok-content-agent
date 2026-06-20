# AGENTS.md

## Project Identity

This repository is `tiktok-content-agent`, a public portfolio project that
demonstrates an offline-first, AI-ready TikTok content strategy pipeline.

It is designed for small direct-to-consumer (DTC) brands that want to turn
recent TikTok performance data into understandable metrics and, in future
versions, reviewable content recommendations, scripts, captions, hashtags, and
draft publishing payloads.

## Core Principle

Codex and other coding agents are used to develop and maintain this project.
They are not the long-running production analyst.

Production behaviour must be implemented as ordinary, testable code that can
run locally, in CI, or in a future scheduled environment. Do not make core
application behaviour depend on an interactive agent session.

## Source of Truth

Before changing the project, inspect the repository rather than assuming a
feature exists.

Use these files as the primary guides:

- `README.md` for the public project overview and primary run command.
- `docs/project-brief.md` for product scope and non-goals.
- `docs/CONTEXT.md` for business context and data assumptions.
- `docs/architecture.md` for module boundaries and security design.
- `docs/setup-notes.md` for setup, environment variables, and verification.
- `.gitignore` for data and output paths that must remain private.

When code and documentation disagree, verify the implementation and update the
stale documentation in the same change.

## Checkpoint and Handoff Requirement

Treat `docs/current-checkpoint.md` as the handoff document for future Codex
sessions and human developers.

At the end of every meaningful task, update `docs/current-checkpoint.md` before
summarising or handing control back.

If a task is becoming long, update the checkpoint before making further
changes. Also update it before pausing work, after completing a phase, or before
a long-running session may lose context.

Each checkpoint update should record, as applicable:

- current phase
- changed files
- verified commands
- generated outputs
- known issues
- next recommended task

Do not rely on chat history as the only record of project state.

## Public Repository Rules

This is a public GitHub repository.

Never commit:

- `.env` or other local environment files
- API keys or access tokens
- Airtable, TikTok, OpenAI, or DeepSeek credentials
- real TikTok analytics or customer data
- real brand strategy outputs or generated private content plans
- account names, private URLs, or internal identifiers
- raw or processed private data
- local logs, caches, or generated outputs

Use only synthetic, clearly fictional data under `examples/`.

Store real local data only in ignored directories:

- `data/raw/`
- `data/processed/`
- `outputs/`
- `logs/`

Use `.env.example` for variable names and obvious placeholder values only.
Never print secrets in logs, errors, test snapshots, or generated reports.

## Repository Structure

- `src/backend/` — Python ingestion, normalisation, metrics, exports, and
  strategy-provider boundaries
- `src/frontend/` — minimal dashboard/frontend placeholder
- `docs/` — product, context, architecture, and setup documentation
- `examples/` — synthetic sample inputs safe to publish
- `prompts/` — versioned prompt templates for future provider adapters
- `tests/` — offline automated tests
- `data/raw/` — ignored local source data
- `data/processed/` — ignored local transformed data
- `outputs/` — ignored generated reports and content plans

Do not move private runtime data into committed example or documentation
directories.

## Current Verified MVP

The current MVP:

- reads a local sample CSV
- validates and normalises canonical TikTok post records
- calculates like, comment, share, save, engagement, watch, and optional region metrics
- compares performance by format and topic
- assigns deterministic rule-based performance signals
- writes `outputs/demo/metrics_summary.md`
- writes `outputs/demo/content_plan.json`
- writes `outputs/demo/script.md`, `caption.txt`, and `hashtags.txt`
- generates a versioned plan and drafts through the deterministic `manual` provider
- includes reserved interfaces for `openai` and `deepseek`
- includes a non-operational TikTok upload placeholder
- includes a static HTML/CSS/JavaScript dashboard concept

The MVP does not call Airtable, TikTok, OpenAI, DeepSeek, or any other external
API.

## Backend Development Rules

Use Python 3.10 or newer.

Prefer:

- standard-library solutions while the MVP remains small
- simple modules with clear responsibilities
- readable code over clever abstractions
- type hints for public boundaries and non-obvious structures
- docstrings for important public functions and classes
- deterministic offline behaviour for tests and demos

Keep these concerns separate:

- ingestion from normalisation
- normalisation from metric calculation
- metric calculation from strategy generation
- provider-specific code from provider-independent orchestration
- analysis from publishing or upload logic
- file export from business logic where practical

Do not introduce a framework, database, queue, or build system unless the task
needs it and the added complexity is documented.

## CLI Contract

Preserve this public MVP command:

```bash
python -m src.backend.pipeline --mode export_only --input examples/sample_recent_posts.csv --limit 10
```

On systems where Python is exposed only as `python3`, the equivalent command
is:

```bash
python3 -m src.backend.pipeline --mode export_only --input examples/sample_recent_posts.csv --limit 10
```

The command must:

1. Read the sample CSV.
2. Normalise at most 10 records.
3. Calculate supported metrics safely, including zero-view handling.
4. Generate `outputs/demo/metrics_summary.md`.
5. Generate `outputs/demo/content_plan.json`.
6. Generate `outputs/demo/script.md`, `caption.txt`, and `hashtags.txt`.
7. Make no network or external API calls.

If this contract changes, update `README.md`, `docs/setup-notes.md`, and tests
in the same change.

## Metric Rules

Use views as the denominator for rate metrics:

- `like_rate = likes / views`
- `comment_rate = comments / views`
- `share_rate = shares / views`
- `save_rate = saves / views`, only when saves are available
- `engagement_rate = (likes + comments + shares + available saves) / views`
- `average_watch_ratio = average_watch_time_seconds / duration_seconds`, only
  when both values are available and duration is greater than zero
- `region_match_score = top_region_view_percentage` when top and target regions
  match; otherwise `1 - top_region_view_percentage`, only when all region fields
  are available

When views are zero, return zero-valued rate metrics rather than raising a
division error. Do not silently invent missing values.

## LLM Provider Rules

The provider boundary supports these names:

- `manual`
- `openai`
- `deepseek`

Only `manual` is implemented in the MVP. It must remain deterministic and must
not require credentials or network access.

For future provider implementations:

- make calls explicitly opt-in
- isolate provider-specific code
- send structured summaries rather than unrestricted private files
- validate structured responses before exporting them
- never log credentials
- retain a human-review requirement before publishing

Do not call real OpenAI, DeepSeek, Airtable, or TikTok APIs during routine
scaffolding or offline tests.

## TikTok Publishing Rules

TikTok authentication, scheduling, upload, and publishing are out of scope for
the MVP.

Keep `src/backend/tiktok_uploader.py` non-operational until a future task
explicitly defines:

- authentication and token handling
- user consent
- draft versus direct-publish behaviour
- human review
- error recovery
- auditability
- safe test accounts and test data

Never turn the placeholder into automatic publishing as an incidental change.

## Frontend Development Rules

Keep the frontend minimal until there is a stable data or API contract.

The current static HTML/CSS/JavaScript approach is sufficient. A framework such
as React or Vite should be added only when interactive requirements justify the
dependency and build setup.

The frontend may eventually display:

- recent post metrics
- performance summaries
- content recommendations
- generated scripts
- captions and hashtags

Do not duplicate backend metric or strategy logic in browser code.

## Documentation Rules

Documentation must be useful to:

- future coding-agent sessions
- human contributors and reviewers
- GitHub visitors
- hiring managers evaluating the portfolio

Keep `README.md` concise and public-facing. Put deeper product and technical
context under `docs/`.

Clearly label features as implemented, planned, reserved, or out of scope.
Do not describe future Airtable, LLM, frontend API, CI, or TikTok capabilities
as currently working.

## Testing and Verification

After making changes, run the smallest meaningful verification.

For backend or cross-cutting changes, run:

```bash
python3 -m unittest discover -v
python3 -m src.backend.pipeline --mode export_only --input examples/sample_recent_posts.csv --limit 10
```

Also inspect or parse the generated files when their schema or formatting
changes.

For documentation-only changes, check links, commands, file names, and claims
against the current repository.

Do not call external APIs as part of the default test suite.

## Change Checklist

Before declaring a change complete:

- confirm no secrets or private data were introduced
- confirm generated/private paths remain ignored
- run the relevant offline test or sample command
- inspect `git status` and avoid unrelated changes
- update affected documentation
- state what was verified and what remains unverified
- do not commit unless the user explicitly asks for a commit

## Current MVP Scope

In scope:

- sample CSV ingestion
- canonical record validation and normalisation
- metric calculation
- rule-based performance signals
- format and topic comparisons
- LLM-ready Markdown metrics summary
- deterministic JSON content plan and reviewable text drafts
- provider interfaces
- documentation
- offline tests
- static frontend placeholder

Out of scope:

- real Airtable integration
- Apify or scraping integration
- real OpenAI or DeepSeek calls
- image or video generation
- TikTok authentication, draft upload, or publishing
- production API or database
- automated scheduled analysis
- automated GitHub Actions scheduling

Future work must preserve the offline sample path even after optional external
integrations are added.
