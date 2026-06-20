"""Command-line pipeline for offline TikTok content analysis."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .csv_source import load_posts
from .exporters import build_metrics_markdown, write_json, write_text
from .metrics import calculate_metrics, summarise_metrics
from .normalise import normalise_posts
from .strategy_agent import get_strategy_provider


def build_parser() -> argparse.ArgumentParser:
    """Build the public CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Analyse TikTok post data and export an offline strategy stub."
    )
    parser.add_argument(
        "--mode",
        choices=("export_only",),
        default="export_only",
        help="Pipeline mode. The MVP supports export_only.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Input CSV path.")
    parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of posts to analyse."
    )
    parser.add_argument(
        "--provider",
        choices=("manual", "openai", "deepseek"),
        default="manual",
        help="Strategy provider. Only manual is implemented in the MVP.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/demo"),
        help="Directory for generated Markdown and JSON files.",
    )
    return parser


def run_pipeline(
    input_path: Path,
    limit: int,
    provider_name: str,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Run ingestion, metrics, and offline plan generation."""
    raw_posts = load_posts(input_path, limit)
    if not raw_posts:
        raise ValueError("Input CSV contains no data rows")

    posts = calculate_metrics(normalise_posts(raw_posts))
    summary = summarise_metrics(posts)
    provider = get_strategy_provider(provider_name)
    content_plan = provider.generate_plan(posts, summary)

    metrics_path = output_dir / "metrics_summary.md"
    plan_path = output_dir / "content_plan_stub.json"
    write_text(metrics_path, build_metrics_markdown(posts, summary, input_path))
    write_json(plan_path, content_plan)
    return metrics_path, plan_path


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)
    metrics_path, plan_path = run_pipeline(
        input_path=args.input,
        limit=args.limit,
        provider_name=args.provider,
        output_dir=args.output_dir,
    )
    print(f"Generated {metrics_path}")
    print(f"Generated {plan_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

