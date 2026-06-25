"""Analyst chat providers grounded in the latest dashboard data."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Mapping

from .llm_strategy import (
    CLAUDE_ENDPOINT,
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_OPENAI_MODEL,
    OPENAI_ENDPOINT,
    LLMStrategyError,
    _decode_json_response,
    _load_local_dotenv,
    _post_json,
    _required_environment,
)

AnalystProviderName = Literal["manual", "openai", "claude"]

SUPPORTED_ANALYST_PROVIDERS = ("manual", "openai", "claude")
DEFAULT_DASHBOARD_PATH = Path("outputs/latest/dashboard_data.json")
REQUIRED_DASHBOARD_FIELDS = (
    "generated_at",
    "source",
    "provider",
    "dataset_overview",
    "posts",
    "signals",
    "content_plan",
)
REQUIRED_ANSWER_FIELDS = (
    "summary",
    "evidence",
    "recommendation",
    "suggested_next_action",
    "limitations",
)


class AnalystError(ValueError):
    """Raised when analyst input, configuration, or output is invalid."""


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
        raise AnalystError("Question is required.")
    return clean_question


def load_dashboard_data(path: Path = DEFAULT_DASHBOARD_PATH) -> dict[str, Any]:
    """Load the latest dashboard JSON produced by the pipeline."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AnalystError(
            "No latest dashboard data found. Run the backend pipeline first."
        ) from exc
    except json.JSONDecodeError as exc:
        raise AnalystError("Latest dashboard data is invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise AnalystError("Latest dashboard data must be a JSON object.")
    validate_dashboard_data(payload)
    return payload


def validate_dashboard_data(dashboard_data: Mapping[str, Any]) -> None:
    """Validate the fields the analyst needs from the dashboard contract."""
    missing = [
        field for field in REQUIRED_DASHBOARD_FIELDS if field not in dashboard_data
    ]
    if missing:
        raise AnalystError(
            "Dashboard data is missing required fields: " + ", ".join(missing)
        )
    posts = dashboard_data["posts"]
    if not isinstance(posts, list) or not posts:
        raise AnalystError("Dashboard data must include at least one post.")
    if not isinstance(dashboard_data["dataset_overview"], dict):
        raise AnalystError("Dashboard data field 'dataset_overview' must be an object.")
    if not isinstance(dashboard_data["signals"], dict):
        raise AnalystError("Dashboard data field 'signals' must be an object.")
    if not isinstance(dashboard_data["content_plan"], dict):
        raise AnalystError("Dashboard data field 'content_plan' must be an object.")


def build_safe_context(dashboard_data: Mapping[str, Any]) -> dict[str, Any]:
    """Build a compact context without raw private records or credentials."""
    validate_dashboard_data(dashboard_data)
    summary = dashboard_data["dataset_overview"]
    plan = dashboard_data["content_plan"]
    strategy = plan.get("strategy", {})
    content_item = plan.get("content_item", {})

    return {
        "generated_at": dashboard_data["generated_at"],
        "source": dashboard_data["source"],
        "pipeline_provider": dashboard_data["provider"],
        "dataset_overview": {
            "post_count": summary.get("post_count"),
            "total_views": summary.get("total_views"),
            "average_views": summary.get("average_views"),
            "average_engagement_rate": summary.get("average_engagement_rate"),
            "average_watch_ratio": summary.get("average_watch_ratio"),
            "top_post": _safe_post_summary(summary.get("top_post", {})),
        },
        "posts": [_safe_post_summary(post) for post in dashboard_data["posts"]],
        "signals": {
            "repeat_post_ids": list(
                dashboard_data["signals"].get("repeat_post_ids", [])
            ),
            "pause_post_ids": list(
                dashboard_data["signals"].get("pause_post_ids", [])
            ),
            "weak_retention_post_ids": list(
                dashboard_data["signals"].get("weak_retention_post_ids", [])
            ),
        },
        "strategy": {
            "primary_goal": strategy.get("primary_goal"),
            "repeat": strategy.get("repeat", {}),
            "pause": strategy.get("pause", []),
            "retention_adjustment": strategy.get("retention_adjustment", {}),
        },
        "content_item": {
            "working_title": content_item.get("working_title"),
            "format": content_item.get("format"),
            "topic": content_item.get("topic"),
            "source_post_id": content_item.get("source_post_id"),
            "creative_direction": content_item.get("creative_direction"),
        },
        "required_response_schema": {
            "summary": "string",
            "evidence": [
                {
                    "post_id": "string",
                    "metric": "string",
                    "value": "string",
                }
            ],
            "recommendation": "string",
            "suggested_next_action": "string",
            "limitations": ["string"],
        },
    }


def _safe_post_summary(post: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "post_id": post.get("post_id"),
        "format": post.get("format"),
        "topic": post.get("topic"),
        "hook": post.get("hook"),
        "views": post.get("views"),
        "engagement_rate": post.get("engagement_rate"),
        "average_watch_ratio": post.get("average_watch_ratio"),
        "region_match_score": post.get("region_match_score"),
        "signals": list(post.get("signals", [])),
    }


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


def _base_limitations(provider: str) -> list[str]:
    return [
        f"Answer generated by the {provider} analyst provider.",
        "Grounded only in outputs/latest/dashboard_data.json.",
        "Descriptive analysis only; it cannot prove causation or predict performance.",
    ]


def _answer_top_post(
    posts: list[dict[str, Any]], plan: Mapping[str, Any], provider: str
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
        "limitations": _base_limitations(provider),
    }


def _answer_retention(
    posts: list[dict[str, Any]], plan: Mapping[str, Any], provider: str
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
        "limitations": _base_limitations(provider),
    }


def _answer_pause(plan: Mapping[str, Any], provider: str) -> dict[str, Any]:
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
            "limitations": _base_limitations(provider),
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
        "limitations": _base_limitations(provider),
    }


