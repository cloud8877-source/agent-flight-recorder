from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue

from collector.metrics import compute_run_metrics, enrich_span, estimate_cost_usd, span_latency_ms
from collector.redaction import redact_attributes

AFR_SPAN_TYPE = "afr.span_type"
AFR_RUN_ID = "afr.run_id"
AFR_AGENT_NAME = "afr.agent_name"
AFR_ENVIRONMENT = "afr.environment"


def _hex_id(value: bytes) -> str | None:
    if not value:
        return None
    return value.hex()


def _ns_to_iso(ns: int) -> str | None:
    if ns <= 0:
        return None
    return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc).isoformat()


def _any_value(value: AnyValue) -> Any:
    which = value.WhichOneof("value")
    if which == "string_value":
        return value.string_value
    if which == "bool_value":
        return value.bool_value
    if which == "int_value":
        return value.int_value
    if which == "double_value":
        return value.double_value
    if which == "array_value":
        return [_any_value(item) for item in value.array_value.values]
    if which == "kvlist_value":
        return {kv.key: _any_value(kv.value) for kv in value.kvlist_value.values}
    return None


def _attrs(values: Any) -> dict[str, Any]:
    return {kv.key: _any_value(kv.value) for kv in values}


def _span_status(code: int) -> str:
    if code == 2:
        return "error"
    return "ok"


def _parse_export_request(body: bytes) -> list[dict[str, Any]]:
    request = ExportTraceServiceRequest()
    request.ParseFromString(body)
    spans: list[dict[str, Any]] = []

    for resource_spans in request.resource_spans:
        resource_attrs = _attrs(resource_spans.resource.attributes)
        for scope_spans in resource_spans.scope_spans:
            for span in scope_spans.spans:
                attrs = _attrs(span.attributes)
                merged_attrs = redact_attributes({**resource_attrs, **attrs})
                spans.append(
                    {
                        "trace_id": _hex_id(span.trace_id),
                        "span_id": _hex_id(span.span_id),
                        "parent_span_id": _hex_id(span.parent_span_id),
                        "name": span.name or "span",
                        "span_type": merged_attrs.get(AFR_SPAN_TYPE, "agent.step"),
                        "status": _span_status(span.status.code),
                        "started_at": _ns_to_iso(span.start_time_unix_nano),
                        "ended_at": _ns_to_iso(span.end_time_unix_nano),
                        "attributes": merged_attrs,
                    }
                )
    return spans


def _derive_agent_run(trace_id: str, spans: list[dict[str, Any]]) -> dict[str, Any]:
    root_candidates = [s for s in spans if not s.get("parent_span_id")]
    root = next((s for s in root_candidates if s.get("span_type") == "agent.run"), None)
    if root is None and root_candidates:
        root = root_candidates[0]
    if root is None and spans:
        root = spans[0]

    attrs = root.get("attributes", {}) if root else {}
    run_id = attrs.get(AFR_RUN_ID) or f"run_{trace_id[:12]}"
    agent_name = attrs.get(AFR_AGENT_NAME) or (root.get("name") if root else "unknown-agent")
    environment = attrs.get(AFR_ENVIRONMENT) or attrs.get("deployment.environment") or "development"
    user_id = attrs.get("enduser.id")
    session_id = attrs.get("afr.session_id")

    started_times = [s["started_at"] for s in spans if s.get("started_at")]
    ended_times = [s["ended_at"] for s in spans if s.get("ended_at")]
    started_at = root.get("started_at") if root else (min(started_times) if started_times else datetime.now(timezone.utc).isoformat())
    ended_at = root.get("ended_at") if root else (max(ended_times) if ended_times else None)

    has_error = any(s.get("status") == "error" for s in spans)
    status = "failed" if has_error else "success"

    agent_run = {
        "id": run_id,
        "trace_id": trace_id,
        "agent_name": agent_name,
        "user_id": user_id,
        "session_id": session_id,
        "environment": environment,
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
    }
    agent_run["metrics"] = compute_run_metrics(agent_run, spans)
    return agent_run


