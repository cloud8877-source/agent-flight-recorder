"""Demo support refund agent — records a trace to the local collector."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../packages/sdk-python/src"))

from agent_flight_recorder import recorder


def fake_refund_agent(user_message: str) -> str:
    with recorder.agent_run(name="refund-agent", user_id="user_123") as run:
        with run.span("get_orders", "tool.call", attributes={"tool.name": "get_orders"}) as span:
            span.set_attribute("tool.result.count", 2)

        with run.span("refund_payment", "tool.call", attributes={"tool.name": "refund_payment"}) as span:
            span.set_attribute("tool.arguments.amount_usd", 49.99)

        with run.span("compose_reply", "llm.call", attributes={"llm.model": "gpt-4.1-mini"}) as span:
            span.set_attribute("llm.output_tokens", 120)

        return f"Refunded order for: {user_message}"


def main() -> None:
    recorder.init(app_name="support-agent", environment=os.environ.get("AFR_ENVIRONMENT", "development"))
    result = fake_refund_agent("Refund my latest order")
    print(result)


if __name__ == "__main__":
    main()