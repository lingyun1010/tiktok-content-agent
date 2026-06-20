# TikTok Content Agent

An offline-first, AI-ready TikTok content strategy pipeline for small
direct-to-consumer (DTC) brands.

It turns recent post performance data into transparent metrics, a readable
summary, and a deterministic manual content plan. CSV remains fully offline;
optional Airtable ingestion is explicitly selected and environment-configured.

## Why this project exists

Small brands often publish on TikTok without a consistent feedback loop. They
can see views, likes, comments, shares, saves, duration, and watch time, but
those numbers do not automatically reveal what to test next.

This project explores a repeatable workflow between platform data, structured
analysis, optional AI-assisted strategy, and human creative judgement.

## Current status

The offline MVP is working.

It currently:

- reads synthetic recent-post data from CSV
- optionally reads authorised Airtable records using canonical field names
- validates and normalises a documented canonical TikTok post schema
- calculates like, comment, share, save, engagement, watch, and optional region metrics
- compares performance by format and topic
- assigns six deterministic, explainable performance signals
- exports `outputs/demo/metrics_summary.md`
- exports a versioned `outputs/demo/content_plan.json`
- exports reviewable `script.md`, `caption.txt`, and `hashtags.txt` drafts
- generates strategy through deterministic rules in the `manual` provider
- reserves provider boundaries for future `openai` and `deepseek` adapters
- includes a static frontend concept
- includes an intentionally non-operational TikTok upload placeholder
- keeps CSV as the default source with no network access or external APIs

It does not currently connect to Apify, TikTok, OpenAI, DeepSeek,
image-generation, or video-generation services.

## Quick start

Requirements:

- Python 3.10 or newer
- no third-party Python packages

From the repository root:

```bash
python -m src.backend.pipeline --mode export_only --input examples/sample_recent_posts.csv --limit 10
```

If Python is exposed as `python3` on your system:

```bash
python3 -m src.backend.pipeline --mode export_only --input examples/sample_recent_posts.csv --limit 10
```

Expected generated files:

```text
outputs/demo/metrics_summary.md
outputs/demo/content_plan.json
outputs/demo/script.md
outputs/demo/caption.txt
outputs/demo/hashtags.txt
```

Generated outputs are deliberately ignored by Git because real runs may contain
private analytics or brand strategy.

To use Airtable, set the four variables documented in `.env.example`, ensure
the selected view exposes the canonical field names, then run:

```bash
python3 -m src.backend.pipeline --source airtable --limit 10
```

The Airtable source is opt-in and makes a network request. Credentials, base
identifiers, table names, and view names are not written to generated reports.

## Example analysis

The synthetic dataset contains 10 fictional posts across formats and topics
such as education, product demonstrations, founder stories, lifestyle, and
behind-the-scenes content.

The generated Markdown report includes:

- posts analysed and total views
- average engagement rate
- average watch ratio
- top and weak post comparisons
- format and topic performance
- audience-region notes
- deterministic signals and next-test guidance
- a per-post metric appendix

The JSON file records the metrics and signals behind repeat, pause, and
retention decisions. The text files are rendered from the selected content
item, and every output requires human review before publishing.

## How it works

```text
CSV (default) or Airtable (opt-in)
              |
              v
       Source ingestion
    |
    v
Record normalisation
    |
    v
Metrics calculation
    |
    +---------------------+
    |                     |
    v                     v
Metrics summary     Strategy provider
  Markdown          rule-based manual
    |                     |
    +----------+----------+
               v
          outputs/demo/
```

The backend owns ingestion, validation, metrics, strategy generation, and
export. The frontend is currently static and will later consume a stable
exported schema or backend API.

## Metrics

The MVP calculates:

```text
like_rate          = likes / views
comment_rate       = comments / views
share_rate         = shares / views
save_rate          = saves / views, when saves are available
engagement_rate    = (likes + comments + shares + available saves) / views
average_watch_ratio = average watch time / duration
region_match_score  = top-region share when target matches, otherwise its remainder
```

Zero-view records receive zero-valued rate metrics. Missing optional values are
kept missing rather than invented.

These metrics are descriptive, not causal. They support creative testing but do
not guarantee future performance.

The canonical fields, validation rules, region-score limitation, and signal
thresholds are documented in
[`docs/canonical-schema.md`](docs/canonical-schema.md).

