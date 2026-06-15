from __future__ import annotations

import json
from typing import Any

import yaml


def load_eval_yaml(content: str) -> dict[str, Any]:
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ValueError("eval YAML must be a mapping")
    return data


def _tool_calls_by_name(run_detail: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for call in run_detail.get("tool_calls", []):
        grouped.setdefault(call["tool_name"], []).append(call)
    return grouped


def _span_tool_attrs(run_detail: dict[str, Any], tool_name: str) -> list[dict[str, Any]]:
    attrs_list: list[dict[str, Any]] = []
    for span in run_detail.get("spans", []):
        if span.get("span_type") != "tool.call":
            continue
        attrs = span.get("attributes") or {}
        if attrs.get("tool.name") == tool_name or span.get("name") == tool_name:
            attrs_list.append(attrs)
    return attrs_list


def run_tool_correctness(eval_def: dict[str, Any], run_detail: dict[str, Any]) -> dict[str, Any]:
    rules = eval_def.get("rules") or []
    failures: list[str] = []
    checks = 0

    for rule in rules:
        tool_name = rule.get("tool_name")
        if not tool_name:
            continue
        checks += 1
        calls = _tool_calls_by_name(run_detail).get(tool_name, [])
        if not calls and rule.get("must_only_be_called_when"):
            failures.append(f"{tool_name} was not called but rules expect conditional invocation")
            continue

        conditions = rule.get("must_only_be_called_when") or []
        for condition in conditions:
            if "==" not in condition:
                continue
            field, expected = [part.strip() for part in condition.split("==", 1)]
            expected = expected.strip().strip('"').strip("'")
            attrs_list = _span_tool_attrs(run_detail, tool_name)
            if not attrs_list:
                failures.append(f"{tool_name}: no attributes to check {field}")
                continue
            key = field
            if not key.startswith("tool."):
                key = f"tool.arguments.{field}"
            values = [str(attrs.get(key, attrs.get(field, ""))) for attrs in attrs_list]
            if not any(v == expected for v in values):
                failures.append(f"{tool_name}: expected {field}=={expected}, got {values}")

    passed = len(failures) == 0 and checks > 0
    score = 1.0 if passed else 0.0
    return {
        "evaluator_name": eval_def.get("name", "tool_correctness"),
        "eval_type": "tool_correctness",
        "score": score,
        "passed": passed,
        "failures": failures,
        "checks": checks,
    }


def run_eval(eval_def: dict[str, Any], run_detail: dict[str, Any]) -> dict[str, Any]:
    eval_type = eval_def.get("type", "tool_correctness")
    if eval_type == "tool_correctness":
        return run_tool_correctness(eval_def, run_detail)
    raise ValueError(f"unsupported eval type: {eval_type}")


def _agent_slug(agent_name: str) -> str:
    return agent_name.replace("-", "_")


def build_regression_test(run_detail: dict[str, Any]) -> dict[str, Any]:
    tool_names = sorted({call["tool_name"] for call in run_detail.get("tool_calls", [])})
    rules = []
    for name in tool_names:
        rules.append({"tool_name": name, "must_only_be_called_when": []})

    slug = _agent_slug(run_detail["agent_name"])
    return {
        "name": f"{slug}_regression",
        "type": "regression",
        "source_run_id": run_detail["id"],
        "trace_id": run_detail["trace_id"],
        "pass_threshold": 0.9,
        "evaluators": [
            {
                "name": f"{run_detail['agent_name']}_tool_correctness",
                "type": "tool_correctness",
                "rules": rules,
            }
        ],
    }