"""OpenAI Agents SDK-style refund agent traced with Agent Flight Recorder."""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../packages/sdk-python/src"))

from agent_flight_recorder import recorder
from agent_flight_recorder.integrations.openai_agents import trace_agent_run, trace_tool
from agent_flight_recorder.recorder import AgentRun


def build_tools(run: AgentRun):
    @trace_tool(run, "get_orders", provider="internal_api")
    def get_orders(_query: str) -> str:
        return "orders:2"

    @trace_tool(run, "refund_payment", provider="internal_api")
    def refund_payment(amount_usd: float) -> str:
        return f"refunded:{amount_usd}"

    return get_orders, refund_payment


async def run_agent(user_message: str) -> str:
    with recorder.agent_run(name="openai-agents-refund-agent", user_id="user_oai_agents") as run:
        get_orders, refund_payment = build_tools(run)

        async def execute() -> str:
            get_orders(user_message)
            refund_payment(49.99)
            return f"Refunded order for: {user_message}"

        return await trace_agent_run(run, "refund-agent", execute, model="gpt-4.1-mini")


def main() -> None:
    recorder.init(
        app_name="openai-agents-support",
        environment=os.environ.get("AFR_ENVIRONMENT", "development"),
    )
    print(asyncio.run(run_agent("Refund my latest order")))


if __name__ == "__main__":
    main()