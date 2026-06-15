# LangGraph refund agent example

Demonstrates tracing LangGraph-style node functions with `trace_node` and `bind_run`.

The graph runs sequentially without requiring LangGraph installed. To use with a real
`StateGraph`, pass the bound state into each node:

```python
state = bind_run(initial_state, run)
state = graph.invoke(state)
```

Run:

```bash
AFR_ENDPOINT=http://localhost:4318 python examples/langgraph-refund-agent/main.py
```