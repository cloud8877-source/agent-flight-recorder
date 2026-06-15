# Framework integrations

Agent Flight Recorder ships lightweight helpers for popular agent frameworks. All integrations emit OpenTelemetry spans compatible with the collector.

## LangGraph

Use `bind_run` to attach the active `AgentRun` to graph state, and `trace_node` to wrap node functions:

```python
from agent_flight_recorder import recorder
from agent_flight_recorder.integrations.langgraph import bind_run, trace_node

@trace_node("get_orders", "tool.call", attributes={"tool.name": "get_orders"})
def get_orders(state):
    return {**state, "orders": 2}

with recorder.agent_run(name="refund-agent", user_id="user_123") as run:
    state = bind_run({"message": "Refund my order"}, run)
    state = get_orders(state)
```

Example: `examples/langgraph-refund-agent/main.py`

## OpenAI Agents SDK

Wrap tools and runner execution with `trace_tool` and `trace_agent_run`:

```python
from agent_flight_recorder.integrations.openai_agents import trace_agent_run, trace_tool

@trace_tool(run, "refund_payment")
def refund_payment(amount_usd: float) -> str:
    return "ok"

result = await trace_agent_run(run, "refund-agent", lambda: Runner.run(agent, input))
```

Example: `examples/openai-agents-refund-agent/main.py`

## Verify

```bash
make integration-test
```