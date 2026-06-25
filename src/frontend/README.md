# Frontend dashboard

The dashboard renders one complete backend pipeline result and includes the
Phase 6B analyst chat panel. It does not calculate metrics or combine committed
examples with real Airtable/provider outputs.

## Workflow

1. Run the backend pipeline from the repository root.

CSV and manual provider:

```bash
python3 -m src.backend.pipeline \
  --mode export_only \
  --source csv \
  --input examples/sample_recent_posts.csv \
  --limit 10 \
  --provider manual
```

Airtable and manual provider:

```bash
python3 -m src.backend.pipeline \
  --mode export_only \
  --source airtable \
  --limit 10 \
  --provider manual
```

The run writes the dashboard contract to:

```text
outputs/latest/dashboard_data.json
```

2. Start the FastAPI server from the repository root:

```bash
python3 -m src.backend.server
```

3. Open:

```text
http://127.0.0.1:8000/
```

4. Refresh the browser after each pipeline run.

## Analyst chat

The chat panel posts questions to:

```text
POST /api/analyst-chat
```

The server loads `outputs/latest/dashboard_data.json`, compacts it into a safe
context, and returns structured answers with summary, evidence, recommendation,
suggested next action, limitations, provider, and LLM-call status.

Supported analyst providers:

- `manual`: deterministic, offline, no API keys
- `openai`: opt-in, server-side `OPENAI_API_KEY`
- `claude`: opt-in, server-side `CLAUDE_API_KEY`

The browser never receives provider credentials and never calls OpenAI or
Claude directly.

## Missing output

If `outputs/latest/dashboard_data.json` is missing or invalid, the page hides
the dashboard and displays the commands needed to generate it. It does not
silently show sample data.

## Privacy

The JSON file may contain real normalised Airtable metrics and private draft
strategy. It excludes raw API responses, credentials, request headers, URLs,
captions from source posts, notes, and private debug data. `outputs/` remains
ignored by Git.