## Repository structure

```text
AGENTS.md                 Coding-agent project rules
README.md                 Public project overview
docs/
  current-checkpoint.md    Latest verified state and safe continuation notes
  project-brief.md        Product goal, users, scope, and non-goals
  CONTEXT.md              Business context and operating assumptions
  architecture.md         Data flow, boundaries, and security model
  canonical-schema.md     Input fields, calculated metrics, and signal rules
  setup-notes.md          Local setup and future CI plan
examples/
  sample_recent_posts.csv Synthetic public demo data
prompts/                  Future provider prompt templates
src/backend/              Python pipeline and provider boundaries
src/frontend/             Static dashboard placeholder
tests/                    Offline automated tests
data/raw/                 Ignored private source data
data/processed/           Ignored private transformed data
outputs/                  Ignored generated results
```

## Backend design

The Python backend separates:

- CSV and optional Airtable ingestion
- record normalisation
- metric calculation and aggregation
- Markdown and JSON export
- provider selection and strategy generation
- future publishing boundaries

The current `manual` provider deterministically selects a repeat candidate,
records pause and retention guidance, and drafts one script, caption, and
hashtag set. Its stable output is documented in
[`docs/content-plan-schema.md`](docs/content-plan-schema.md). Selecting
`openai` or `deepseek` produces a clear not-implemented error rather than
making an unexpected network call.

## Frontend

The current frontend is a static HTML/CSS/JavaScript concept under
`src/frontend/`.

It previews a future dashboard for:

- recent post metrics
- performance summaries
- content recommendations
- generated scripts
- captions and hashtags

Open `src/frontend/index.html` directly in a browser to view it. It does not yet
read pipeline outputs.

## Human review

The intended workflow keeps a person in control:

1. Collect recent performance data.
2. Calculate transparent metrics.
3. Generate a summary and recommendation.
4. Review facts, creative direction, tone, visuals, and compliance.
5. Edit or approve any generated assets.
6. Make the final publishing decision.

TikTok authentication, scheduling, and publishing are deliberately outside the
MVP.

## Privacy and security

This is a public portfolio repository.

- All committed example records are fictional.
- `.env`, generated outputs, raw data, processed data, and logs are ignored.
- `.env.example` contains placeholders only.
- Real analytics and generated plans must stay in ignored local directories.
- The sample command uses no credentials and performs no network calls.
- Future provider calls must be explicitly enabled and must not log secrets.
- Any future publishing workflow must require authentication, consent, review,
  and auditable actions.

## Configuration

No environment variables are required for the default CSV path. Optional
Airtable ingestion requires `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`,
`AIRTABLE_TABLE_ID`, and `AIRTABLE_VIEW_ID`. Never commit the local values.

## Tests

Run the offline test suite:

```bash
python3 -m unittest discover -v
```

Then exercise the public CLI:

```bash
python3 -m src.backend.pipeline --mode export_only --input examples/sample_recent_posts.csv --limit 10
```

The default tests must remain independent of paid APIs and repository secrets.

## Roadmap

1. Add further authorised export adapters.
2. Implement opt-in OpenAI and DeepSeek strategy providers.
3. Validate structured provider responses.
4. Expose results through a small backend API.
5. Connect the dashboard to generated data.
6. Add GitHub Actions for offline tests, JSON validation, and secret scanning.
7. Design a separate, human-reviewed TikTok draft workflow.

Private workflow outputs should be stored as protected artifacts or in private
storage—not committed to this repository.

The phased product plan prioritises stronger analytics and deterministic
strategy before external APIs, media generation, or publishing integrations.

See the [full project roadmap](docs/roadmap.md) and its
[roadmap infographic](docs/assets/project-roadmap-infographic.png).


## Portfolio focus

This project demonstrates:

- modular backend pipeline design
- data normalisation and metric calculation
- deterministic offline fallbacks
- LLM-ready summarisation and provider abstraction
- privacy-aware repository architecture
- frontend/backend separation
- human-in-the-loop system design
- staged integration planning without overstating current capabilities

The goal is not simply to automate content creation. It is to build a reliable,
reviewable feedback loop between platform data, AI-assisted reasoning, and
human creative judgement.

See [the project brief](docs/project-brief.md),
[project context](docs/CONTEXT.md), and
[architecture notes](docs/architecture.md) for deeper detail.
