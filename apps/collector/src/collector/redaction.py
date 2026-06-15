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


def redact_string(value: str, mode: str = "strict") -> str:
    if mode != "strict":
        return value
    result = EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    result = PHONE_RE.sub("[REDACTED_PHONE]", result)
    result = CREDIT_CARD_RE.sub("[REDACTED_CARD]", result)
    result = API_KEY_RE.sub("[REDACTED_API_KEY]", result)
    return BEARER_RE.sub("Bearer [REDACTED_TOKEN]", result)


def redact_value(value: Any, mode: str = "strict") -> Any:
    if isinstance(value, str):
        return redact_string(value, mode)
    if isinstance(value, dict):
        return {k: redact_value(v, mode) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(v, mode) for v in value]
    return value


def redact_attributes(attrs: dict[str, Any]) -> dict[str, Any]:
    mode = os.environ.get("AFR_REDACTION_MODE", "strict")
    return redact_value(attrs, mode)