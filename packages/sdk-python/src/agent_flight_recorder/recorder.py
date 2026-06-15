from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generator

import httpx

from agent_flight_recorder.config import RecorderConfig, get_config, load_from_env, set_config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init(
    app_name: str,
    environment: str = "development",
    *,
    endpoint: str | None = None,
) -> None:
    config = load_from_env(app_name, environment)
    if endpoint is not None:
        config.endpoint = endpoint.rstrip("/")
    set_config(config)


@dataclass
class AgentRun:
    id: str
    trace_id: str
    name: str
    user_id: str | None
    session_id: str | None
    started_at: str
    _spans: list[dict[str, Any]] = field(default_factory=list)

    def span(
        self,
        name: str,
        span_type: str,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> "SpanRecorder":
        return SpanRecorder(self, name=name, span_type=span_type, attributes=attributes or {})

    def _flush(self, status: str, output: Any | None = None, error: BaseException | None = None) -> None:
        config = get_config()
        ended_at = _now()
        payload = {
            "agent_run": {
                "id": self.id,
                "trace_id": self.trace_id,
                "agent_name": self.name,
                "user_id": self.user_id,
                "session_id": self.session_id,
                "environment": config.environment,
                "status": status,
                "started_at": self.started_at,
                "ended_at": ended_at,
                "output": {"value": output} if output is not None else None,
                "metrics": {},
            },
            "spans": self._spans,
        }
        if error is not None:
            payload["agent_run"]["output"] = {"error": str(error)}

        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        with httpx.Client(timeout=10.0) as client:
            response = client.post(f"{config.endpoint}/v1/traces", json=payload, headers=headers)
            response.raise_for_status()


class SpanRecorder:
    def __init__(
        self,
        run: AgentRun,
        *,
        name: str,
        span_type: str,
        attributes: dict[str, Any],
    ) -> None:
        self.run = run
        self.name = name
        self.span_type = span_type
        self.attributes = attributes
        self.span_id = uuid.uuid4().hex[:16]
        self.started_at = _now()
        self.status = "ok"

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_error(self, error: BaseException) -> None:
        self.status = "error"
        self.attributes["error.message"] = str(error)

    def end(self) -> None:
        self.run._spans.append(
            {
                "id": uuid.uuid4().hex,
                "agent_run_id": self.run.id,
                "span_id": self.span_id,
                "parent_span_id": None,
                "span_type": self.span_type,
                "name": self.name,
                "status": self.status,
                "started_at": self.started_at,
                "ended_at": _now(),
                "attributes": self.attributes,
            }
        )

    def __enter__(self) -> "SpanRecorder":
        return self

    def __exit__(self, exc_type, exc, _tb) -> None:
        if exc is not None and isinstance(exc, BaseException):
            self.set_error(exc)
        self.end()


@contextmanager
def agent_run(
    name: str,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
) -> Generator[AgentRun, None, None]:
    run = AgentRun(
        id=f"run_{uuid.uuid4().hex[:12]}",
        trace_id=f"trace_{uuid.uuid4().hex[:16]}",
        name=name,
        user_id=user_id,
        session_id=session_id,
        started_at=_now(),
    )
    root = run.span(name, "agent.run", attributes={"afr.app_name": get_config().app_name})
    root.__enter__()
    try:
        yield run
        root.__exit__(None, None, None)
        run._flush("success")
    except BaseException as exc:
        root.__exit__(type(exc), exc, exc.__traceback__)
        run._flush("failed", error=exc)
        raise