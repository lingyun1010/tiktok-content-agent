"""Strategy provider boundary for manual and future LLM-backed plans."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

SUPPORTED_PROVIDERS = ("manual", "openai", "deepseek")


class StrategyProvider(Protocol):
    """Contract implemented by content strategy providers."""

    def generate_plan(
        self, posts: list[dict[str, Any]], summary: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a serialisable content plan."""


@dataclass
class ManualStrategyProvider:
    """Create a deterministic plan that needs no API or credentials."""

    name: str = "manual"

    def generate_plan(
        self, posts: list[dict[str, Any]], summary: dict[str, Any]
    ) -> dict[str, Any]:
        top_post = summary.get("top_post") or {}
        strongest_pillar = top_post.get("content_pillar") or "best-performing theme"
        strongest_hook = top_post.get("hook") or "a clear problem-first hook"

        return {
            "status": "stub",
            "provider": self.name,
            "llm_called": False,
            "based_on": {
                "post_count": summary["post_count"],
                "top_post_id": top_post.get("post_id"),
            },
            "recommendations": [
                {
                    "priority": 1,
                    "idea": f"Create a follow-up around {strongest_pillar}.",
                    "reason": "This pillar appears in the highest-engagement sample post.",
                },
                {
                    "priority": 2,
                    "idea": f"Test a new variation of: {strongest_hook}",
                    "reason": "Keep the winning premise while changing the opening execution.",
                },
                {
                    "priority": 3,
                    "idea": "Compare one educational video with one product-led story.",
                    "reason": "A controlled creative contrast makes the next data review clearer.",
                },
            ],
            "content_items": [
                {
                    "working_title": "Winning theme, new angle",
                    "content_pillar": strongest_pillar,
                    "script": None,
                    "caption": None,
                    "hashtags": [],
                    "human_review_required": True,
                }
            ],
            "next_step": (
                "Review these placeholders and use a future provider adapter "
                "to draft scripts, captions, and hashtags."
            ),
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

