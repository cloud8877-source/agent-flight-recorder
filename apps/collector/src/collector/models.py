from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRunIn(BaseModel):
    id: str
    trace_id: str
    agent_name: str
    agent_version: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    environment: str
    status: str = "running"
    started_at: str
    ended_at: str | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None


class SpanIn(BaseModel):
    id: str
    agent_run_id: str
    span_id: str
    parent_span_id: str | None = None
    span_type: str
    name: str
    status: str = "ok"
    started_at: str
    ended_at: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class TraceBatchIn(BaseModel):
    agent_run: AgentRunIn | None = None
    spans: list[SpanIn] = Field(default_factory=list)


class EvalRunIn(BaseModel):
    agent_run_id: str
    eval_yaml: str | None = None
    eval_name: str | None = None


class ReplayCreateIn(BaseModel):
    source_agent_run_id: str
    mode: str = "exact"