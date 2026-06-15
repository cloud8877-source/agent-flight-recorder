# ADR-004: Evaluation and Regression Testing Strategy

## Status

Proposed (stub)

## Date

2026-06-15

## Owner

<Your Name / Team>

## Related Decisions

- [ADR-001: Build an OpenTelemetry-Native Agent Flight Recorder](ADR-001-agent-flight-recorder.md)

## Context

Agent Flight Recorder differentiates on the reliability loop: production trace → investigation → replay → eval → regression test → CI gate. Evaluations must work on both replayed and live production traces.

ADR-001 defines replay as a first-class capability with five modes (exact, prompt, model, tool, retrieval) that feed into the eval engine.

## Decision

**TBD.** This ADR will formalize:

- Evaluator types and execution model
- Trace-to-regression-test conversion format
- Scoring, pass thresholds, and CI integration
- Relationship between replay results and eval results
- Dataset management for regression suites

### Provisional eval types (from ADR-001)

1. Rule-based evals
2. LLM-as-judge evals
3. Tool correctness evals
4. Policy compliance evals
5. Regression evals
6. Human review evals

### Example CLI (Phase 2)

```bash
afr replay run_123 --model gpt-4.1-mini
afr eval run regression_refund_agent.yml
afr test ./afr-tests/
```

### MVP scope

**Must have:** manual eval definition, convert trace into regression test

**Should have:** JSON/YAML eval configuration, GitHub Actions example for regression tests

**Could have:** LLM-as-judge evals, managed eval workers (commercial)

## Consequences

**TBD.** Expected topics:

- Non-determinism in LLM-as-judge evals and how to make CI reliable
- Versioning of eval definitions alongside agent/prompt changes
- Storage of eval results and linkage to source agent runs
- False positive/negative rates and developer trust in CI gates

## Exit Criteria (Phase 2)

- Developer can turn a production-like trace into a regression test
- CI can fail when an eval score drops below threshold

> See [ADR-001](ADR-001-agent-flight-recorder.md) for the overarching architecture. See also [docs/evals.md](../docs/evals.md) and [docs/replay.md](../docs/replay.md).