from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from agent_flight_recorder.recorder import AgentRun

StateT = TypeVar("StateT")
NodeFn = Callable[[StateT], StateT]

AFR_RUN_KEY = "__afr_run__"


def bind_run(state: dict[str, Any], run: AgentRun) -> dict[str, Any]:
    """Attach the active AgentRun to LangGraph state for downstream nodes."""
    merged = dict(state)
    merged[AFR_RUN_KEY] = run
    return merged


def _run_from_state(state: StateT, run: AgentRun | None) -> AgentRun:
    if run is not None:
        return run
    if isinstance(state, dict) and AFR_RUN_KEY in state:
        bound = state[AFR_RUN_KEY]
        if isinstance(bound, AgentRun):
            return bound
    raise RuntimeError("LangGraph node tracing requires an AgentRun via bind_run() or trace_node(run=...)")


def trace_node(
    name: str,
    span_type: str = "agent.step",
    *,
    run: AgentRun | None = None,
    attributes: dict[str, Any] | None = None,
) -> Callable[[NodeFn[StateT]], NodeFn[StateT]]:
    """Wrap a LangGraph node so each invocation emits an AFR span."""

    def decorator(fn: NodeFn[StateT]) -> NodeFn[StateT]:
        def wrapped(state: StateT, *args: Any, **kwargs: Any) -> StateT:
            active_run = _run_from_state(state, run)
            attrs = dict(attributes or {})
            attrs.setdefault("graph.node", name)
            with active_run.span(name, span_type, attributes=attrs):
                return fn(state, *args, **kwargs)

        return wrapped

    return decorator