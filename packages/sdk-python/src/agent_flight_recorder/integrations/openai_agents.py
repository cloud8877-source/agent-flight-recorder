from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from agent_flight_recorder.recorder import AgentRun

T = TypeVar("T")
AsyncFn = Callable[..., Awaitable[T]]
SyncFn = Callable[..., T]


def trace_tool(
    run: AgentRun,
    tool_name: str,
    *,
    provider: str | None = None,
) -> Callable[[SyncFn[T]], SyncFn[T]]:
    """Wrap an OpenAI Agents SDK tool function with tool.call spans."""

    def decorator(fn: SyncFn[T]) -> SyncFn[T]:
        def wrapped(*args: Any, **kwargs: Any) -> T:
            attrs: dict[str, Any] = {"tool.name": tool_name}
            if provider:
                attrs["tool.provider"] = provider
            if args:
                attrs["tool.arguments.payload"] = str(args[0])[:500]
            with run.span(tool_name, "tool.call", attributes=attrs) as span:
                result = fn(*args, **kwargs)
                span.set_attribute("tool.result.preview", str(result)[:500])
                return result

        return wrapped

    return decorator


async def trace_agent_run(
    run: AgentRun,
    agent_name: str,
    execute: Callable[[], Awaitable[T]],
    *,
    model: str | None = None,
) -> T:
    """Execute an OpenAI Agents SDK runner inside agent + llm spans."""
    with run.span(agent_name, "agent.step", attributes={"agent.framework": "openai-agents"}):
        with run.span("model_turn", "llm.call", attributes={"llm.model": model or "unknown"}) as span:
            result = await execute()
            span.set_attribute("llm.output.preview", str(result)[:500])
            return result