from __future__ import annotations

from datetime import datetime
from typing import Any

MODEL_RATES: dict[str, tuple[float, float]] = {
    "gpt-4.1-mini": (0.00000015, 0.0000006),
    "gpt-4.1": (0.000002, 0.000008),
    "gpt-4o-mini": (0.00000015, 0.0000006),
}


def _parse_iso(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def span_latency_ms(span: dict[str, Any]) -> int | None:
    attrs = span.get("attributes") or {}
    if attrs.get("llm.latency_ms") is not None:
        return int(attrs["llm.latency_ms"])
    if attrs.get("tool.latency_ms") is not None:
        return int(attrs["tool.latency_ms"])

    start = _parse_iso(span.get("started_at"))
    end = _parse_iso(span.get("ended_at"))
    if start and end:
        return max(int((end - start).total_seconds() * 1000), 0)
    return None


def estimate_cost_usd(model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    rates = MODEL_RATES.get(model)
    if rates is None:
        return None
    inp = input_tokens or 0
    out = output_tokens or 0
    return round(inp * rates[0] + out * rates[1], 6)


def enrich_span(span: dict[str, Any]) -> dict[str, Any]:
    attrs = dict(span.get("attributes") or {})
    latency = span_latency_ms(span)
    span_type = span.get("span_type")

    if latency is not None:
        if span_type == "llm.call":
            attrs.setdefault("llm.latency_ms", latency)
        elif span_type == "tool.call":
            attrs.setdefault("tool.latency_ms", latency)

    if span_type == "llm.call":
        model = str(attrs.get("llm.model", "unknown"))
        input_tokens = attrs.get("llm.input_tokens")
        output_tokens = attrs.get("llm.output_tokens")
        if input_tokens is not None:
            input_tokens = int(input_tokens)
        if output_tokens is not None:
            output_tokens = int(output_tokens)
        cost = estimate_cost_usd(model, input_tokens, output_tokens)
        if cost is not None:
            attrs.setdefault("llm.cost_usd", cost)

    span["attributes"] = attrs
    return span


def compute_run_metrics(agent_run: dict[str, Any], spans: list[dict[str, Any]]) -> dict[str, Any]:
    input_tokens = 0
    output_tokens = 0
    cost_usd = 0.0
    has_cost = False

    for span in spans:
        if span.get("span_type") != "llm.call":
            continue
        attrs = span.get("attributes") or {}
        input_tokens += int(attrs.get("llm.input_tokens") or 0)
        output_tokens += int(attrs.get("llm.output_tokens") or 0)
        cost = attrs.get("llm.cost_usd")
        if cost is not None:
            cost_usd += float(cost)
            has_cost = True

    start = _parse_iso(agent_run.get("started_at"))
    end = _parse_iso(agent_run.get("ended_at"))
    latency_ms = None
    if start and end:
        latency_ms = max(int((end - start).total_seconds() * 1000), 0)

    metrics: dict[str, Any] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
    }
    if has_cost:
        metrics["cost_usd"] = round(cost_usd, 6)
    return metrics