def _answer_unknown_limits(provider: str) -> dict[str, Any]:
    return {
        "summary": (
            "The current dashboard data does not explain why performance is stuck "
            "at a specific view count."
        ),
        "evidence": [],
        "recommendation": (
            "Treat this as an unknown until you add distribution context such as "
            "posting time, traffic source, audience retention curve, audio, and "
            "impression data."
        ),
        "suggested_next_action": (
            "Run one controlled hook or pacing test, then compare the next batch "
            "against this dashboard's views, engagement, and watch-ratio fields."
        ),
        "limitations": _base_limitations(provider)
        + [
            "The dashboard contract does not include impressions, traffic source, follower status, audio trend, or platform distribution diagnostics.",
        ],
    }


def _answer_general(
    dashboard_data: Mapping[str, Any], provider: str
) -> dict[str, Any]:
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
        "limitations": _base_limitations(provider),
    }


def manual_answer(question: str, dashboard_data: Mapping[str, Any]) -> dict[str, Any]:
    """Answer one analyst question with deterministic local rules."""
    validate_dashboard_data(dashboard_data)
    clean_question = _normalise_question(question)
    posts = list(dashboard_data["posts"])
    plan = dashboard_data["content_plan"]

    if any(
        word in clean_question
        for word in ("top", "best", "strongest", "winner", "performed")
    ):
        answer = _answer_top_post(posts, plan, "manual")
    elif any(
        word in clean_question
        for word in ("hook", "reuse", "repeat", "post tomorrow", "tomorrow")
    ):
        answer = _answer_top_post(posts, plan, "manual")
        answer["suggested_next_action"] = plan["strategy"]["primary_goal"]
    elif any(
        word in clean_question
        for word in ("retention", "watch", "drop", "hold", "pacing")
    ):
        answer = _answer_retention(posts, plan, "manual")
    elif any(word in clean_question for word in ("pause", "weak", "worst", "avoid")):
        answer = _answer_pause(plan, "manual")
    elif any(
        phrase in clean_question
        for phrase in ("90 views", "stuck", "can't you tell", "cannot tell")
    ):
        answer = _answer_unknown_limits("manual")
    else:
        answer = _answer_general(dashboard_data, "manual")

    return _finalise_answer(answer, provider="manual", llm_called=False)


def _finalise_answer(
    payload: Mapping[str, Any], *, provider: str, llm_called: bool
) -> dict[str, Any]:
    answer = validate_answer_payload(payload)
    answer["provider"] = provider
    answer["llm_called"] = llm_called
    return answer


def validate_answer_payload(payload: Any) -> dict[str, Any]:
    """Validate analyst answer JSON before it reaches the frontend."""
    if not isinstance(payload, dict):
        raise AnalystError("Analyst response must be a JSON object.")
    missing = [field for field in REQUIRED_ANSWER_FIELDS if field not in payload]
    if missing:
        raise AnalystError(
            "Analyst response is missing required fields: " + ", ".join(missing)
        )
    answer: dict[str, Any] = {}
    for field in ("summary", "recommendation", "suggested_next_action"):
        value = payload[field]
        if not isinstance(value, str) or not value.strip():
            raise AnalystError(f"Analyst response field '{field}' must be a string.")
        answer[field] = value.strip()
    evidence = payload["evidence"]
    if not isinstance(evidence, list):
        raise AnalystError("Analyst response field 'evidence' must be a list.")
    answer["evidence"] = [_validate_evidence_item(item) for item in evidence]
    limitations = payload["limitations"]
    if not isinstance(limitations, list) or not limitations:
        raise AnalystError("Analyst response field 'limitations' must be a list.")
    answer["limitations"] = []
    for index, limitation in enumerate(limitations):
        if not isinstance(limitation, str) or not limitation.strip():
            raise AnalystError(
                f"Analyst response field 'limitations[{index}]' must be a string."
            )
        answer["limitations"].append(limitation.strip())
    return answer


