"""Output writers for metrics summaries and content plans."""

from __future__ import annotations

import json
from datetime import datetime, timezone
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


def _text(value: str | None) -> str:
    if value is None:
        return "Unavailable"
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
    posts: list[dict[str, Any]], summary: dict[str, Any], source: str | Path
) -> str:
    """Render a compact, LLM-ready Markdown performance brief."""
    source_label = source.as_posix() if isinstance(source, Path) else source
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
        f"- Source: `{source_label}`",
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
    if summary["topic_performance"]:
        lines.extend(_group_table(summary["topic_performance"], "Topic"))
    else:
        lines.append(
            "- Topic-level analysis is unavailable because no topic metadata was provided."
        )
    if summary["topic_coverage_count"] < summary["post_count"]:
        lines.append(
            "- Topic-level analysis is limited: "
            f"{summary['topic_coverage_count']} of {summary['post_count']} posts "
            "include topic metadata."
        )
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


def build_script_markdown(plan: dict[str, Any]) -> str:
    """Render the selected content item as a human-reviewable script."""
    item = plan["content_item"]
    script = item["script"]
    provider = plan["provider"]
    generation_note = (
        "deterministic manual rules"
        if provider == "manual"
        else f"the opt-in {provider} strategy provider"
    )
    lines = [
        f"# {item['working_title']}",
        "",
        f"> Draft generated by {generation_note}. Human review is required before publishing.",
        "",
        f"- Format: {item['format']}",
        f"- Topic: {_text(item['topic'])}",
        f"- Evidence source: `{item['source_post_id']}`",
        "",
        "## Hook",
        "",
        script["hook"],
        "",
        "## Body",
        "",
    ]
    lines.extend(
        f"{index}. {line}" for index, line in enumerate(script["body"], start=1)
    )
    lines.extend(
        [
            "",
            "## Call to action",
            "",
            script["cta"],
            "",
            "## Review checks",
            "",
        ]
    )
    lines.extend(f"- [ ] {check}" for check in item["review_checks"])
    lines.append("")
    return "\n".join(lines)


def build_caption_text(plan: dict[str, Any]) -> str:
    """Return the selected caption with a trailing newline."""
    return plan["content_item"]["caption"].strip() + "\n"


def build_hashtags_text(plan: dict[str, Any]) -> str:
    """Return deterministic hashtags on one copy-ready line."""
    return " ".join(plan["content_item"]["hashtags"]) + "\n"


def build_dashboard_data(
    posts: list[dict[str, Any]],
    summary: dict[str, Any],
    plan: dict[str, Any],
    source: str | Path,
    metrics_path: Path,
    metrics_content: str,
) -> dict[str, Any]:
    """Build the safe, presentation-only payload consumed by the dashboard."""
    source_label = source.as_posix() if isinstance(source, Path) else source
    item = plan["content_item"]

    def safe_post_summary(post: dict[str, Any]) -> dict[str, Any]:
        return {
            "post_id": post["post_id"],
            "format": post["format"],
            "topic": post["topic"],
            "hook": post["hook"],
            "views": post["views"],
            "engagement_rate": post["engagement_rate"],
            "average_watch_ratio": post["average_watch_ratio"],
            "region_match_score": post["region_match_score"],
            "signals": post["signals"],
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source_label,
        "provider": plan["provider"],
        "dataset_overview": {
            "post_count": summary["post_count"],
            "total_views": summary["total_views"],
            "average_views": summary["average_views"],
            "average_engagement_rate": summary["average_engagement_rate"],
            "average_watch_ratio": summary["average_watch_ratio"],
            "top_post": safe_post_summary(summary["top_post"]),
        },
        "posts": [safe_post_summary(post) for post in posts],
        "signals": {
            "repeat_post_ids": plan["analysis_basis"][
                "repeat_candidate_post_ids"
            ],
            "pause_post_ids": plan["analysis_basis"]["pause_candidate_post_ids"],
            "weak_retention_post_ids": plan["analysis_basis"][
                "weak_retention_post_ids"
            ],
        },
        "metrics_summary": {
            "path": metrics_path.as_posix(),
            "content": metrics_content,
        },
        "content_plan_path": metrics_path.with_name("content_plan.json").as_posix(),
        "content_plan": plan,
        "script": item["script"],
        "caption": item["caption"],
        "hashtags": item["hashtags"],
        "human_review_note": item.get("review_checks", []),
    }


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
