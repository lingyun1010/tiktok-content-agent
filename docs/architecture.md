# Architecture

## System boundaries

The project is split into a Python backend, a minimal FastAPI server, and a
small static frontend.

- **Backend:** ingestion, normalisation, metrics, summaries, and strategy
  provider selection.
- **FastAPI server:** local dashboard-data API and analyst-chat API grounded in
  the latest generated dashboard JSON.
- **Frontend:** static presentation of reviewed public sample metrics,
  recommendations, scripts, captions, hashtags, human-review checks, and
  analyst-chat answers.

The pipeline still communicates its latest run through generated files. The
FastAPI layer reads `outputs/latest/dashboard_data.json` and exposes it to the
frontend through a small local API.

## Data flow

```text
examples/sample_recent_posts.csv
               |
               v
        csv_source.load_posts
               |
               v
       normalise.normalise_post
               |
               v
       canonical TikTok record
               |
               v
    metrics + rule-based signals
               |
        +------+-------+
        |              |
        v              v
Markdown exporter  strategy_agent
                       |
                       v
          manual / OpenAI / Claude
        |              |
        +------+-------+
               v
 metrics summary, plan, script,
    caption, and hashtags
               |
               v
 outputs/latest/dashboard_data.json
               |
               v
        FastAPI server
        /api/dashboard-data
        /api/analyst-chat
               |
               v
        Static dashboard
```

## Backend modules

- `pipeline.py`: command-line orchestration and output paths.
- `schema.py`: canonical field definitions shared by current and future sources.
- `csv_source.py`: local CSV ingestion and required-header validation.
- `normalise.py`: conversion from string records to a typed internal shape.
- `metrics.py`: per-post calculations, signals, rankings, and grouped summaries.
- `exporters.py`: metrics, plan, script, caption, and hashtag rendering/writing.
- `strategy_agent.py`: provider selection and deterministic manual rules.
- `llm_strategy.py`: compact LLM inputs, OpenAI/Claude adapters, and validation.
- `analyst.py`: dashboard-grounded analyst chat providers and response validation.
- `server.py`: minimal FastAPI app for dashboard data, analyst chat, and static
  frontend serving.
- `tiktok_uploader.py`: explicit non-operational placeholder.

## Provider adapters

The `StrategyAgent` interface supports three provider names:

- `manual`: implemented; converts metrics and signals into a deterministic,
  human-reviewable plan and text drafts.
- `openai`: opt-in; calls the OpenAI Responses API when configured.
- `claude`: opt-in; calls the Anthropic Messages API when configured.

LLM providers receive compact structured metrics and signals rather than raw
records, credentials, or arbitrary files. Prompt templates live under
`prompts/` so they can be reviewed and versioned independently.

The analyst chat supports the same provider names:

- `manual`: deterministic, offline answers over the dashboard JSON.
- `openai`: opt-in; calls OpenAI from the server only.
- `claude`: opt-in; calls Claude from the server only.

Analyst LLM providers receive only a compact context derived from
`outputs/latest/dashboard_data.json`. They must return valid JSON with
`summary`, `evidence`, `recommendation`, `suggested_next_action`, and
`limitations`; the backend adds `provider` and `llm_called`.

## Analytics boundary

Metrics are calculated from canonical records only. Source adapters must not
leak source-specific names into the analytics layer. Dataset averages drive the
relative performance signals; fixed 50% thresholds define weak retention and
wrong-region distribution.

The region match score uses only the top observed region and its view share.
It is explicitly a proxy until a future authorised source provides a complete
regional distribution.

## Strategy and export boundary

All providers receive enriched posts plus the Phase 1 summary. The manual
provider applies deterministic rules. LLM adapters reduce those inputs to a
compact metrics-and-signals payload and validate the returned draft. Python
retains ownership of evidence IDs and analysis metadata. Every provider returns
the versioned schema documented in
[`content-plan-schema.md`](content-plan-schema.md).

`pipeline.py` writes `content_plan.json`, then renders `script.md`,
`caption.txt` and `hashtags.txt`. It also writes the frontend contract at
`outputs/latest/dashboard_data.json` from the same normalised posts, metric
summary, and validated plan. The pipeline does not upload, schedule, or publish
any output.

The frontend contains no backend metric or strategy logic. In Phase 6B it is
served by `src.backend.server`, fetches the latest dashboard JSON through
`GET /api/dashboard-data`, and sends analyst questions to
`POST /api/analyst-chat`. It does not combine sample and generated data.
Missing or invalid output produces an explicit empty state.

The dashboard payload includes safe normalised post summaries but excludes raw
Airtable responses, source captions, post URLs, notes, credentials, request
headers, and provider debug data.

The analyst safe context preserves this boundary. It excludes raw Airtable
responses, post URLs, source captions, notes, credentials, request headers, and
secrets before any OpenAI or Claude analyst call.

## Security model

- Secrets are loaded only from local environment variables or ignored local
  `.env` files.
- `.env` and local output/data directories are ignored.
- Example data is synthetic.
- The offline path is the default and requires no network access.
- Provider calls must be opt-in and must never log tokens.
- Browser code never receives provider API keys and never calls OpenAI or
  Claude directly.
- TikTok upload is outside the current trust boundary and is not implemented.
- Before any future publishing feature, require explicit user review,
  authentication, consent, and auditable actions.

## Future deployment shape

A modest next architecture would add authentication, a persistent database,
background jobs for authorised provider calls, and a versioned public API.
Those components remain intentionally excluded from the current MVP.