def _validate_evidence_item(item: Any) -> dict[str, str]:
    if not isinstance(item, dict):
        raise AnalystError("Analyst evidence entries must be objects.")
    cleaned = {}
    for field in ("post_id", "metric", "value"):
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            raise AnalystError(
                f"Analyst evidence field '{field}' must be a string."
            )
        cleaned[field] = value.strip()
    return cleaned


def _analyst_prompt() -> str:
    return (
        "You are an analyst for a TikTok content performance dashboard. "
        "Answer only from the provided dashboard JSON context. Do not infer "
        "facts that are not present. If the context cannot answer the question, "
        "say so in limitations and recommend what data is missing. Return only "
        "valid JSON matching the required_response_schema."
    )


def _decode_provider_text(response: Mapping[str, Any], provider: str) -> str:
    if provider == "OpenAI":
        texts = [
            part["text"]
            for item in response.get("output", [])
            for part in item.get("content", [])
            if part.get("type") == "output_text" and isinstance(part.get("text"), str)
        ]
    else:
        texts = [
            item["text"]
            for item in response.get("content", [])
            if item.get("type") == "text" and isinstance(item.get("text"), str)
        ]
    if not texts:
        raise AnalystError(f"{provider} returned no analyst text.")
    return "".join(texts)


@dataclass(repr=False)
class OpenAIAnalystProvider:
    """Generate analyst answers with the OpenAI Responses API."""

    api_key: str
    model: str
    post_json: Callable[..., dict[str, Any]] = _post_json

    @classmethod
    def from_environment(cls) -> "OpenAIAnalystProvider":
        _load_local_dotenv()
        return cls(
            api_key=_required_environment("OPENAI_API_KEY", "OpenAI"),
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip()
            or DEFAULT_OPENAI_MODEL,
        )

    def answer(self, question: str, dashboard_data: Mapping[str, Any]) -> dict[str, Any]:
        context = build_safe_context(dashboard_data)
        response = self.post_json(
            OPENAI_ENDPOINT,
            {"Authorization": f"Bearer {self.api_key}"},
            {
                "model": self.model,
                "instructions": _analyst_prompt(),
                "input": json.dumps(
                    {"question": question, "dashboard_context": context},
                    ensure_ascii=False,
                ),
            },
            "OpenAI",
        )
        text = _decode_provider_text(response, "OpenAI")
        try:
            payload = _decode_json_response(text, "OpenAI")
            return _finalise_answer(payload, provider="openai", llm_called=True)
        except LLMStrategyError as exc:
            raise AnalystError(str(exc)) from exc


@dataclass(repr=False)
class ClaudeAnalystProvider:
    """Generate analyst answers with the Anthropic Claude Messages API."""

    api_key: str
    model: str
    post_json: Callable[..., dict[str, Any]] = _post_json

    @classmethod
    def from_environment(cls) -> "ClaudeAnalystProvider":
        _load_local_dotenv()
        return cls(
            api_key=_required_environment("CLAUDE_API_KEY", "Claude"),
            model=os.getenv("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL).strip()
            or DEFAULT_CLAUDE_MODEL,
        )

    def answer(self, question: str, dashboard_data: Mapping[str, Any]) -> dict[str, Any]:
        context = build_safe_context(dashboard_data)
        response = self.post_json(
            CLAUDE_ENDPOINT,
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            {
                "model": self.model,
                "max_tokens": 2048,
                "system": _analyst_prompt(),
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"question": question, "dashboard_context": context},
                            ensure_ascii=False,
                        ),
                    }
                ],
            },
            "Claude",
        )
        text = _decode_provider_text(response, "Claude")
        try:
            payload = _decode_json_response(text, "Claude")
            return _finalise_answer(payload, provider="claude", llm_called=True)
        except LLMStrategyError as exc:
            raise AnalystError(str(exc)) from exc


def answer_question(
    question: str,
    dashboard_data: Mapping[str, Any],
    provider: str = "manual",
) -> dict[str, Any]:
    """Answer an analyst question using the selected provider."""
    provider_name = provider.strip().lower()
    if provider_name not in SUPPORTED_ANALYST_PROVIDERS:
        raise AnalystError(
            f"Unknown analyst provider '{provider}'. Choose one of: "
            + ", ".join(SUPPORTED_ANALYST_PROVIDERS)
        )
    if provider_name == "manual":
        return manual_answer(question, dashboard_data)
    if provider_name == "openai":
        return OpenAIAnalystProvider.from_environment().answer(
            question, dashboard_data
        )
    return ClaudeAnalystProvider.from_environment().answer(question, dashboard_data)
