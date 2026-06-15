from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from collector.metrics import span_latency_ms


def _enabled() -> bool:
    return bool(os.environ.get("AFR_CLICKHOUSE_URL"))


def _base_url() -> str:
    return os.environ.get("AFR_CLICKHOUSE_URL", "").rstrip("/")


def _parse_iso(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _span_rows(agent_run: dict[str, Any], spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for span in spans:
        attrs = span.get("attributes") or {}
        row = {
            "trace_id": agent_run.get("trace_id"),
            "agent_run_id": agent_run.get("id"),
            "span_id": span.get("span_id"),
            "span_type": span.get("span_type"),
            "name": span.get("name"),
            "status": span.get("status"),
            "agent_name": agent_run.get("agent_name"),
            "environment": agent_run.get("environment"),
            "started_at": _parse_iso(span.get("started_at")),
            "ended_at": _parse_iso(span.get("ended_at")),
            "latency_ms": span_latency_ms(span),
            "input_tokens": attrs.get("llm.input_tokens"),
            "output_tokens": attrs.get("llm.output_tokens"),
            "cost_usd": attrs.get("llm.cost_usd"),
            "attributes": json.dumps(attrs, separators=(",", ":")),
        }
        if row["started_at"]:
            rows.append(row)
    return rows


async def write_span_events(agent_run: dict[str, Any], spans: list[dict[str, Any]]) -> int:
    if not _enabled():
        return 0

    rows = _span_rows(agent_run, spans)
    if not rows:
        return 0

    payload = "\n".join(json.dumps(row, separators=(",", ":")) for row in rows)
    query = "INSERT INTO span_events FORMAT JSONEachRow"
    url = f"{_base_url()}/?query={quote(query)}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            content=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
    return len(rows)


def write_span_events_background(agent_run: dict[str, Any], spans: list[dict[str, Any]]) -> None:
    if not _enabled():
        return
    asyncio.create_task(write_span_events(agent_run, spans))


async def count_span_events(trace_id: str | None = None) -> int:
    if not _enabled():
        return 0
    if trace_id:
        query = f"SELECT count() AS c FROM span_events WHERE trace_id = '{trace_id}'"
    else:
        query = "SELECT count() AS c FROM span_events"
    url = f"{_base_url()}/?query={quote(query + ' FORMAT JSON')}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
    return int(data["data"][0]["c"])