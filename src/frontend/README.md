# Frontend dashboard

The Phase 5 dashboard renders one complete backend pipeline result. It does not
calculate metrics or combine committed examples with real Airtable/provider
outputs.

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

2. Start a local static server from the repository root:

```bash
python3 -m http.server 8000
```

3. Open:

```text
http://localhost:8000/src/frontend/
```

4. Refresh the browser after each pipeline run.

Use a local server rather than opening `index.html` with `file://`; browser
security commonly blocks local JSON fetches.

## Missing output

If `outputs/latest/dashboard_data.json` is missing or invalid, the page hides
the dashboard and displays the commands needed to generate it. It does not
silently show sample data.

## Privacy

The JSON file may contain real normalised Airtable metrics and private draft
strategy. It excludes raw API responses, credentials, request headers, URLs,
captions from source posts, notes, and private debug data. `outputs/` remains
ignored by Git.
