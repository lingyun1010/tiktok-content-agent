# Setup Notes

## Local requirements

- Python 3.10+
- A terminal
- No external accounts, keys, or package installation for the MVP

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
outputs/demo/content_plan_stub.json
```

The `outputs/` directory is intentionally ignored because real generated
content may reveal private performance data or brand strategy.

## Environment variables

None are required for the sample run. Future integrations may use:

| Variable | Purpose |
| --- | --- |
| `STRATEGY_PROVIDER` | Select `manual`, `openai`, or `deepseek` |
| `OPENAI_API_KEY` | Future OpenAI provider credential |
| `DEEPSEEK_API_KEY` | Future DeepSeek provider credential |
| `AIRTABLE_TOKEN` | Future Airtable access token |
| `AIRTABLE_BASE_ID` | Future Airtable base identifier |
| `AIRTABLE_TABLE_NAME` | Future source table name |

Use `.env.example` as a template. Never place a real value in that committed
file.

## Frontend preview

Open `src/frontend/index.html` directly in a browser. It is a visual placeholder
and does not yet read pipeline output.

## Troubleshooting

- Run the command from the repository root so Python can resolve `src`.
- Confirm the CSV header uses the documented field names.
- Invalid numeric values produce a clear row-specific error.
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
