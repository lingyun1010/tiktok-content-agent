"""Command-line pipeline for offline TikTok content analysis."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .csv_source import load_posts as load_csv_posts
from .exporters import (
    build_caption_text,
    build_hashtags_text,
    build_metrics_markdown,
    build_script_markdown,
    write_json,
    write_text,
)
from .ingest.airtable import AirtableError, load_posts as load_airtable_posts
from .llm_strategy import configured_provider_name
from .metrics import calculate_metrics, summarise_metrics
from .normalise import normalise_posts
from .strategy_agent import get_strategy_provider


def build_parser() -> argparse.ArgumentParser:
    """Build the public CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Analyse TikTok post data and export an offline content strategy."
    )
    parser.add_argument(
        "--mode",
        choices=("export_only",),
        default="export_only",
        help="Pipeline mode. The MVP supports export_only.",
    )
    parser.add_argument(
        "--source",
        choices=("csv", "airtable"),
        default="csv",
        help="Input source. CSV remains the default.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Input CSV path. Required when --source csv is selected.",
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of posts to analyse."
    )
    parser.add_argument(
        "--provider",
        choices=("manual", "openai", "claude"),
        default=None,
        help="Strategy provider. Defaults to MODEL_PROVIDER or manual.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/demo"),
        help="Directory for generated Markdown and JSON files.",
    )
    return parser


def run_pipeline(
    input_path: Path | None,
    limit: int,
    provider_name: str,
    output_dir: Path,
    source: str = "csv",
) -> tuple[Path, Path, Path, Path, Path]:
    """Run ingestion, deterministic metrics, and selected strategy generation."""
    if source == "csv":
        if input_path is None:
            raise ValueError("--input is required when --source csv is selected")
        raw_posts = load_csv_posts(input_path, limit)
        source_label: str | Path = input_path
        empty_message = "Input CSV contains no data rows"
    elif source == "airtable":
        raw_posts = load_airtable_posts(limit)
        source_label = "airtable"
        empty_message = "Configured Airtable view contains no records"
    else:
        raise ValueError(f"Unsupported source: {source}")

    if not raw_posts:
        raise ValueError(empty_message)

    posts = calculate_metrics(normalise_posts(raw_posts))
    summary = summarise_metrics(posts)
    provider = get_strategy_provider(provider_name)
    content_plan = provider.generate_plan(posts, summary)

    metrics_path = output_dir / "metrics_summary.md"
    plan_path = output_dir / "content_plan.json"
    script_path = output_dir / "script.md"
    caption_path = output_dir / "caption.txt"
    hashtags_path = output_dir / "hashtags.txt"
    write_text(metrics_path, build_metrics_markdown(posts, summary, source_label))
    write_json(plan_path, content_plan)
    write_text(script_path, build_script_markdown(content_plan))
    write_text(caption_path, build_caption_text(content_plan))
    write_text(hashtags_path, build_hashtags_text(content_plan))
    return metrics_path, plan_path, script_path, caption_path, hashtags_path


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output_paths = run_pipeline(
            input_path=args.input,
            limit=args.limit,
            provider_name=args.provider or configured_provider_name(),
            output_dir=args.output_dir,
            source=args.source,
        )
    except (AirtableError, FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    for output_path in output_paths:
        print(f"Generated {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
