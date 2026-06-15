from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from collector.metrics import compute_run_metrics, estimate_cost_usd


async def build_snapshot(db: Any, run_id: str, run_detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": "1",
        "source_run_id": run_id,
        "trace_id": run_detail["trace_id"],
        "agent_name": run_detail["agent_name"],
        "environment": run_detail["environment"],
        "user_id": run_detail.get("user_id"),
        "started_at": run_detail["started_at"],
        "ended_at": run_detail.get("ended_at"),
        "spans": run_detail["spans"],
        "model_calls": run_detail.get("model_calls", []),
        "tool_calls": run_detail.get("tool_calls", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def save_snapshot(db: Any, run_id: str, snapshot: dict[str, Any]) -> str:
    snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
    await db.execute(
        """
        INSERT INTO replay_snapshots (id, agent_run_id, snapshot_json, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (snapshot_id, run_id, json.dumps(snapshot), datetime.now(timezone.utc).isoformat()),
    )
    await db.commit()
    return snapshot_id


def _apply_model_override(snapshot: dict[str, Any], model: str) -> tuple[dict[str, Any], dict[str, Any]]:
    replay_snapshot = copy.deepcopy(snapshot)
    changes: list[dict[str, Any]] = []

    for span in replay_snapshot.get("spans", []):
        if span.get("span_type") != "llm.call":
            continue
        attrs = dict(span.get("attributes") or {})
        previous = attrs.get("llm.model")
        if previous == model:
            continue
        attrs["llm.model"] = model
        input_tokens = attrs.get("llm.input_tokens")
        output_tokens = attrs.get("llm.output_tokens")
        if input_tokens is not None:
            input_tokens = int(input_tokens)
        if output_tokens is not None:
            output_tokens = int(output_tokens)
        cost = estimate_cost_usd(model, input_tokens, output_tokens)
        if cost is not None:
            attrs["llm.cost_usd"] = cost
        span["attributes"] = attrs
        changes.append({"span": span.get("name"), "field": "llm.model", "from": previous, "to": model})

    for call in replay_snapshot.get("model_calls", []):
        previous = call.get("model")
        if previous == model:
            continue
        call["model"] = model
        cost = estimate_cost_usd(
            model,
            call.get("input_tokens"),
            call.get("output_tokens"),
        )
        if cost is not None:
            call["cost_usd"] = cost

    metrics = compute_run_metrics(
        {
            "started_at": replay_snapshot.get("started_at"),
            "ended_at": replay_snapshot.get("ended_at"),
        },
        replay_snapshot.get("spans", []),
    )
    result = {
        "spans": replay_snapshot["spans"],
        "model_calls": replay_snapshot.get("model_calls", []),
        "metrics": metrics,
        "model_override": model,
        "changes": changes,
        "identical": len(changes) == 0,
    }
    return replay_snapshot, result


async def create_replay(
    db: Any,
    source_run_id: str,
    run_detail: dict[str, Any],
    *,
    mode: str = "exact",
    model: str | None = None,
) -> dict[str, Any]:
    snapshot = await build_snapshot(db, source_run_id, run_detail)
    snapshot_id = await save_snapshot(db, source_run_id, snapshot)

    if mode == "model":
        if not model:
            raise ValueError("model replay requires a model override")
        replay_snapshot, result = _apply_model_override(snapshot, model)
    else:
        replay_snapshot = snapshot
        result = {"spans": snapshot["spans"], "identical": True}

    replay_id = f"replay_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """
        INSERT INTO replay_runs (
            id, source_agent_run_id, snapshot_id, mode, status, created_at, completed_at, result_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            replay_id,
            source_run_id,
            snapshot_id,
            mode,
            "success",
            now,
            now,
            json.dumps(result),
        ),
    )
    await db.commit()

    return {
        "id": replay_id,
        "source_agent_run_id": source_run_id,
        "snapshot_id": snapshot_id,
        "mode": mode,
        "status": "success",
        "created_at": now,
        "snapshot": replay_snapshot,
        "result": result,
    }


async def create_exact_replay(db: Any, source_run_id: str, run_detail: dict[str, Any]) -> dict[str, Any]:
    return await create_replay(db, source_run_id, run_detail, mode="exact")


async def get_replay(db: Any, replay_id: str) -> dict[str, Any] | None:
    cursor = await db.execute("SELECT * FROM replay_runs WHERE id = ?", (replay_id,))
    row = await cursor.fetchone()
    if row is None:
        return None

    result = dict(row)
    result["result"] = json.loads(result.pop("result_json") or "{}")

    cursor = await db.execute(
        "SELECT snapshot_json FROM replay_snapshots WHERE id = ?",
        (result["snapshot_id"],),
    )
    snap = await cursor.fetchone()
    if snap:
        result["snapshot"] = json.loads(snap["snapshot_json"])

    cursor = await db.execute("SELECT * FROM agent_runs WHERE id = ?", (result["source_agent_run_id"],))
    source = await cursor.fetchone()
    if source:
        result["source_run"] = dict(source)

    return result