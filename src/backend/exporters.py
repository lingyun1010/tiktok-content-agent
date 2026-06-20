"""Output writers for metrics summaries and content plans."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SIGNAL_GUIDANCE = {
    "high_view_low_engagement": (
        "Keep the distribution lesson, but test a clearer value proposition or CTA."
    ),
    "low_view_high_save": (
        "Retest the useful premise with a stronger opening and packaging."
    ),
    "good_hook_weak_retention": (
        "Keep the hook idea and tighten the middle or shorten the edit."
    ),
    "wrong_region_distribution": (
        "Review language, references, posting time, and audience targeting cues."
    ),
    "repeat_candidate": (
        "Create a controlled follow-up that preserves the premise and changes one variable."
    ),
    "pause_candidate": (
        "Pause direct repetition until the hook, retention, or regional fit is revised."
    ),
}


def _percentage(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.2f}%"


def _text(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _post_table(posts: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Post | Format | Topic | Hook | Views | Engagement | Watch | Signals |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for post in posts:
        lines.append(
            "| {post_id} | {format} | {topic} | {hook} | {views:,} | "
            "{engagement} | {watch} | {signals} |".format(
                post_id=_text(post["post_id"]),
                format=_text(post["format"]),
                topic=_text(post["topic"]),
                hook=_text(post["hook"]),
                views=post["views"],
                engagement=_percentage(post["engagement_rate"]),
                watch=_percentage(post["average_watch_ratio"]),
                signals=", ".join(post["signals"]) or "none",
            )
        )
    return lines


def _metric_appendix_table(posts: list[dict[str, Any]]) -> list[str]:
    lines = [
        (
            "| Post | Views | Like | Comment | Share | Save | Engagement | "
            "Watch | Region | Signals |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for post in posts:
        lines.append(
            "| {post_id} | {views:,} | {likes} | {comments} | {shares} | "
            "{saves} | {engagement} | {watch} | {region} | {signals} |".format(
                post_id=_text(post["post_id"]),
                views=post["views"],
                likes=_percentage(post["like_rate"]),
                comments=_percentage(post["comment_rate"]),
                shares=_percentage(post["share_rate"]),
                saves=_percentage(post["save_rate"]),
                engagement=_percentage(post["engagement_rate"]),
                watch=_percentage(post["average_watch_ratio"]),
                region=_percentage(post["region_match_score"]),
                signals=", ".join(post["signals"]) or "none",
            )
        )
    return lines


def _group_table(groups: list[dict[str, Any]], label: str) -> list[str]:
    lines = [
        f"| {label} | Posts | Avg views | Avg engagement | Avg watch | Repeat candidates |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group in groups:
        lines.append(
            "| {name} | {count} | {views:,.0f} | {engagement} | {watch} | "
            "{repeat} |".format(
                name=_text(group["name"]),
                count=group["post_count"],
                views=group["average_views"],
                engagement=_percentage(group["average_engagement_rate"]),
                watch=_percentage(group["average_watch_ratio"]),
                repeat=group["repeat_candidates"],
            )
        )
    return lines


def build_metrics_markdown(
    posts: list[dict[str, Any]], summary: dict[str, Any], source_path: Path
) -> str:
    """Render a compact, LLM-ready Markdown performance brief."""
    lines = [
        "# TikTok Metrics Summary",
        "",
        (
            "> Deterministic offline analysis. Observations describe this dataset; "
            "recommendations are test hypotheses, not causal findings."
        ),
        "",
        "## Dataset overview",
        "",
        f"- Source: `{source_path.as_posix()}`",
        f"- Posts analysed: {summary['post_count']}",
        f"- Total views: {summary['total_views']:,}",
        f"- Average views per post: {summary['average_views']:,.0f}",
        (
            "- Average engagement rate: "
            f"{_percentage(summary['average_engagement_rate'])}"
        ),
        f"- Average watch ratio: {_percentage(summary['average_watch_ratio'])}",
        (
            "- Posts with comparable region fields: "
            f"{summary['region_coverage_count']} of {summary['post_count']}"
        ),
        "",
        "## Top performing posts",
        "",
    ]
    lines.extend(_post_table(summary["top_posts"]))
    lines.extend(["", "## Weak performing posts", ""])
    lines.extend(_post_table(summary["weak_posts"]))
    lines.extend(["", "## Format performance", ""])
    lines.extend(_group_table(summary["format_performance"], "Format"))
    lines.extend(["", "## Topic performance", ""])
    lines.extend(_group_table(summary["topic_performance"], "Topic"))
    lines.extend(["", "## Audience region notes", ""])

    if summary["region_coverage_count"] == 0:
        lines.append(
            "- Region fields were not available, so no region match score was calculated."
        )
    else:
        lines.extend(
            [
                (
                    "- Average region match score: "
                    f"{_percentage(summary['average_region_match_score'])}"
                ),
                (
                    "- `region_match_score` uses the top-region view share when the "
                    "top and target regions match; otherwise it uses the remaining share "
                    "as a conservative proxy."
                ),
            ]
        )
        wrong_region_posts = summary["signal_posts"].get(
            "wrong_region_distribution", []
        )
        if wrong_region_posts:
            lines.append(
                "- Wrong-region distribution flagged: "
                + ", ".join(f"`{post_id}`" for post_id in wrong_region_posts)
                + "."
            )
        else:
            lines.append("- No post fell below the 50% region-match threshold.")

    lines.extend(["", "## Recommended signals for next content", ""])
    if summary["signal_counts"]:
        for signal, guidance in SIGNAL_GUIDANCE.items():
            count = summary["signal_counts"].get(signal, 0)
            if count:
                post_ids = summary["signal_posts"][signal]
                lines.append(
                    f"- `{signal}` ({count}): {guidance} "
                    f"Posts: {', '.join(f'`{post_id}`' for post_id in post_ids)}."
                )
    else:
        lines.append("- No rule-based signals were triggered.")

    lines.extend(
        [
            "",
            "### Signal rules used",
            "",
            "- High/low views, likes, saves, engagement, and repeat thresholds use dataset averages.",
            "- Weak retention means `average_watch_ratio < 50%`.",
            "- Wrong-region distribution means `region_match_score < 50%`.",
            (
                "- A repeat candidate has at-or-above-average engagement, supported "
                "retention, and no wrong-region flag."
            ),
            (
                "- A pause candidate has below-average engagement plus weak retention "
                "or a wrong-region flag."
            ),
            "",
            "## Per-post metric appendix",
            "",
        ]
    )
    lines.extend(_metric_appendix_table(posts))
    lines.append("")
    return "\n".join(lines)


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text, creating parent directories when needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write formatted JSON, creating parent directories when needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
