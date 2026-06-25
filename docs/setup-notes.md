# Setup Notes

## Local requirements

- Python 3.10+
- A terminal
- Install dependencies with `python3 -m pip install -r requirements.txt`
- No external accounts or keys for the default CSV path

## Run the sample pipeline

From the repository root:

```bash
python -m src.backend.pipeline --mode export_only --input examples/sample_recent_posts.csv --limit 10
```

On systems where Python is installed as `python3` rather than `python`, replace
only the executable name; all other arguments stay the same.

The command creates:

```text
outputs/demo/metrics_summary.md
outputs/demo/content_plan.json
outputs/demo/script.md
outputs/demo/caption.txt
outputs/demo/hashtags.txt
outputs/latest/dashboard_data.json
```

The `outputs/` directory is intentionally ignored because real generated
content may reveal private performance data or brand strategy.

The input must use the canonical columns documented in
[`canonical-schema.md`](canonical-schema.md). The committed sample contains
only fictional records.

The manual strategy output follows
[`content-plan-schema.md`](content-plan-schema.md). All generated text is a
draft and requires human review before publishing.

## Optional LLM strategy providers

Manual remains the default and makes no network calls. Select an LLM provider
explicitly after configuring its key:

```bash
python3 -m src.backend.pipeline --mode export_only --source csv \
  --input examples/sample_recent_posts.csv --limit 10 --provider openai

python3 -m src.backend.pipeline --mode export_only --source csv \
  --input examples/sample_recent_posts.csv --limit 10 --provider claude
```

OpenAI and Claude receive a compact aggregate summary, canonical post signals,
the required content-plan shape, and public brand guidance. Raw records,
captions, URLs, timestamps, notes, credentials, and private source files are
not sent. Provider JSON is validated before any plan or draft files are
written. Invalid JSON, missing fields, wrong types, or invented evidence post
IDs stop the run with a clear error.

The default tests mock both HTTP boundaries. Do not run live-provider commands
unless the corresponding key is configured and the API call is intentional.

## Optional Airtable source

The Airtable adapter uses the standard library and is selected explicitly:

```bash
python3 -m src.backend.pipeline --source airtable --limit 10
```

The configured table and view must expose fields using the exact, case-sensitive
canonical names in [`canonical-schema.md`](canonical-schema.md). In particular,
`duration_seconds` is a required Airtable field and every retrieved record must
contain a number greater than zero. The adapter retrieves only enough pages to
satisfy `--limit`. Tests mock the HTTP boundary and do not call Airtable.
`topic` and `hook` may be absent; the pipeline does not infer them.

## Environment variables

None are required for the sample CSV run with `--provider manual`. Provider and
Airtable variables are required only when their integrations are selected:

| Variable | Purpose |
| --- | --- |
| `MODEL_PROVIDER` | Optional default: `manual`, `openai`, or `claude` |
| `OPENAI_API_KEY` | Required only for `--provider openai` |
| `OPENAI_MODEL` | Optional OpenAI model override |
| `CLAUDE_API_KEY` | Required only for `--provider claude` |
| `CLAUDE_MODEL` | Optional Claude model override |
| `AIRTABLE_API_KEY` | Airtable credential sent only in the authorization header |
| `AIRTABLE_BASE_ID` | Airtable base identifier |
| `AIRTABLE_TABLE_ID` | Airtable table ID beginning with `tbl` |
| `AIRTABLE_VIEW_ID` | Airtable view ID beginning with `viw` |

Copy `.env.example` to `.env` for local development, replace only the required
placeholder values, and run commands from the repository root. The pipeline
loads the local `.env` without overriding variables already exported by the
shell. `.env` is ignored by Git; keep `.env.example` limited to placeholders.

## Frontend and analyst server

After running the pipeline, start the FastAPI server from the repository root:

```bash
python3 -m src.backend.server
```

Open `http://127.0.0.1:8000/`. The server exposes:

```text
GET /api/health
GET /api/dashboard-data
POST /api/analyst-chat
```

The dashboard reads the ignored `outputs/latest/dashboard_data.json` through
`GET /api/dashboard-data`. The analyst chat posts questions to
`POST /api/analyst-chat`; manual mode is deterministic and offline, while
OpenAI and Claude are opt-in and use server-side environment variables only.
If the latest JSON is missing or invalid, the page shows generation
instructions and no sample metrics. Reload the page after each pipeline run.

See `src/frontend/README.md` for the exact preview and sample-refresh workflow.

## Troubleshooting

- Run the command from the repository root so Python can resolve `src`.
- CSV is the default source and requires `--input`.
- OpenAI requires `OPENAI_API_KEY`; Claude requires `CLAUDE_API_KEY`.
- Analyst chat requires the FastAPI server for `/api/analyst-chat`; the browser
  does not call OpenAI or Claude directly.
- Provider errors never include configured key values.
- Invalid provider JSON is rejected before strategy files are exported.
- Airtable requires all four `AIRTABLE_*` variables and omits `--input`.
- Rename older local variables from `AIRTABLE_TABLE_NAME` and
  `AIRTABLE_VIEW_NAME` to `AIRTABLE_TABLE_ID` and `AIRTABLE_VIEW_ID`.
- Confirm the CSV header uses the documented field names.
- Invalid numeric values produce a clear row-specific error.
- Count fields must be whole numbers and percentage fields must be from 0 to 1.
- `published_at` must be an ISO 8601 datetime and duration must be greater than zero.
- Duplicate post IDs are rejected.
- A zero-view post is accepted and receives zero-valued rate metrics.

## Future GitHub Actions plan

A future workflow should:

1. Run on pushes and pull requests.
2. Set up a supported Python version.
3. Run unit tests and the offline sample command.
4. Validate that generated JSON parses.
5. Check formatting and linting if those tools are added.
6. Scan for accidentally committed secrets.

The workflow must not call paid APIs or depend on repository secrets for basic
validation.
