from __future__ import annotations

# USD per token (input, output) — rough estimates for Phase 1
MODEL_RATES: dict[str, tuple[float, float]] = {
    "gpt-4.1-mini": (0.00000015, 0.0000006),
    "gpt-4.1": (0.000002, 0.000008),
    "gpt-4o-mini": (0.00000015, 0.0000006),
    "claude-3-5-sonnet": (0.000003, 0.000015),
}


def estimate_llm_cost_usd(model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None and output_tokens is None:
        return None
    rates = MODEL_RATES.get(model)
    if rates is None:
        return None
    inp = input_tokens or 0
    out = output_tokens or 0
    return round(inp * rates[0] + out * rates[1], 6)