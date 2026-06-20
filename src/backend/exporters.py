"""Output writers for metrics summaries and content plans."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _percentage(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.2f}%"


def build_metrics_markdown(
    posts: list[dict[str, Any]], summary: dict[str, Any], source_path: Path
) -> str:
    """Render metrics as a compact, human-readable Markdown report."""
    lines = [
        "# TikTok Metrics Summary",
        "",
        f"- Source: `{source_path.as_posix()}`",
        f"- Posts analysed: {summary['post_count']}",
        f"- Total views: {summary['total_views']:,}",
        (
            "- Average engagement rate: "
            f"{_percentage(summary['average_engagement_rate'])}"
        ),
        f"- Average watch ratio: {_percentage(summary['average_watch_ratio'])}",
        "",
        "## Post metrics",
        "",
        (
            "| Post | Views | Like rate | Comment rate | Share rate | "
            "Save rate | Engagement rate | Watch ratio |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for post in posts:
        lines.append(
            "| {post_id} | {views:,} | {like_rate} | {comment_rate} | "
            "{share_rate} | {save_rate} | {engagement_rate} | {watch_ratio} |".format(
                post_id=post["post_id"],
                views=post["views"],
                like_rate=_percentage(post["like_rate"]),
                comment_rate=_percentage(post["comment_rate"]),
                share_rate=_percentage(post["share_rate"]),
                save_rate=_percentage(post["save_rate"]),
                engagement_rate=_percentage(post["engagement_rate"]),
                watch_ratio=_percentage(post["average_watch_ratio"]),
            )
        )

    top_post = summary.get("top_post")
    lines.extend(["", "## Strongest engagement signal", ""])
    if top_post:
        lines.extend(
            [
                f"- Post: `{top_post['post_id']}`",
                f"- Engagement rate: {_percentage(top_post['engagement_rate'])}",
                f"- Caption: {top_post['caption']}",
                f"- Content pillar: {top_post['content_pillar'] or 'Not provided'}",
                f"- Hook: {top_post['hook'] or 'Not provided'}",
            ]
        )
    else:
        lines.append("No posts were available for analysis.")

    lines.extend(
        [
            "",
            "## Interpretation note",
            "",
            (
                "These metrics describe this sample only. They do not establish "
                "causation or guarantee future content performance."
            ),
            "",
        ]
    )
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

