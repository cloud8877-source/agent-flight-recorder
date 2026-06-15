from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from collector.redaction import API_KEY_RE, BEARER_RE, CREDIT_CARD_RE, EMAIL_RE, PHONE_RE
from collector.risk import classify_tool_risk, max_severity

PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", EMAIL_RE),
    ("phone", PHONE_RE),
    ("credit_card", CREDIT_CARD_RE),
    ("api_key", API_KEY_RE),
    ("bearer_token", BEARER_RE),
]


def load_policy_yaml(content: str) -> dict[str, Any]:
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ValueError("policy YAML must be a mapping")
    return data


def detect_pii_in_text(text: str) -> list[str]:
    hits: list[str] = []
    for name, pattern in PII_PATTERNS:
        if pattern.search(text):
            hits.append(name)
    return hits


def _tool_argument(attrs: dict[str, Any], field: str) -> Any:
    key = field if field.startswith("tool.arguments.") else f"tool.arguments.{field}"
    return attrs.get(key, attrs.get(field))


def _compare_numeric(actual: Any, op: str, expected: Any) -> bool:
    try:
        actual_num = float(actual)
        expected_num = float(expected)
    except (TypeError, ValueError):
        return False
    if op == "greater_than":
        return actual_num > expected_num
    if op == "greater_than_or_equal":
        return actual_num >= expected_num
    if op == "less_than":
        return actual_num < expected_num
    if op == "equals":
        return actual_num == expected_num
    return False


def _rule_matches(
    rule: dict[str, Any],
    *,
    agent_name: str,
    span: dict[str, Any],
    attrs: dict[str, Any],
) -> bool:
    when = rule.get("when") or {}
    scope_agents = (rule.get("scope") or {}).get("agents")
    if scope_agents and agent_name not in scope_agents:
        return False

    tool_name = when.get("tool_name")
    if tool_name and attrs.get("tool.name") != tool_name and span.get("name") != tool_name:
        return False

    span_type = when.get("span_type")
    if span_type and span.get("span_type") != span_type:
        return False

    arguments = when.get("arguments") or {}
    for field, constraint in arguments.items():
        if not isinstance(constraint, dict):
            continue
        actual = _tool_argument(attrs, field)
        matched = False
        for op, expected in constraint.items():
            if _compare_numeric(actual, op, expected):
                matched = True
                break
        if not matched:
            return False

    if when.get("output_contains_pii"):
        text_parts: list[str] = []
        for key in ("llm.response", "llm.prompt", "tool.result"):
            value = attrs.get(key)
            if isinstance(value, str):
                text_parts.append(value)
        for key, value in attrs.items():
            if key.startswith("tool.result.") and isinstance(value, str):
                text_parts.append(value)
        if not any(detect_pii_in_text(part) for part in text_parts):
            return False

    forbidden_tools = when.get("forbidden_tools") or []
    current_tool = attrs.get("tool.name") or span.get("name")
    if forbidden_tools and current_tool in forbidden_tools:
        return True

    if tool_name or span_type or arguments or when.get("output_contains_pii"):
        return True
    return False


def _approval_status(attrs: dict[str, Any]) -> str | None:
    approval = attrs.get("approval.status") or attrs.get("tool.approval.status")
    if approval:
        return str(approval)
    nested = attrs.get("approval")
    if isinstance(nested, dict) and nested.get("status"):
        return str(nested["status"])
    return None


