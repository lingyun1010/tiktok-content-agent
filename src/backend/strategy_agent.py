"""Strategy provider boundary for manual and future LLM-backed plans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

SUPPORTED_PROVIDERS = ("manual", "openai", "deepseek")
CONTENT_PLAN_SCHEMA_VERSION = "1.0"
WEAK_RETENTION_THRESHOLD = 0.50


class StrategyProvider(Protocol):
    """Contract implemented by content strategy providers."""

    def generate_plan(
        self, posts: list[dict[str, Any]], summary: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a serialisable content plan."""


def _rank_repeat_candidates(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        post for post in posts if "repeat_candidate" in post["signals"]
    ]
    return sorted(
        candidates,
        key=lambda post: (
            -post["engagement_rate"],
            -(post["average_watch_ratio"] or 0),
            -post["views"],
            post["post_id"],
        ),
    )


def _rank_pause_candidates(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [post for post in posts if "pause_candidate" in post["signals"]]
    return sorted(
        candidates,
        key=lambda post: (
            post["engagement_rate"],
            post["average_watch_ratio"]
            if post["average_watch_ratio"] is not None
            else 1,
            post["post_id"],
        ),
    )


def _weak_retention_posts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (
            post
            for post in posts
            if post["average_watch_ratio"] is not None
            and post["average_watch_ratio"] < WEAK_RETENTION_THRESHOLD
        ),
        key=lambda post: (post["average_watch_ratio"], post["post_id"]),
    )


def _percentage(value: float | None) -> str:
    return "unavailable" if value is None else f"{value * 100:.2f}%"


def _hashtag(value: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", value)
    return "#" + "".join(word.capitalize() for word in words)


def _hashtags(format_name: str, topic: str) -> list[str]:
    candidates = [
        _hashtag(topic),
        _hashtag(format_name),
        "#TikTokContent",
        "#ContentExperiment",
        "#HairCareTips",
    ]
    return list(dict.fromkeys(candidates))


def _pause_actions(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions = []
    for post in posts:
        reason_parts = [
            f"`pause_candidate` on {post['post_id']}",
            f"engagement {_percentage(post['engagement_rate'])}",
        ]
        if post["average_watch_ratio"] is not None:
            reason_parts.append(
                f"watch ratio {_percentage(post['average_watch_ratio'])}"
            )
        if "wrong_region_distribution" in post["signals"]:
            reason_parts.append("wrong-region distribution")
        actions.append(
            {
                "post_id": post["post_id"],
                "format": post["format"],
                "topic": post["topic"],
                "action": "Pause direct repetition until the weak signal is revised.",
                "reason": "; ".join(reason_parts) + ".",
            }
        )
    return actions


@dataclass
class ManualStrategyProvider:
    """Create a deterministic, rule-based plan without APIs or credentials."""

    name: str = "manual"

    def generate_plan(
        self, posts: list[dict[str, Any]], summary: dict[str, Any]
    ) -> dict[str, Any]:
        if not posts:
            raise ValueError("Manual strategy requires at least one analysed post")

        repeat_candidates = _rank_repeat_candidates(posts)
        pause_candidates = _rank_pause_candidates(posts)
        weak_retention = _weak_retention_posts(posts)
        source = repeat_candidates[0] if repeat_candidates else max(
            posts,
            key=lambda post: (
                post["engagement_rate"],
                post["average_watch_ratio"] or 0,
                post["views"],
                post["post_id"],
            ),
        )
        repeat_rule = (
            "`repeat_candidate`"
            if "repeat_candidate" in source["signals"]
            else "highest available engagement fallback"
        )
        retention_guidance = (
            "Use a shorter, punchier edit: state the value immediately, keep one "
            "teaching point, and remove any slow setup."
            if weak_retention
            else "Keep the edit focused and preserve the source post's supported pacing."
        )
        caption = (
            f"{source['hook']}. A clearer way to approach "
            f"{source['topic'].lower()}—save this for your next routine."
        )

        return {
            "schema_version": CONTENT_PLAN_SCHEMA_VERSION,
            "status": "draft_for_human_review",
            "provider": self.name,
            "llm_called": False,
            "human_review_required": True,
            "analysis_basis": {
                "post_count": summary["post_count"],
                "top_post_id": summary["top_post"]["post_id"],
                "repeat_candidate_post_ids": [
                    post["post_id"] for post in repeat_candidates
                ],
                "pause_candidate_post_ids": [
                    post["post_id"] for post in pause_candidates
                ],
                "weak_retention_post_ids": [
                    post["post_id"] for post in weak_retention
                ],
            },
            "strategy": {
                "primary_goal": (
                    f"Retest the strongest supported {source['format']} approach "
                    f"around {source['topic']} while changing one creative variable."
                ),
                "repeat": {
                    "source_post_id": source["post_id"],
                    "format": source["format"],
                    "topic": source["topic"],
                    "reason": (
                        f"Selected by {repeat_rule}: engagement "
                        f"{_percentage(source['engagement_rate'])}, watch ratio "
                        f"{_percentage(source['average_watch_ratio'])}, and signals "
                        f"{', '.join(source['signals']) or 'none'}."
                    ),
                },
                "pause": _pause_actions(pause_candidates),
                "retention_adjustment": {
                    "required": bool(weak_retention),
                    "affected_post_ids": [
                        post["post_id"] for post in weak_retention
                    ],
                    "guidance": retention_guidance,
                },
            },
            "content_item": {
                "id": "manual-001",
                "working_title": f"{source['topic']}: one clear next-step test",
                "format": source["format"],
                "topic": source["topic"],
                "source_post_id": source["post_id"],
                "creative_direction": (
                    "Preserve the proven premise, introduce one new example, and keep "
                    "the test focused so the next performance review is interpretable."
                ),
                "script": {
                    "hook": source["hook"],
                    "body": [
                        (
                            f"Here is the part of {source['topic'].lower()} "
                            "that is easiest to overcomplicate."
                        ),
                        (
                            "Focus on one small adjustment, show it clearly, "
                            "and explain why it matters."
                        ),
                        (
                            "Try that change in your next routine before adding "
                            "anything else."
                        ),
                    ],
                    "cta": "Save this for your next routine and share which step you want explained next.",
                },
                "caption": caption,
                "hashtags": _hashtags(source["format"], source["topic"]),
                "review_checks": [
                    "Verify every product, ingredient, and performance claim.",
                    "Check brand voice, visual context, accessibility, and platform compliance.",
                    "Edit and approve the script, caption, and hashtags before publishing.",
                ],
            },
            "limitations": [
                "Rules describe this small input dataset and do not establish causation.",
                "The draft does not account for current trends, audio, timing, or visual execution.",
                "No content is uploaded, scheduled, or published by this pipeline.",
            ],
        }


def get_strategy_provider(provider_name: str) -> StrategyProvider:
    """Return an implemented provider or explain why it is unavailable."""
    normalised_name = provider_name.strip().lower()
    if normalised_name == "manual":
        return ManualStrategyProvider()
    if normalised_name in {"openai", "deepseek"}:
        raise NotImplementedError(
            f"Provider '{normalised_name}' is reserved for a future opt-in integration."
        )
    raise ValueError(
        f"Unknown provider '{provider_name}'. "
        f"Choose one of: {', '.join(SUPPORTED_PROVIDERS)}"
    )
