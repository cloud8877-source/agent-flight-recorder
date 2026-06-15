from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any


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


async def create_exact_replay(db: Any, source_run_id: str, run_detail: dict[str, Any]) -> dict[str, Any]:
    snapshot = await build_snapshot(db, source_run_id, run_detail)
    snapshot_id = await save_snapshot(db, source_run_id, snapshot)

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
            "exact",
            "success",
            now,
            now,
            json.dumps({"spans": snapshot["spans"], "identical": True}),
        ),
    )
    await db.commit()

    return {
        "id": replay_id,
        "source_agent_run_id": source_run_id,
        "snapshot_id": snapshot_id,
        "mode": "exact",
        "status": "success",
        "created_at": now,
        "snapshot": snapshot,
        "result": {"spans": snapshot["spans"], "identical": True},
    }


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