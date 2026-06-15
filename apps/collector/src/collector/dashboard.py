from __future__ import annotations

import json
from typing import Any


def _metrics_from_row(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("metrics_json")
    if not raw:
        return {}
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return dict(raw) if isinstance(raw, dict) else {}


async def build_dashboard(db: Any, *, window: int = 200) -> dict[str, Any]:
    cursor = await db.execute(
        """
        SELECT id, agent_name, status, environment, started_at, metrics_json
        FROM agent_runs
        ORDER BY started_at DESC
        LIMIT ?
        """,
        (window,),
    )
    runs = [dict(row) for row in await cursor.fetchall()]

    total_runs = len(runs)
    failed_runs = sum(1 for run in runs if run.get("status") == "failed")
    success_runs = sum(1 for run in runs if run.get("status") == "success")

    latencies: list[float] = []
    costs: list[float] = []
    input_tokens = 0
    output_tokens = 0
    agent_costs: dict[str, float] = {}
    agent_counts: dict[str, int] = {}

    for run in runs:
        metrics = _metrics_from_row(run)
        if metrics.get("latency_ms") is not None:
            latencies.append(float(metrics["latency_ms"]))
        if metrics.get("cost_usd") is not None:
            cost = float(metrics["cost_usd"])
            costs.append(cost)
            name = str(run.get("agent_name") or "unknown")
            agent_costs[name] = agent_costs.get(name, 0.0) + cost
        input_tokens += int(metrics.get("input_tokens") or 0)
        output_tokens += int(metrics.get("output_tokens") or 0)
        name = str(run.get("agent_name") or "unknown")
        agent_counts[name] = agent_counts.get(name, 0) + 1

    cursor = await db.execute("SELECT COUNT(*) AS c FROM policy_violations")
    violation_row = await cursor.fetchone()
    total_violations = int(violation_row["c"] if violation_row else 0)

    cursor = await db.execute(
        """
        SELECT v.id, v.agent_run_id, v.policy_name, v.rule_name, v.action, v.severity,
               v.tool_name, v.message, v.created_at, r.agent_name
        FROM policy_violations v
        JOIN agent_runs r ON r.id = v.agent_run_id
        ORDER BY v.created_at DESC
        LIMIT 10
        """
    )
    recent_violations = [dict(row) for row in await cursor.fetchall()]

    cursor = await db.execute(
        """
        SELECT tool_name, COUNT(*) AS failures
        FROM tool_calls
        WHERE status = 'error'
        GROUP BY tool_name
        ORDER BY failures DESC
        LIMIT 5
        """
    )
    failed_tools = [
        {"tool_name": row["tool_name"], "failures": int(row["failures"])}
        for row in await cursor.fetchall()
    ]

    if agent_costs:
        ranked_costs = sorted(agent_costs.items(), key=lambda item: item[1], reverse=True)[:5]
        expensive_agents = [
            {"agent_name": name, "total_cost_usd": round(total, 6)}
            for name, total in ranked_costs
        ]
    else:
        ranked = sorted(agent_counts.items(), key=lambda item: item[1], reverse=True)[:5]
        expensive_agents = [
            {"agent_name": name, "run_count": count}
            for name, count in ranked
        ]

    failure_rate = round(failed_runs / total_runs, 4) if total_runs else 0.0
    violation_rate = round(total_violations / total_runs, 4) if total_runs else 0.0

    return {
        "window": window,
        "total_runs": total_runs,
        "success_runs": success_runs,
        "failed_runs": failed_runs,
        "failure_rate": failure_rate,
        "policy_violations": total_violations,
        "violation_rate": violation_rate,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "avg_cost_usd": round(sum(costs) / len(costs), 6) if costs else None,
        "total_input_tokens": input_tokens,
        "total_output_tokens": output_tokens,
        "expensive_agents": expensive_agents,
        "failed_tools": failed_tools,
        "recent_violations": recent_violations,
    }