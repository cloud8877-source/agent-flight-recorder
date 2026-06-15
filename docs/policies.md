# Policies

Detect risky, forbidden, or non-compliant agent behavior at capture time and during replay.

> Parent decision: [ADR-001](../adr/ADR-001-agent-flight-recorder.md)

Privacy and redaction details: [ADR-003](../adr/ADR-003-redaction-privacy.md).

## Policy Result Types

```text
allow
warn
block
require_approval
```

## What the Policy Engine Detects

- Forbidden tool calls
- Risky tool calls (e.g., financial writes, external email)
- Missing human approval when required
- PII and secret leakage in outputs
- Prompt injection indicators
- Excessive tool loops
- Excessive cost or latency
- Unauthorized environment access
- Suspicious MCP tool usage

## Example Policy

```yaml
name: require_approval_for_large_refunds
description: Refunds above 500 USD require human approval.
scope:
  agents:
    - refund-agent
rules:
  - when:
      tool_name: refund_payment
      arguments:
        amount_usd:
          greater_than: 500
    then:
      action: require_approval
      severity: high
```

## Human Approval Events

When `require_approval` fires, the SDK records:

```text
human.approval.requested
human.approval.granted
human.approval.denied
```

Tool calls include approval metadata:

```json
{
  "approval": {
    "required": true,
    "status": "approved",
    "approved_by": "manager_123"
  }
}
```

## Capture Modes and Privacy

Policies interact with what data is available for checks. Three capture modes:

| Mode | Use |
|------|-----|
| `metadata_only` | Production high-security; policy checks on tool names/status only |
| `redacted` | **Default for production** — full structure with sensitive values redacted |
| `full` | Development only; complete payloads |

Default production configuration:

```yaml
capture_mode: redacted
redaction_mode: strict
```

Redaction patterns (email mask, credit card remove, API key remove, custom regex hash) are defined in [ADR-003](../adr/ADR-003-redaction-privacy.md).

## UI

The Policy screen shows:

- Active policies and scope
- Violations by severity
- Blocked actions and pending approvals
- Links to affected agent runs in the trace viewer

## MVP Scope

- **Should have:** basic policy checks, policy violation UI
- **Could have:** advanced PII detection, MCP-specific governance, enterprise policy packs ([ADR-005](../adr/ADR-005-open-source-boundary.md))

## Loading policies

Policies in `examples/policies/` are seeded on collector startup. Load or update via API or CLI:

```bash
afr policy load examples/policies/require_approval_for_large_refunds.yml
afr policy list
afr policy check <run_id>   # exits 1 when violations exist
```

Trigger a violation locally:

```bash
make collector
AFR_ENDPOINT=http://localhost:4318 python examples/support-refund-agent/policy_violation.py
```

## Phase 3 Exit Criteria

- [x] Developer can define a policy in YAML
- [x] System detects a risky or forbidden tool call
- [x] UI clearly shows policy violations (`/policies`, run detail banner)

## Related Docs

- [evals.md](evals.md) — policy compliance evaluators
- [replay.md](replay.md) — replay with mocked tools under policy constraints
- [architecture.md](architecture.md) — policy engine in system context