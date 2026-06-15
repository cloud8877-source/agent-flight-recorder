# ADR-003: Redaction and Privacy Model for Prompt/Response Logging

## Status

Proposed (stub)

## Date

2026-06-15

## Owner

<Your Name / Team>

## Related Decisions

- [ADR-001: Build an OpenTelemetry-Native Agent Flight Recorder](ADR-001-agent-flight-recorder.md)

## Context

Agent traces routinely contain sensitive data: prompts, model outputs, tool arguments, retrieval results, and user identifiers. Privacy concerns are a top adoption risk (ADR-001 Section 21.3).

ADR-001 mandates a redaction engine in both the SDK (before network transmission) and the collector ingestion pipeline. Default production behavior should be safe by default.

## Decision

**TBD.** This ADR will formalize:

- Redaction modes: `strict`, custom pattern sets, field allowlists/blocklists
- Built-in detectors: email, phone, credit card, API keys, secrets/tokens
- Actions per pattern: mask, remove, hash
- SDK-side vs. server-side redaction responsibilities
- Capture modes and their interaction with redaction

### Provisional capture modes (from ADR-001)

| Mode | Captures | Does not capture |
|------|----------|------------------|
| `metadata_only` | Trace/span IDs, latency, cost, tokens, tool names, status, error types | Prompts, responses, tool args/results |
| `redacted` | Full payloads after redaction | Raw sensitive values |
| `full` | Complete payloads | — (not recommended for production) |

### Default production position

```yaml
capture_mode: redacted
redaction_mode: strict
```

### Example redaction configuration

```yaml
redaction:
  mode: strict
  redact_prompts: false
  redact_responses: false
  patterns:
    - name: email
      action: mask
    - name: credit_card
      action: remove
    - name: api_key
      action: remove
  custom_patterns:
    - name: internal_customer_id
      regex: "cust_[a-zA-Z0-9]+"
      action: hash
```

## Consequences

**TBD.** Expected topics:

- Trade-off between debuggability and privacy in `redacted` mode
- Compliance implications for replay snapshots containing historical payloads
- Performance cost of regex/hash redaction at ingestion scale
- How redaction metadata is stored for audit without leaking content

> See [ADR-001](ADR-001-agent-flight-recorder.md) for the overarching architecture. See also [docs/policies.md](../docs/policies.md) for policy-related risk detection.