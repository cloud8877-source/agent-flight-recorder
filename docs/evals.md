# Evaluations

Structured assessments of agent outputs and traces — used for debugging, regression testing, and CI quality gates.

> Parent decision: [ADR-001](../adr/ADR-001-agent-flight-recorder.md)

Full strategy: [ADR-004](../adr/ADR-004-evaluation-regression.md) (stub).

## Eval Types

| Type | Description |
|------|-------------|
| **Rule-based** | Deterministic checks on trace structure and outputs |
| **LLM-as-judge** | Model-assisted quality scoring |
| **Tool correctness** | Validates tool selection, arguments, and preconditions |
| **Policy compliance** | Checks output and actions against policy rules |
| **Regression** | Runs a dataset of known failures against evaluators |
| **Human review** | Manual scoring workflow |

## YAML Configuration

### Tool Correctness

```yaml
name: refund_tool_correctness
type: tool_correctness
rules:
  - tool_name: refund_payment
    must_only_be_called_when:
      - order_status == "delivered"
      - refund_amount <= 500
      - user_is_order_owner == true
```

### Policy Compliance

```yaml
name: no_private_notes_leak
type: policy
rules:
  - output_must_not_contain:
      - customer_internal_notes
      - admin_comments
      - fraud_score
```

### Regression Suite

```yaml
name: refund_agent_regression
type: regression
dataset: production_refund_failures
pass_threshold: 0.9
evaluators:
  - refund_tool_correctness
  - no_private_notes_leak
  - final_answer_helpfulness
```

## Trace → Regression Test

Typical workflow (from [ADR-001 Section 23](../adr/ADR-001-agent-flight-recorder.md#23-example-user-flow)):

1. Find a failed production run (e.g., wrong order refunded)
2. Inspect timeline in the UI
3. Click **Create Regression Test**
4. Modify prompt or tool validation logic
5. Run [replay](replay.md) and confirm eval passes
6. Add test to CI via `afr test ./afr-tests/`

## CLI

```bash
# Run a single eval definition
afr eval run regression_refund_agent.yml

# Run all tests in a directory (CI)
afr test ./afr-tests/
```

CI should fail when an eval score drops below the configured `pass_threshold`.

## Eval on Production vs. Replay

| Source | When to use |
|--------|-------------|
| **Production trace** | Monitor live behavior, detect regressions in prod |
| **Replay result** | Safe iteration on prompt/model/tool changes before deploy |

Both produce `eval.run` events linked to the source `agent_run_id`.

## MVP Scope

- **Must have:** manual eval definition, trace-to-regression-test conversion
- **Should have:** JSON/YAML config, GitHub Actions example
- **Could have:** LLM-as-judge evals (see commercial boundary in [ADR-005](../adr/ADR-005-open-source-boundary.md))

## Related Docs

- [replay.md](replay.md) — replay modes that feed evals
- [policies.md](policies.md) — policy compliance evaluators
- [quickstart.md](quickstart.md) — capture traces to evaluate