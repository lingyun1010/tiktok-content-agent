# Architecture

## System boundaries

The project is split into a Python backend and a small static frontend.

- **Backend:** ingestion, normalisation, metrics, summaries, and strategy
  provider selection.
- **Frontend:** future presentation of metrics, recommendations, scripts,
  captions, and hashtags.

The MVP communicates through generated files. A future version may place a
small HTTP API between the two layers.

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
                  manual provider
        |              |
        +------+-------+
               v
          outputs/demo/
```

## Backend modules

- `pipeline.py`: command-line orchestration and output paths.
- `schema.py`: canonical field definitions shared by current and future sources.
- `csv_source.py`: local CSV ingestion and required-header validation.
- `normalise.py`: conversion from string records to a typed internal shape.
- `metrics.py`: per-post calculations, signals, rankings, and grouped summaries.
- `exporters.py`: Markdown and JSON file writing.
- `strategy_agent.py`: provider interface and manual implementation.
- `tiktok_uploader.py`: explicit non-operational placeholder.

## Provider adapters

The `StrategyAgent` interface supports three provider names:

- `manual`: implemented; creates deterministic recommendations from metrics.
- `openai`: reserved; raises a clear not-implemented error.
- `deepseek`: reserved; raises a clear not-implemented error.

Future provider implementations should receive structured metrics rather than
raw credentials or arbitrary files. Prompt templates live under `prompts/` so
they can be reviewed and versioned independently.

## Analytics boundary

Metrics are calculated from canonical records only. Source adapters must not
leak source-specific names into the analytics layer. Dataset averages drive the
relative performance signals; fixed 50% thresholds define weak retention and
wrong-region distribution.

The region match score uses only the top observed region and its view share.
It is explicitly a proxy until a future authorised source provides a complete
regional distribution.

## Security model

- Secrets are loaded only from local environment variables in future
  integrations.
- `.env` and local output/data directories are ignored.
- Example data is synthetic.
- The offline path is the default and requires no network access.
- Provider calls must be opt-in and must never log tokens.
- TikTok upload is outside the current trust boundary and is not implemented.
- Before any future publishing feature, require explicit user review,
  authentication, consent, and auditable actions.

## Future deployment shape

A modest next architecture would add a FastAPI service, a persistent database,
background jobs for authorised provider calls, and a frontend that reads a
versioned API. Those components are intentionally excluded from the MVP.