async def persist_otlp_spans(db: Any, body: bytes) -> int:
    spans = [enrich_span(s) for s in _parse_export_request(body)]
    if not spans:
        return 0

    traces: dict[str, list[dict[str, Any]]] = {}
    for span in spans:
        trace_id = span.get("trace_id")
        if not trace_id:
            continue
        traces.setdefault(trace_id, []).append(span)

    stored = 0
    for trace_id, trace_spans in traces.items():
        agent_run = _derive_agent_run(trace_id, trace_spans)
        await db.execute(
            """
            INSERT INTO agent_runs (
                id, trace_id, agent_name, user_id, session_id, environment,
                status, started_at, ended_at, metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                ended_at = excluded.ended_at,
                metrics_json = excluded.metrics_json
            """,
            (
                agent_run["id"],
                agent_run["trace_id"],
                agent_run["agent_name"],
                agent_run["user_id"],
                agent_run["session_id"],
                agent_run["environment"],
                agent_run["status"],
                agent_run["started_at"],
                agent_run["ended_at"],
                json.dumps(agent_run.get("metrics")),
            ),
        )

        for span in trace_spans:
            span_id = span.get("span_id")
            if not span_id:
                continue
            attrs = span.get("attributes") or {}
            latency = span_latency_ms(span)
            await db.execute(
                """
                INSERT OR REPLACE INTO spans (
                    id, agent_run_id, span_id, parent_span_id, span_type, name,
                    status, started_at, ended_at, attributes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"span_{span_id}",
                    agent_run["id"],
                    span_id,
                    span.get("parent_span_id"),
                    span.get("span_type", "agent.step"),
                    span.get("name", "span"),
                    span.get("status", "ok"),
                    span.get("started_at"),
                    span.get("ended_at"),
                    json.dumps(attrs),
                ),
            )
            stored += 1

            span_type = span.get("span_type")
            if span_type == "llm.call":
                model = str(attrs.get("llm.model", "unknown"))
                input_tokens = attrs.get("llm.input_tokens")
                output_tokens = attrs.get("llm.output_tokens")
                if input_tokens is not None:
                    input_tokens = int(input_tokens)
                if output_tokens is not None:
                    output_tokens = int(output_tokens)
                cost = attrs.get("llm.cost_usd")
                if cost is None:
                    cost = estimate_cost_usd(model, input_tokens, output_tokens)
                await db.execute(
                    """
                    INSERT OR REPLACE INTO model_calls (
                        id, agent_run_id, span_id, provider, model,
                        input_tokens, output_tokens, cost_usd, latency_ms, started_at, ended_at, attributes_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"mc_{span_id}",
                        agent_run["id"],
                        span_id,
                        attrs.get("llm.provider", "unknown"),
                        model,
                        input_tokens,
                        output_tokens,
                        cost,
                        latency,
                        span.get("started_at"),
                        span.get("ended_at"),
                        json.dumps(attrs),
                    ),
                )
            elif span_type == "tool.call":
                await db.execute(
                    """
                    INSERT OR REPLACE INTO tool_calls (
                        id, agent_run_id, span_id, tool_name, tool_provider, status,
                        latency_ms, started_at, ended_at, arguments_json, result_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"tc_{span_id}",
                        agent_run["id"],
                        span_id,
                        attrs.get("tool.name", span.get("name", "tool")),
                        attrs.get("tool.provider"),
                        "error" if span.get("status") == "error" else "success",
                        latency,
                        span.get("started_at"),
                        span.get("ended_at"),
                        json.dumps({k: v for k, v in attrs.items() if k.startswith("tool.arguments.")}),
                        json.dumps({k: v for k, v in attrs.items() if k.startswith("tool.result.")}),
                    ),
                )

    await db.commit()
    return stored