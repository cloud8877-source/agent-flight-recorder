from __future__ import annotations

import hashlib
import os
import re
from typing import Any

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_RE = re.compile(r"\b\+?\d[\d\s().-]{7,}\d\b")
CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
API_KEY_RE = re.compile(r"\b(?:sk|pk|rk|api)[-_][A-Za-z0-9]{16,}\b", re.IGNORECASE)
BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._-]+", re.IGNORECASE)

SENSITIVE_KEYS = frozenset(
    {
        "llm.prompt",
        "llm.response",
        "llm.system_prompt",
        "tool.arguments",
        "tool.result",
    }
)

SENSITIVE_PREFIXES = ("tool.arguments.", "tool.result.", "llm.prompt", "llm.response")


def _custom_patterns() -> list[re.Pattern[str]]:
    raw = os.environ.get("AFR_REDACTION_CUSTOM_REGEX", "")
    if not raw:
        return []
    return [re.compile(part.strip()) for part in raw.split(",") if part.strip()]


def _hash_value(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"hash:{digest}"


def redact_string(value: str, mode: str) -> str:
    if mode != "strict":
        return value

    result = EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    result = PHONE_RE.sub("[REDACTED_PHONE]", result)
    result = CREDIT_CARD_RE.sub("[REDACTED_CARD]", result)
    result = API_KEY_RE.sub("[REDACTED_API_KEY]", result)
    result = BEARER_RE.sub("Bearer [REDACTED_TOKEN]", result)

    for pattern in _custom_patterns():
        result = pattern.sub(_hash_value(result), result)

    return result


def redact_value(value: Any, mode: str) -> Any:
    if isinstance(value, str):
        return redact_string(value, mode)
    if isinstance(value, dict):
        return redact_dict(value, mode)
    if isinstance(value, list):
        return [redact_value(item, mode) for item in value]
    return value


def redact_dict(data: dict[str, Any], mode: str) -> dict[str, Any]:
    return {key: redact_value(val, mode) for key, val in data.items()}


def apply_capture_mode(attributes: dict[str, Any], capture_mode: str, redaction_mode: str) -> dict[str, Any]:
    if capture_mode == "metadata_only":
        return {
            k: v
            for k, v in attributes.items()
            if not k.startswith(SENSITIVE_PREFIXES) and k not in SENSITIVE_KEYS
        }
    if capture_mode == "full":
        return attributes
    return redact_dict(attributes, redaction_mode)