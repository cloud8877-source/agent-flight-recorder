"""LangGraph-style refund agent traced with Agent Flight Recorder."""

from __future__ import annotations

import os
import sys
from typing import TypedDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../packages/sdk-python/src"))

from agent_flight_recorder import recorder
from agent_flight_recorder.integrations.langgraph import bind_run, trace_node


class RefundState(TypedDict):
    message: str
    order_count: int
    refunded: bool
    reply: str


@trace_node("get_orders", "tool.call", attributes={"tool.name": "get_orders"})
def get_orders(state: RefundState) -> RefundState:
    next_state = dict(state)
    next_state["order_count"] = 2
    return next_state  # type: ignore[return-value]


@trace_node("refund_payment", "tool.call", attributes={"tool.name": "refund_payment"})
def refund_payment(state: RefundState) -> RefundState:
    next_state = dict(state)
    next_state["refunded"] = True
    return next_state  # type: ignore[return-value]


@trace_node("compose_reply", "llm.call", attributes={"llm.model": "gpt-4.1-mini"})
def compose_reply(state: RefundState) -> RefundState:
    next_state = dict(state)
    next_state["reply"] = f"Refunded order for: {state['message']}"
    return next_state  # type: ignore[return-value]


def run_refund_graph(user_message: str) -> str:
    with recorder.agent_run(name="langgraph-refund-agent", user_id="user_langgraph") as run:
        state = bind_run({"message": user_message, "order_count": 0, "refunded": False, "reply": ""}, run)
        state = get_orders(state)  # type: ignore[assignment]
        state = refund_payment(state)  # type: ignore[assignment]
        state = compose_reply(state)  # type: ignore[assignment]
        return state["reply"]


def main() -> None:
    recorder.init(
        app_name="langgraph-support-agent",
        environment=os.environ.get("AFR_ENVIRONMENT", "development"),
    )
    print(run_refund_graph("Refund my latest order"))


if __name__ == "__main__":
    main()