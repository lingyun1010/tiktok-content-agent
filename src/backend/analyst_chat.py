"""Deterministic analyst answers from the safe dashboard data contract."""

from __future__ import annotations

from typing import Any


REQUIRED_ANSWER_FIELDS = (
    "summary",
    "evidence",
    "recommendation",
    "suggested_next_action",
)


class AnalystChatError(ValueError):
    """Raised when the dashboard data or analyst question is invalid."""


def _percentage(value: Any) -> str:
    if value is None:
        return "unavailable"
    return f"{float(value) * 100:.2f}%"


def _format_compact(value: Any) -> str:
    number = float(value)
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if abs(number) >= 1_000:
        return f"{number / 1_000:.1f}K"
    return str(int(number))


def _normalise_question(question: str) -> str:
    clean_question = " ".join(question.strip().lower().split())
    if not clean_question:
        raise AnalystChatError("Question is required.")
    return clean_question


def _require_dashboard_data(dashboard_data: dict[str, Any]) -> None:
    required = (
        "dataset_overview",
        "posts",
        "signals",
        "content_plan",
    )
    missing = [field for field in required if field not in dashboard_data]
    if missing:
        raise AnalystChatError(
            "Dashboard data is missing required fields: " + ", ".join(missing)
        )
    if not isinstance(dashboard_data["posts"], list) or not dashboard_data["posts"]:
        raise AnalystChatError("Dashboard data must include at least one post.")


def _top_post(posts: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        posts,
        key=lambda post: (
            post.get("engagement_rate") or 0,
            post.get("average_watch_ratio") or 0,
            post.get("views") or 0,
            post.get("post_id") or "",
        ),
    )


def _weakest_retention_post(posts: list[dict[str, Any]]) -> dict[str, Any] | None:
    with_watch = [
        post for post in posts if post.get("average_watch_ratio") is not None
    ]
    if not with_watch:
        return None
    return min(
        with_watch,
        key=lambda post: (
            post.get("average_watch_ratio") or 0,
            post.get("engagement_rate") or 0,
            post.get("post_id") or "",
        ),
    )


def _answer_top_post(
    posts: list[dict[str, Any]], plan: dict[str, Any]
) -> dict[str, Any]:
    post = _top_post(posts)
    return {
        "summary": (
            f"{post['post_id']} is the strongest evidence point in this run, "
            f"with {_format_compact(post['views'])} views, "
            f"{_percentage(post['engagement_rate'])} engagement, and "
            f"{_percentage(post['average_watch_ratio'])} watch ratio."
        ),
        "evidence": [
            {
                "post_id": post["post_id"],
                "metric": "engagement_rate",
                "value": _percentage(post["engagement_rate"]),
            },
            {
                "post_id": post["post_id"],
                "metric": "signals",
                "value": ", ".join(post.get("signals", [])) or "none",
            },
        ],
        "recommendation": plan["strategy"]["primary_goal"],
        "suggested_next_action": (
            "Use this post as the controlled-test source and change one creative "
            "variable in the next draft."
        ),
    }


def _answer_retention(
    posts: list[dict[str, Any]], plan: dict[str, Any]
) -> dict[str, Any]:
    weakest = _weakest_retention_post(posts)
    retention = plan["strategy"]["retention_adjustment"]
    affected = retention.get("affected_post_ids", [])
    evidence = [
        {
            "post_id": post_id,
            "metric": "retention_flag",
            "value": "weak_retention",
        }
        for post_id in affected
    ]
    if weakest is not None:
        evidence.insert(
            0,
            {
                "post_id": weakest["post_id"],
                "metric": "average_watch_ratio",
                "value": _percentage(weakest["average_watch_ratio"]),
            },
        )
    return {
        "summary": (
            "Retention needs attention in this run."
            if affected
            else "No post is currently flagged for weak retention."
        ),
        "evidence": evidence,
        "recommendation": retention["guidance"],
        "suggested_next_action": (
            "Shorten the next edit, state the value earlier, and compare watch "
            "ratio against this latest run."
        ),
    }


def _answer_pause(plan: dict[str, Any]) -> dict[str, Any]:
    pause_items = plan["strategy"].get("pause", [])
    if not pause_items:
        return {
            "summary": "No direct pause recommendation is present in this run.",
            "evidence": [],
            "recommendation": "Keep testing the strongest supported pattern.",
            "suggested_next_action": (
                "Review repeat candidates first, then rerun the pipeline after the "
                "next batch of posts."
            ),
        }
    first_pause = pause_items[0]
    return {
        "summary": (
            f"{first_pause['post_id']} is the clearest pause candidate in this run."
        ),
        "evidence": [
            {
                "post_id": item["post_id"],
                "metric": "pause_reason",
                "value": item["reason"],
            }
            for item in pause_items
        ],
        "recommendation": first_pause["action"],
        "suggested_next_action": (
            "Revise the hook, pacing, or audience cue before repeating this format."
        ),
    }


def _answer_general(dashboard_data: dict[str, Any]) -> dict[str, Any]:
    summary = dashboard_data["dataset_overview"]
    plan = dashboard_data["content_plan"]
    signals = dashboard_data["signals"]
    top_post = summary["top_post"]
    return {
        "summary": (
            f"This run analysed {summary['post_count']} posts with "
            f"{_format_compact(summary['total_views'])} total views. "
            f"The top post is {top_post['post_id']}."
        ),
        "evidence": [
            {
                "post_id": top_post["post_id"],
                "metric": "top_post_engagement",
                "value": _percentage(top_post["engagement_rate"]),
            },
            {
                "post_id": "repeat_candidates",
                "metric": "post_ids",
                "value": ", ".join(signals.get("repeat_post_ids", [])) or "none",
            },
            {
                "post_id": "pause_candidates",
                "metric": "post_ids",
                "value": ", ".join(signals.get("pause_post_ids", [])) or "none",
            },
        ],
        "recommendation": plan["strategy"]["primary_goal"],
        "suggested_next_action": (
            "Review the recommended content item, then run one controlled creative "
            "test before adding more variables."
        ),
    }


def answer_question(question: str, dashboard_data: dict[str, Any]) -> dict[str, Any]:
    """Answer one analyst question from ``outputs/latest/dashboard_data.json`` data."""
    _require_dashboard_data(dashboard_data)
    clean_question = _normalise_question(question)
    posts = dashboard_data["posts"]
    plan = dashboard_data["content_plan"]

    if any(word in clean_question for word in ("top", "best", "strongest", "winner")):
        answer = _answer_top_post(posts, plan)
    elif any(word in clean_question for word in ("retention", "watch", "drop", "hold")):
        answer = _answer_retention(posts, plan)
    elif any(word in clean_question for word in ("pause", "weak", "worst", "avoid")):
        answer = _answer_pause(plan)
    else:
        answer = _answer_general(dashboard_data)

    missing = [field for field in REQUIRED_ANSWER_FIELDS if field not in answer]
    if missing:
        raise AnalystChatError(
            "Analyst answer is missing required fields: " + ", ".join(missing)
        )
    return answer
