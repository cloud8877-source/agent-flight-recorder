# OpenAI Agents SDK example

Demonstrates wrapping tool functions and agent execution with AFR spans using
`trace_tool` and `trace_agent_run`. The example mirrors the OpenAI Agents SDK
pattern without requiring the SDK package.

Run:

```bash
AFR_ENDPOINT=http://localhost:4318 python examples/openai-agents-refund-agent/main.py
```