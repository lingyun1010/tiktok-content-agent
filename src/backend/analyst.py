"""Analyst chat providers grounded in the latest dashboard data."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Mapping

from .analyst_tools import (
    get_dashboard_summary,
    get_pause_candidates,
    get_repeat_candidates,
    get_retention_issues,
    get_top_posts,
    get_underperforming_posts,
)
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
            "trace": {
                "interpreted_intent": "optional string",
                "tools_used": ["optional string"],
                "observations": ["optional string"],
                "limitations": ["optional string"],
            },
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


def _base_limitations(provider: str) -> list[str]:
    return [
        f"Answer generated by the {provider} analyst provider.",
        "Grounded only in outputs/latest/dashboard_data.json.",
        "Descriptive analysis only; it cannot prove causation or predict performance.",
    ]


def _answer_top_post(
    dashboard_data: Mapping[str, Any], plan: Mapping[str, Any], provider: str
) -> dict[str, Any]:
    posts = get_top_posts(dashboard_data, limit=1)
    post = posts[0]
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
    dashboard_data: Mapping[str, Any], plan: Mapping[str, Any], provider: str
) -> dict[str, Any]:
    issues = get_retention_issues(dashboard_data)
    weakest = issues[0] if issues else None
    retention = plan["strategy"]["retention_adjustment"]
    affected = retention.get("affected_post_ids", []) or [
        post["post_id"] for post in issues
    ]
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


def _answer_pause(
    dashboard_data: Mapping[str, Any], plan: Mapping[str, Any], provider: str
) -> dict[str, Any]:
    pause_items = plan["strategy"].get("pause", [])
    pause_candidates = get_pause_candidates(dashboard_data)
    if not pause_items and not pause_candidates:
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
    first_pause = pause_items[0] if pause_items else {}
    first_candidate = pause_candidates[0] if pause_candidates else {}
    post_id = first_pause.get("post_id") or first_candidate.get("post_id")
    return {
        "summary": (
            f"{post_id} is the clearest pause candidate in this run."
        ),
        "evidence": _pause_evidence(pause_items, pause_candidates),
        "recommendation": first_pause.get("action")
        or "Revise the weakest-performing post before repeating it.",
        "suggested_next_action": (
            "Revise the hook, pacing, or audience cue before repeating this format."
        ),
        "limitations": _base_limitations(provider),
    }


def _pause_evidence(
    pause_items: list[dict[str, Any]], pause_candidates: list[dict[str, Any]]
) -> list[dict[str, str]]:
    if pause_items:
        return [
            {
                "post_id": item["post_id"],
                "metric": "pause_reason",
                "value": item["reason"],
            }
            for item in pause_items
        ]
    return [
        {
            "post_id": post["post_id"],
            "metric": "signals",
            "value": ", ".join(post.get("signals", [])) or "pause_candidate",
        }
        for post in pause_candidates
    ]


def _answer_underperforming(
    dashboard_data: Mapping[str, Any], provider: str
) -> dict[str, Any]:
    posts = get_underperforming_posts(dashboard_data, limit=3)
    return {
        "summary": (
            "The latest dashboard can show which posts underperformed, but it "
            "cannot fully explain a specific view plateau."
        ),
        "evidence": [
            {
                "post_id": post["post_id"],
                "metric": "views",
                "value": _format_compact(post["views"] or 0),
            }
            for post in posts
        ],
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
    summary = get_dashboard_summary(dashboard_data)
    plan = dashboard_data["content_plan"]
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
                "value": ", ".join(summary.get("repeat_post_ids", [])) or "none",
            },
            {
                "post_id": "pause_candidates",
                "metric": "post_ids",
                "value": ", ".join(summary.get("pause_post_ids", [])) or "none",
            },
        ],
        "recommendation": plan["strategy"]["primary_goal"],
        "suggested_next_action": (
            "Review the recommended content item, then run one controlled creative "
            "test before adding more variables."
        ),
        "limitations": _base_limitations(provider),
    }


def _answer_hook_reuse(
    dashboard_data: Mapping[str, Any], plan: Mapping[str, Any], provider: str
) -> dict[str, Any]:
    repeats = get_repeat_candidates(dashboard_data)
    source = repeats[0] if repeats else get_top_posts(dashboard_data, limit=1)[0]
    return {
        "summary": (
            f"Reuse the pattern behind {source['post_id']}: "
            f"{source.get('hook') or 'hook unavailable'}."
        ),
        "evidence": [
            {
                "post_id": source["post_id"],
                "metric": "signals",
                "value": ", ".join(source.get("signals", [])) or "top_post",
            },
            {
                "post_id": source["post_id"],
                "metric": "engagement_rate",
                "value": _percentage(source.get("engagement_rate")),
            },
        ],
        "recommendation": plan["strategy"]["primary_goal"],
        "suggested_next_action": plan["strategy"]["primary_goal"],
        "limitations": _base_limitations(provider),
    }


def _trace(
    interpreted_intent: str,
    tools_used: list[str],
    observations: list[str],
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    default_limitations = ["Grounded only in outputs/latest/dashboard_data.json."]
    return {
        "interpreted_intent": interpreted_intent,
        "tools_used": tools_used,
        "observations": observations,
        "limitations": limitations or default_limitations,
    }


def _post_observation(post: Mapping[str, Any], label: str) -> str:
    return f"{post.get('post_id')} {label} among the loaded posts."


def manual_answer(question: str, dashboard_data: Mapping[str, Any]) -> dict[str, Any]:
    """Answer one analyst question with deterministic local rules."""
    validate_dashboard_data(dashboard_data)
    clean_question = _normalise_question(question)
    plan = dashboard_data["content_plan"]

    if any(
        word in clean_question
        for word in ("top", "best", "strongest", "winner", "performed")
    ):
        top_post = get_top_posts(dashboard_data, limit=1)[0]
        answer = _answer_top_post(dashboard_data, plan, "manual")
        answer["trace"] = _trace(
            "best_performing_posts",
            ["get_top_posts"],
            [
                _post_observation(top_post, "had the highest engagement rate"),
                f"{top_post['post_id']} signals: {', '.join(top_post.get('signals', [])) or 'none'}.",
            ],
        )
    elif any(
        word in clean_question
        for word in ("hook", "reuse", "repeat", "post tomorrow", "tomorrow")
    ):
        repeats = get_repeat_candidates(dashboard_data)
        answer = _answer_hook_reuse(dashboard_data, plan, "manual")
        answer["trace"] = _trace(
            "hook_reuse",
            ["get_repeat_candidates", "get_top_posts"]
            if not repeats
            else ["get_repeat_candidates"],
            [
                (
                    f"{repeats[0]['post_id']} was marked as a repeat candidate."
                    if repeats
                    else "No repeat candidate was available, so the top post was used."
                )
            ],
        )
    elif any(
        word in clean_question
        for word in ("retention", "watch", "drop", "hold", "pacing")
    ):
        issues = get_retention_issues(dashboard_data)
        answer = _answer_retention(dashboard_data, plan, "manual")
        answer["trace"] = _trace(
            "retention_issues",
            ["get_retention_issues"],
            [
                (
                    f"{issues[0]['post_id']} had the weakest available watch ratio."
                    if issues
                    else "No weak retention item was found in the loaded posts."
                )
            ],
        )
    elif any(word in clean_question for word in ("pause", "weak", "worst", "avoid")):
        pauses = get_pause_candidates(dashboard_data)
        answer = _answer_pause(dashboard_data, plan, "manual")
        answer["trace"] = _trace(
            "pause_or_avoid",
            ["get_pause_candidates", "get_underperforming_posts"]
            if not pauses
            else ["get_pause_candidates"],
            [
                (
                    f"{pauses[0]['post_id']} was marked as a pause candidate."
                    if pauses
                    else "No pause candidate was available, so underperforming posts were checked."
                )
            ],
        )
    elif any(
        phrase in clean_question
        for phrase in (
            "90 views",
            "low views",
            "underperforming",
            "stuck",
            "can't you tell",
            "cannot tell",
        )
    ):
        underperforming = get_underperforming_posts(dashboard_data, limit=1)
        answer = _answer_underperforming(dashboard_data, "manual")
        answer["trace"] = _trace(
            "underperforming_or_low_views",
            ["get_underperforming_posts"],
            [
                (
                    f"{underperforming[0]['post_id']} had one of the lowest view counts."
                    if underperforming
                    else "No loaded post was available for underperformance comparison."
                )
            ],
            [
                "Grounded only in outputs/latest/dashboard_data.json.",
                "No impression, traffic-source, audio trend, or distribution diagnostics are available.",
            ],
        )
    else:
        answer = _answer_general(dashboard_data, "manual")
        summary = get_dashboard_summary(dashboard_data)
        answer["trace"] = _trace(
            "general_summary",
            ["get_dashboard_summary"],
            [
                f"{summary.get('post_count')} posts were loaded from the latest dashboard data.",
                f"Repeat candidates: {', '.join(summary.get('repeat_post_ids', [])) or 'none'}.",
            ],
        )

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
    if "trace" in payload:
        answer["trace"] = _validate_trace(payload["trace"])
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


def _validate_trace(trace: Any) -> dict[str, Any]:
    if not isinstance(trace, dict):
        raise AnalystError("Analyst response field 'trace' must be an object.")
    intent = trace.get("interpreted_intent")
    if not isinstance(intent, str) or not intent.strip():
        raise AnalystError("Analyst trace field 'interpreted_intent' must be a string.")
    cleaned = {"interpreted_intent": intent.strip()}
    for field in ("tools_used", "observations"):
        values = trace.get(field)
        if not isinstance(values, list):
            raise AnalystError(f"Analyst trace field '{field}' must be a list.")
        cleaned[field] = _validate_string_list(values, f"trace.{field}")
    values = trace.get("limitations", [])
    if values is None:
        values = []
    if not isinstance(values, list):
        raise AnalystError("Analyst trace field 'limitations' must be a list.")
    cleaned["limitations"] = _validate_string_list(values, "trace.limitations")
    return cleaned


def _validate_string_list(values: list[Any], field_name: str) -> list[str]:
    cleaned = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise AnalystError(f"Analyst {field_name}[{index}] must be a string.")
        cleaned.append(value.strip())
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
