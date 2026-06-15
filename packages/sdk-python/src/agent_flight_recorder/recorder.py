from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generator

from opentelemetry import context, trace
from opentelemetry.trace import Status, StatusCode

from agent_flight_recorder.attributes import (
    AFR_AGENT_NAME,
    AFR_APP_NAME,
    AFR_ENVIRONMENT,
    AFR_RUN_ID,
    AFR_SESSION_ID,
    AFR_SPAN_TYPE,
)
from agent_flight_recorder.config import get_config, load_from_env, set_config
from agent_flight_recorder.telemetry import force_flush, get_tracer, setup_telemetry


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
    setup_telemetry(config)


@dataclass
class AgentRun:
    id: str
    trace_id: str | None
    name: str
    user_id: str | None
    session_id: str | None

    def span(
        self,
        name: str,
        span_type: str,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> "SpanRecorder":
        return SpanRecorder(
            run=self,
            name=name,
            span_type=span_type,
            attributes=attributes or {},
        )


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
        self._span: trace.Span | None = None
        self._token: object | None = None

    def set_attribute(self, key: str, value: Any) -> None:
        if self._span is not None:
            self._span.set_attribute(key, value)

    def set_error(self, error: BaseException) -> None:
        if self._span is not None:
            self._span.record_exception(error)
            self._span.set_status(Status(StatusCode.ERROR, str(error)))

    def __enter__(self) -> "SpanRecorder":
        config = get_config()
        attrs: dict[str, Any] = {
            AFR_SPAN_TYPE: self.span_type,
            AFR_RUN_ID: self.run.id,
            AFR_AGENT_NAME: self.run.name,
            AFR_APP_NAME: config.app_name,
            AFR_ENVIRONMENT: config.environment,
        }
        if self.run.user_id:
            attrs["enduser.id"] = self.run.user_id
        if self.run.session_id:
            attrs[AFR_SESSION_ID] = self.run.session_id
        attrs.update(self.attributes)

        tracer = get_tracer()
        self._span = tracer.start_span(self.name, attributes=attrs)
        ctx = trace.set_span_in_context(self._span)
        self._token = context.attach(ctx)
        return self

    def __exit__(self, exc_type, exc, _tb) -> None:
        if self._span is not None:
            if exc is not None and isinstance(exc, BaseException):
                self.set_error(exc)
            self._span.end()
        if self._token is not None:
            context.detach(self._token)


@contextmanager
def agent_run(
    name: str,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
) -> Generator[AgentRun, None, None]:
    config = get_config()
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    tracer = get_tracer()

    root_attrs: dict[str, Any] = {
        AFR_SPAN_TYPE: "agent.run",
        AFR_RUN_ID: run_id,
        AFR_AGENT_NAME: name,
        AFR_APP_NAME: config.app_name,
        AFR_ENVIRONMENT: config.environment,
    }
    if user_id:
        root_attrs["enduser.id"] = user_id
    if session_id:
        root_attrs[AFR_SESSION_ID] = session_id

    with tracer.start_as_current_span(name, attributes=root_attrs) as root:
        ctx_span = trace.get_current_span()
        span_ctx = ctx_span.get_span_context()
        trace_id = format(span_ctx.trace_id, "032x") if span_ctx.is_valid else None

        run = AgentRun(
            id=run_id,
            trace_id=trace_id,
            name=name,
            user_id=user_id,
            session_id=session_id,
        )
        try:
            yield run
            root.set_status(Status(StatusCode.OK))
        except BaseException as exc:
            root.record_exception(exc)
            root.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
        finally:
            force_flush()