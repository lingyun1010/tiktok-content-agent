"""Offline evaluation harness for deterministic analyst chat behaviour."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .analyst import AnalystError, answer_question

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DASHBOARD_FIXTURE = (
    PROJECT_ROOT / "tests" / "fixtures" / "analyst_dashboard_data.json"
)
DEFAULT_CASES_PATH = PROJECT_ROOT / "tests" / "fixtures" / "analyst_eval_cases.json"
REQUIRED_RESPONSE_FIELDS = (
    "summary",
    "evidence",
    "recommendation",
    "suggested_next_action",
    "limitations",
    "provider",
    "llm_called",
)
FORBIDDEN_TRACE_LANGUAGE = (
    "i reasoned step by step",
    "chain-of-thought",
    "hidden reasoning",
    "private reasoning",
)


@dataclass(frozen=True)
class EvaluationResult:
    """One analyst evaluation result."""

    case_id: str
    passed: bool
    failures: list[str]
    intent: str | None = None
    tools_used: list[str] | None = None


def load_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def load_eval_cases(path: Path = DEFAULT_CASES_PATH) -> list[dict[str, Any]]:
    """Load analyst evaluation cases."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path} must contain a non-empty JSON list.")
    cases: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Evaluation case {index} must be an object.")
        if not isinstance(item.get("id"), str) or not item["id"].strip():
            raise ValueError(f"Evaluation case {index} is missing id.")
        if not isinstance(item.get("question"), str) or not item["question"].strip():
            raise ValueError(f"Evaluation case {item['id']} is missing question.")
        if item.get("expected_provider", "manual") != "manual":
            raise ValueError(
                f"Evaluation case {item['id']} must use the manual provider."
            )
        cases.append(item)
    return cases


def evaluate_cases(
    cases: Iterable[Mapping[str, Any]],
    dashboard_data: Mapping[str, Any],
) -> list[EvaluationResult]:
    """Run all eval cases against the manual analyst provider."""
    results: list[EvaluationResult] = []
    for case in cases:
        results.append(evaluate_case(case, dashboard_data))
    return results


def evaluate_case(
    case: Mapping[str, Any],
    dashboard_data: Mapping[str, Any],
) -> EvaluationResult:
    """Run and validate one analyst eval case."""
    case_id = str(case.get("id", "unknown"))
    try:
        response = answer_question(
            str(case["question"]),
            dashboard_data,
            provider="manual",
        )
    except (AnalystError, KeyError, TypeError, ValueError) as exc:
        return EvaluationResult(case_id, False, [f"answer failed: {exc}"])

    failures = validate_response(case, response)
    trace = response.get("trace", {})
    tools_used = trace.get("tools_used") if isinstance(trace, Mapping) else None
    return EvaluationResult(
        case_id=case_id,
        passed=not failures,
        failures=failures,
        intent=trace.get("interpreted_intent") if isinstance(trace, Mapping) else None,
        tools_used=list(tools_used) if isinstance(tools_used, list) else None,
    )


def validate_response(
    case: Mapping[str, Any],
    response: Mapping[str, Any],
) -> list[str]:
    """Validate a manual analyst response against one eval case."""
    failures: list[str] = []
    for field in REQUIRED_RESPONSE_FIELDS:
        if field not in response:
            failures.append(f"missing required field: {field}")

    expected_provider = case.get("expected_provider", "manual")
    if response.get("provider") != expected_provider:
        failures.append(
            f"provider was {response.get('provider')!r}, expected {expected_provider!r}"
        )

    expected_llm_called = case.get("expected_llm_called", False)
    if response.get("llm_called") is not expected_llm_called:
        failures.append(
            "llm_called was "
            f"{response.get('llm_called')!r}, expected {expected_llm_called!r}"
        )

    if case.get("expect_evidence") and not _non_empty_list(response.get("evidence")):
        failures.append("expected non-empty evidence")

    if case.get("expect_limitations") and not _non_empty_list(
        response.get("limitations")
    ):
        failures.append("expected non-empty limitations")

    expected_keywords = case.get("expected_limitation_keywords")
    if expected_keywords:
        failures.extend(
            _validate_limitation_keywords(
                response.get("limitations"),
                [str(keyword) for keyword in expected_keywords],
            )
        )

    if case.get("expected_tools") or case.get("expected_intent"):
        failures.extend(_validate_trace(case, response.get("trace")))

    return failures


def _validate_trace(case: Mapping[str, Any], trace: Any) -> list[str]:
    failures: list[str] = []
    if not isinstance(trace, Mapping):
        return ["expected trace object"]

    expected_intent = case.get("expected_intent")
    actual_intent = trace.get("interpreted_intent")
    if expected_intent and (
        not isinstance(actual_intent, str) or str(expected_intent) not in actual_intent
    ):
        failures.append(
            f"intent was {actual_intent!r}, expected to contain {expected_intent!r}"
        )

    tools_used = trace.get("tools_used")
    if not isinstance(tools_used, list):
        failures.append("trace.tools_used must be a list")
    else:
        for expected_tool in case.get("expected_tools", []):
            if expected_tool not in tools_used:
                failures.append(f"missing expected tool: {expected_tool}")

    observations = trace.get("observations")
    if not isinstance(observations, list):
        failures.append("trace.observations must be a list")
    else:
        failures.extend(_validate_observations(observations))

    return failures


def _validate_observations(observations: Sequence[Any]) -> list[str]:
    failures: list[str] = []
    for index, observation in enumerate(observations):
        if not isinstance(observation, str) or not observation.strip():
            failures.append(f"trace.observations[{index}] must be a string")
            continue
        word_count = len(observation.split())
        if word_count > 24:
            failures.append(
                f"trace.observations[{index}] should be short; got {word_count} words"
            )
        lowered = observation.lower()
        for forbidden in FORBIDDEN_TRACE_LANGUAGE:
            if forbidden in lowered:
                failures.append(
                    f"trace.observations[{index}] contains hidden reasoning language"
                )
    return failures


def _validate_limitation_keywords(
    limitations: Any, expected_keywords: Sequence[str]
) -> list[str]:
    if not isinstance(limitations, list):
        return ["limitations must be a list before keyword checks"]
    joined = " ".join(
        limitation.lower() for limitation in limitations if isinstance(limitation, str)
    )
    if any(keyword.lower() in joined for keyword in expected_keywords):
        return []
    return [
        "limitations did not contain any expected keyword: "
        + ", ".join(expected_keywords)
    ]


def _non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def format_report(results: Sequence[EvaluationResult]) -> str:
    """Format a compact pass/fail report for local runs and CI logs."""
    passed_count = sum(1 for result in results if result.passed)
    lines = [
        "Analyst evaluation harness",
        f"Cases: {passed_count}/{len(results)} passed",
    ]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        detail_parts = []
        if result.intent:
            detail_parts.append(f"intent={result.intent}")
        if result.tools_used:
            detail_parts.append("tools=" + ",".join(result.tools_used))
        detail = " (" + "; ".join(detail_parts) + ")" if detail_parts else ""
        lines.append(f"- {status} {result.case_id}{detail}")
        for failure in result.failures:
            lines.append(f"  - {failure}")
    return "\n".join(lines)


def main() -> int:
    """Run the analyst eval harness from the command line."""
    dashboard_data = load_json_object(DEFAULT_DASHBOARD_FIXTURE)
    cases = load_eval_cases(DEFAULT_CASES_PATH)
    results = evaluate_cases(cases, dashboard_data)
    print(format_report(results))
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