def evaluate_policies(
    policies: list[dict[str, Any]],
    *,
    agent_run: dict[str, Any],
    spans: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    violations: list[dict[str, Any]] = []
    approvals: list[dict[str, Any]] = []
    tool_risk: dict[str, str] = {}

    agent_name = agent_run.get("agent_name", "")

    for span in spans:
        attrs = span.get("attributes") or {}
        span_type = span.get("span_type")
        span_id = span.get("span_id")

        if span_type == "human.approval":
            event_type = str(attrs.get("approval.event", "requested"))
            approvals.append(
                {
                    "span_id": span_id,
                    "tool_name": attrs.get("tool.name"),
                    "event_type": event_type.replace("human.approval.", ""),
                    "status": attrs.get("approval.status"),
                    "approved_by": attrs.get("approval.approved_by"),
                    "details": attrs,
                }
            )
            continue

        if span_type != "tool.call":
            if span_type == "llm.call":
                for policy in policies:
                    if not policy.get("enabled", True):
                        continue
                    policy_scope = policy.get("scope") or {}
                    if policy_scope.get("agents") and agent_name not in policy_scope["agents"]:
                        continue
                    for rule in policy.get("rules") or []:
                        if not _rule_matches(rule, agent_name=agent_name, span=span, attrs=attrs):
                            continue
                        when = rule.get("when") or {}
                        if not when.get("output_contains_pii"):
                            continue
                        then = rule.get("then") or {}
                        hits = detect_pii_in_text(str(attrs.get("llm.response", "")))
                        violations.append(
                            _violation(
                                policy_name=policy.get("name", "policy"),
                                rule_name=rule.get("name"),
                                action=then.get("action", "warn"),
                                severity=then.get("severity", "medium"),
                                tool_name=None,
                                span_id=span_id,
                                message=f"PII detected in model output: {', '.join(hits)}",
                                details={"pii_types": hits},
                            )
                        )
            continue

        tool_name = str(attrs.get("tool.name") or span.get("name") or "tool")
        tool_risk[span_id or tool_name] = classify_tool_risk(tool_name)

        for policy in policies:
            if not policy.get("enabled", True):
                continue
            policy_scope = policy.get("scope") or {}
            if policy_scope.get("agents") and agent_name not in policy_scope["agents"]:
                continue

            for rule in policy.get("rules") or []:
                if not _rule_matches(rule, agent_name=agent_name, span=span, attrs=attrs):
                    continue
                then = rule.get("then") or {}
                action = then.get("action", "warn")
                severity = then.get("severity", tool_risk[span_id or tool_name])

                if action == "require_approval":
                    status = _approval_status(attrs)
                    if status in {"approved", "granted"}:
                        continue
                    if status == "denied":
                        violations.append(
                            _violation(
                                policy_name=policy.get("name", "policy"),
                                rule_name=rule.get("name"),
                                action="block",
                                severity=severity,
                                tool_name=tool_name,
                                span_id=span_id,
                                message=f"{tool_name} denied by human approval",
                                details={"approval_status": status},
                            )
                        )
                        continue
                    violations.append(
                        _violation(
                            policy_name=policy.get("name", "policy"),
                            rule_name=rule.get("name"),
                            action=action,
                            severity=severity,
                            tool_name=tool_name,
                            span_id=span_id,
                            message=f"{tool_name} requires human approval",
                            details={"approval_status": status or "missing"},
                        )
                    )
                    continue

                message = then.get("message") or f"Policy rule triggered for {tool_name}"
                violations.append(
                    _violation(
                        policy_name=policy.get("name", "policy"),
                        rule_name=rule.get("name"),
                        action=action,
                        severity=severity,
                        tool_name=tool_name,
                        span_id=span_id,
                        message=message,
                        details={"tool_arguments": {k: v for k, v in attrs.items() if k.startswith("tool.arguments.")}},
                    )
                )

    return violations, approvals, tool_risk


def _violation(
    *,
    policy_name: str,
    rule_name: str | None,
    action: str,
    severity: str,
    tool_name: str | None,
    span_id: str | None,
    message: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": f"viol_{uuid.uuid4().hex[:12]}",
        "policy_name": policy_name,
        "rule_name": rule_name,
        "action": action,
        "severity": severity,
        "tool_name": tool_name,
        "span_id": span_id,
        "message": message,
        "details": details,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def load_policies_from_db(db: Any) -> list[dict[str, Any]]:
    cursor = await db.execute(
        "SELECT id, name, description, policy_yaml, enabled FROM policies WHERE enabled = 1"
    )
    rows = await cursor.fetchall()
    policies: list[dict[str, Any]] = []
    for row in rows:
        policy = load_policy_yaml(row["policy_yaml"])
        policy["id"] = row["id"]
        policy["enabled"] = bool(row["enabled"])
        if "name" not in policy:
            policy["name"] = row["name"]
        policies.append(policy)
    return policies


async def seed_default_policies(db: Any, policies_dir: Path) -> None:
    if not policies_dir.is_dir():
        return
    for path in sorted(policies_dir.glob("*.yml")):
        content = path.read_text(encoding="utf-8")
        policy = load_policy_yaml(content)
        name = policy.get("name", path.stem)
        cursor = await db.execute("SELECT id FROM policies WHERE name = ?", (name,))
        if await cursor.fetchone():
            continue
        policy_id = f"pol_{uuid.uuid4().hex[:12]}"
        await db.execute(
            """
            INSERT INTO policies (id, name, description, policy_yaml, enabled, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (
                policy_id,
                name,
                policy.get("description"),
                content,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    await db.commit()


async def upsert_policy(db: Any, content: str) -> dict[str, Any]:
    policy = load_policy_yaml(content)
    name = policy.get("name")
    if not name:
        raise ValueError("policy requires name")

    cursor = await db.execute("SELECT id FROM policies WHERE name = ?", (name,))
    existing = await cursor.fetchone()
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        await db.execute(
            """
            UPDATE policies SET description = ?, policy_yaml = ?, enabled = 1
            WHERE id = ?
            """,
            (policy.get("description"), content, existing["id"]),
        )
        policy_id = existing["id"]
    else:
        policy_id = f"pol_{uuid.uuid4().hex[:12]}"
        await db.execute(
            """
            INSERT INTO policies (id, name, description, policy_yaml, enabled, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (policy_id, name, policy.get("description"), content, now),
        )
    await db.commit()
    return {"id": policy_id, "name": name, "description": policy.get("description")}


async def persist_policy_results(
    db: Any,
    agent_run_id: str,
    violations: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    tool_risk: dict[str, str],
) -> None:
    await db.execute("DELETE FROM policy_violations WHERE agent_run_id = ?", (agent_run_id,))
    await db.execute("DELETE FROM approval_events WHERE agent_run_id = ?", (agent_run_id,))

    for violation in violations:
        await db.execute(
            """
            INSERT INTO policy_violations (
                id, agent_run_id, policy_name, rule_name, action, severity,
                tool_name, span_id, message, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                violation["id"],
                agent_run_id,
                violation["policy_name"],
                violation.get("rule_name"),
                violation["action"],
                violation["severity"],
                violation.get("tool_name"),
                violation.get("span_id"),
                violation["message"],
                json.dumps(violation.get("details") or {}),
                violation["created_at"],
            ),
        )

    for approval in approvals:
        await db.execute(
            """
            INSERT INTO approval_events (
                id, agent_run_id, span_id, tool_name, event_type, status,
                approved_by, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"appr_{uuid.uuid4().hex[:12]}",
                agent_run_id,
                approval.get("span_id"),
                approval.get("tool_name"),
                approval.get("event_type", "requested"),
                approval.get("status"),
                approval.get("approved_by"),
                json.dumps(approval.get("details") or {}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    for span_id, risk_level in tool_risk.items():
        await db.execute(
            "UPDATE tool_calls SET risk_level = ? WHERE agent_run_id = ? AND span_id = ?",
            (risk_level, agent_run_id, span_id),
        )

    violation_count = len(violations)
    max_risk = max_severity(*(tool_risk.values() or ["low"]))
    run_status = "failed" if any(v["action"] in {"block", "require_approval"} for v in violations) else None

    cursor = await db.execute("SELECT metrics_json FROM agent_runs WHERE id = ?", (agent_run_id,))
    row = await cursor.fetchone()
    metrics = json.loads(row["metrics_json"] or "{}") if row else {}
    metrics["risk"] = {
        "max_risk_level": max_risk,
        "policy_violations": violation_count,
    }
    if run_status:
        await db.execute(
            "UPDATE agent_runs SET metrics_json = ?, status = ? WHERE id = ?",
            (json.dumps(metrics), run_status, agent_run_id),
        )
    else:
        await db.execute(
            "UPDATE agent_runs SET metrics_json = ? WHERE id = ?",
            (json.dumps(metrics), agent_run_id),
        )

async def evaluate_run_policies(db: Any, agent_run_id: str, run_detail: dict[str, Any]) -> dict[str, Any]:
    policies = await load_policies_from_db(db)
    violations, approvals, tool_risk = evaluate_policies(
        policies,
        agent_run=run_detail,
        spans=run_detail.get("spans", []),
    )
    await persist_policy_results(db, agent_run_id, violations, approvals, tool_risk)
    await db.commit()
    return {
        "violations": violations,
        "approvals": approvals,
        "tool_risk": tool_risk,
        "violation_count": len(violations),
    }