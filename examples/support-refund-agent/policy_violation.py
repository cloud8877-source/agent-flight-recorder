"""Demo agent that triggers a policy violation (large refund without approval)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../packages/sdk-python/src"))

from agent_flight_recorder import recorder


def large_refund_without_approval(user_message: str) -> str:
    with recorder.agent_run(name="refund-agent", user_id="user_456") as run:
        with run.span("get_orders", "tool.call", attributes={"tool.name": "get_orders"}) as span:
            span.set_attribute("tool.result.count", 1)

        with run.span("refund_payment", "tool.call", attributes={"tool.name": "refund_payment"}) as span:
            span.set_attribute("tool.arguments.amount_usd", 749.99)

        with run.span("compose_reply", "llm.call", attributes={"llm.model": "gpt-4.1-mini"}) as span:
            span.set_attribute("llm.input_tokens", 60)
            span.set_attribute("llm.output_tokens", 40)
            span.set_attribute("llm.response", "Refund processed for user@example.com")

        return f"Processed large refund for: {user_message}"


def main() -> None:
    recorder.init(app_name="support-agent", environment=os.environ.get("AFR_ENVIRONMENT", "development"))
    result = large_refund_without_approval("Refund order #9912 immediately")
    print(result)


if __name__ == "__main__":
    main()