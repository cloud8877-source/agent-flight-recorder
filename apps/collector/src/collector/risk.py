from __future__ import annotations

TOOL_RISK_LEVELS: dict[str, str] = {
    "delete_account": "critical",
    "transfer_funds": "critical",
    "refund_payment": "high",
    "send_email": "medium",
    "send_sms": "medium",
    "update_billing": "high",
    "get_orders": "low",
    "get_user_profile": "low",
    "search_knowledge_base": "low",
}

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def classify_tool_risk(tool_name: str) -> str:
    return TOOL_RISK_LEVELS.get(tool_name, "medium")


def max_severity(*levels: str) -> str:
    if not levels:
        return "low"
    return max(levels, key=lambda level: SEVERITY_ORDER.get(level, 0))