# ADR-004: Evaluation and Regression Testing Strategy

## Status

Accepted (Phase 1 scope)

## Date

2026-06-15

## Owner

Agent Flight Recorder contributors

## Related Decisions

- [ADR-001: Build an OpenTelemetry-Native Agent Flight Recorder](ADR-001-agent-flight-recorder.md)

## Context

Agent Flight Recorder differentiates on the reliability loop: production trace → investigation → replay → eval → regression test → CI gate. Evaluations must work on both replayed and live production traces.

ADR-001 defines replay as a first-class capability with five modes (exact, prompt, model, tool, retrieval) that feed into the eval engine.

## Decision

Phase 1 delivers a **minimal eval runner** and **trace-to-regression-test export** suitable for local development and scripted CI.

### Evaluator types (Phase 1)

| Type | Status | Description |
|------|--------|-------------|
| `tool_correctness` | Implemented | Rule-based checks on tool call names and span attributes |
| Rule-based (general) | Partial | Condition syntax `field == value` on tool span attributes |
| LLM-as-judge | Deferred | Phase 2+ |
| Policy compliance | Deferred | Phase 3 |

### APIs

- `POST /v1/evals/run` — run eval against a stored `agent_run_id`; persists result to `eval_results`.
- `GET /v1/runs/{id}/regression-test` — export YAML regression suite derived from a trace.

Default eval fixture: `examples/evals/refund_tool_correctness.yml`. Example regression export: `examples/afr-tests/refund_agent_regression.yml`.

### Tool correctness rules

```yaml
rules:
  - tool_name: refund_payment
    must_only_be_called_when:
      - tool.arguments.amount_usd == 49.99
```

Conditions match against span attributes (`tool.arguments.*`, `tool.result.*`) and `tool_calls` table entries.

### Regression test format

Exported YAML includes `name`, `type: regression`, `source_run_id`, `trace_id`, `pass_threshold`, and nested `evaluators` with tool rules scaffolded from observed tool calls.

### CI integration

`make e2e` (`scripts/e2e.sh`) exercises the full Phase 1 loop: demo agent → ingest → search → replay → eval → regression export.

### Scoring

- `tool_correctness`: score `1.0` if all rules pass, else `0.0`.
- `passed`: boolean; eval fails if any rule condition is unmet.

## Consequences

**Positive**

- Developers can turn a captured trace into a regression artifact without manual YAML authoring.
- Eval results are stored alongside runs for audit.

**Deferred**

- `afr` CLI and GitHub Actions gate (Phase 2).
- Live replay comparison against original trace (Phase 2).
- Dataset management and eval suites spanning multiple runs.

> See [docs/evals.md](../docs/evals.md) for usage examples.