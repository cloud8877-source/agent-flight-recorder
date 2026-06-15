from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class RecorderConfig:
    app_name: str
    environment: str
    endpoint: str
    api_key: str | None
    capture_mode: str
    capture_prompts: bool
    capture_responses: bool
    redaction_mode: str


_config: RecorderConfig | None = None


def load_from_env(app_name: str, environment: str) -> RecorderConfig:
    capture_mode = os.environ.get("AFR_CAPTURE_MODE", "redacted")
    return RecorderConfig(
        app_name=app_name,
        environment=environment,
        endpoint=os.environ.get("AFR_ENDPOINT", "http://localhost:4318").rstrip("/"),
        api_key=os.environ.get("AFR_API_KEY"),
        capture_mode=capture_mode,
        capture_prompts=os.environ.get("AFR_CAPTURE_PROMPTS", "true").lower() == "true",
        capture_responses=os.environ.get("AFR_CAPTURE_RESPONSES", "true").lower() == "true",
        redaction_mode=os.environ.get("AFR_REDACTION_MODE", "strict"),
    )


def get_config() -> RecorderConfig:
    if _config is None:
        raise RuntimeError("recorder.init() must be called before using the SDK")
    return _config


def set_config(config: RecorderConfig) -> None:
    global _config
    _config = config