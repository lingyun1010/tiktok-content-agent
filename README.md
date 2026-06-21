# TikTok Content Agent

An offline-first, AI-ready TikTok content strategy pipeline for small
direct-to-consumer (DTC) brands.

It turns recent post performance data into transparent metrics, a readable
summary, and a reviewable content plan. CSV and the manual strategy provider
remain fully offline; Airtable, OpenAI, and Claude integrations are opt-in.

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
- supports opt-in `openai` and `claude` strategy providers with validated JSON
- includes a static frontend concept
- includes an intentionally non-operational TikTok upload placeholder
- keeps CSV plus the manual provider as the default offline path

It does not upload to TikTok or provide image-generation, video-generation, or
automatic publishing features.

## How to use

Requirements:

- Python 3.10 or newer
- a virtual environment is recommended
- dependencies installed from `requirements.txt`

From the repository root, create and activate a virtual environment, then
install the dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

### 1. CSV with the manual provider

This is the default offline demo. It requires no API keys and makes no network
requests:

```bash
python3 -m src.backend.pipeline \
  --mode export_only \
  --source csv \
  --input examples/sample_recent_posts.csv \
  --limit 10 \
  --provider manual
```

### 2. Airtable with the manual provider

Copy `.env.example` to `.env` and configure:

```dotenv
AIRTABLE_API_KEY=replace_with_your_airtable_key
AIRTABLE_BASE_ID=replace_with_your_base_id
AIRTABLE_TABLE_ID=replace_with_your_table_id
AIRTABLE_VIEW_ID=replace_with_your_view_id
```

Then run:

```bash
python3 -m src.backend.pipeline \
  --mode export_only \
  --source airtable \
  --limit 10 \
  --provider manual
```

### 3. CSV with OpenAI

Add `OPENAI_API_KEY` and optionally `OPENAI_MODEL` to the ignored local `.env`:

```dotenv
OPENAI_API_KEY=replace_with_your_key
OPENAI_MODEL=gpt-4.1-mini
```

Then run:

```bash
python3 -m src.backend.pipeline \
  --mode export_only \
  --source csv \
  --input examples/sample_recent_posts.csv \
  --limit 10 \
  --provider openai
```

### 4. Airtable with OpenAI

Configure both the four `AIRTABLE_*` variables and `OPENAI_API_KEY`, then run:

```bash
python3 -m src.backend.pipeline \
  --mode export_only \
  --source airtable \
  --limit 10 \
  --provider openai
```

### 5. CSV or Airtable with Claude

Add `CLAUDE_API_KEY` and optionally `CLAUDE_MODEL` to `.env`:

```dotenv
CLAUDE_API_KEY=replace_with_your_key
CLAUDE_MODEL=claude-sonnet-4-5
```

Use `--provider claude` with either source:

```bash
python3 -m src.backend.pipeline \
  --mode export_only \
  --source airtable \
  --limit 10 \
  --provider claude
```

For CSV, change `--source airtable` to `--source csv` and add:

```bash
--input examples/sample_recent_posts.csv
```

Never commit `.env` or paste real keys into source files, documentation, logs,
or issues.

### Available options

| Option | Values or default | Purpose |
| --- | --- | --- |
| `--mode` | `export_only` | Generates local strategy files without publishing |
| `--source` | `csv` or `airtable`; default `csv` | Selects the analytics source |
| `--input` | CSV file path | Required only when `--source csv` is used |
| `--limit` | Integer; default `10` | Maximum number of posts to analyse |
| `--provider` | `manual`, `openai`, or `claude`; default `manual` | Selects the strategy provider |
| `--output-dir` | Default `outputs/demo` | Changes the generated-output directory |

`MODEL_PROVIDER` may set the default provider when `--provider` is omitted.
An explicit `--provider` option takes precedence.

View the built-in command help with:

```bash
python3 -m src.backend.pipeline --help
```

### Generated files

Every successful run creates:

```text
outputs/demo/metrics_summary.md
outputs/demo/content_plan.json
outputs/demo/script.md
outputs/demo/caption.txt
outputs/demo/hashtags.txt
```

Generated outputs are deliberately ignored by Git because real runs may contain
private analytics or brand strategy.

The Airtable, OpenAI, and Claude integrations are opt-in and make network
requests. Credentials and private source identifiers are not written to the
generated reports. All strategy output remains a draft for human review.

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
  Markdown          manual / OpenAI / Claude
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
[`docs/content-plan-schema.md`](docs/content-plan-schema.md). The `openai` and
`claude` providers are explicitly selected, send only a compact metrics and
signal payload, validate returned JSON, and require human review. Configuration
and commands are documented in [`docs/setup-notes.md`](docs/setup-notes.md).

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
- Provider calls are explicitly selected and do not log secrets.
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
2. Expose results through a small backend API.
3. Connect the dashboard to generated data.
4. Add GitHub Actions for offline tests, JSON validation, and secret scanning.
5. Design a separate, human-reviewed TikTok draft workflow.

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
