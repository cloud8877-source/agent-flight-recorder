# ADR-003: Redaction and Privacy Model for Prompt/Response Logging

## Status

Accepted

## Date

2026-06-15

## Owner

Agent Flight Recorder contributors

## Related Decisions

- [ADR-001: Build an OpenTelemetry-Native Agent Flight Recorder](ADR-001-agent-flight-recorder.md)

## Context

Agent traces routinely contain sensitive data: prompts, model outputs, tool arguments, retrieval results, and user identifiers. Privacy concerns are a top adoption risk (ADR-001 Section 21.3).

ADR-001 mandates a redaction engine in both the SDK (before network transmission) and the collector ingestion pipeline. Default production behavior should be safe by default.

## Decision

Phase 1 implements a **strict redaction mode** with SDK-side capture filtering and collector-side attribute scrubbing.

### Capture modes

| Mode | Captures | Does not capture |
|------|----------|------------------|
| `metadata_only` | Trace/span IDs, latency, cost, tokens, tool names, status, error types | Prompts, responses, tool args/results |
| `redacted` (default) | Full payloads after redaction | Raw sensitive values |
| `full` | Complete payloads | — (not recommended for production) |

Configured via `AFR_CAPTURE_MODE` in the Python SDK (`config.py`). Default: `redacted`.

### Redaction mode

`AFR_REDACTION_MODE=strict` (default) applies built-in detectors to all string values in span attributes:

| Pattern | Action |
|---------|--------|
| Email | Mask → `[REDACTED_EMAIL]` |
| Phone | Mask → `[REDACTED_PHONE]` |
| Credit card | Mask → `[REDACTED_CARD]` |
| API keys (`sk-`, `pk-`, etc.) | Remove → `[REDACTED_API_KEY]` |
| Bearer tokens | Mask → `Bearer [REDACTED_TOKEN]` |
| Custom regex (`AFR_REDACTION_CUSTOM_REGEX`) | Hash → `hash:<sha256-prefix>` |

### Responsibility split

1. **SDK** (`packages/sdk-python/src/agent_flight_recorder/redaction.py`): applies `apply_capture_mode()` before OTLP export — strips payloads in `metadata_only`, redacts in `redacted`, passes through in `full`.
2. **Collector** (`apps/collector/src/collector/redaction.py`): re-applies strict redaction on ingest as a defense-in-depth layer for OTLP attributes.

Schema reference: `packages/shared-schema/schemas/redaction.json`.

### Default production position

```yaml
capture_mode: redacted
redaction_mode: strict
```

## Consequences

**Positive**

- Safe-by-default local development and self-hosted deployments.
- Redaction runs twice (SDK + collector) so misconfigured clients still get scrubbed at ingest.

**Trade-offs**

- `redacted` mode may obscure debugging detail; operators can opt into `full` only in trusted environments.
- Replay snapshots inherit redacted payloads; historical sensitive content is not recoverable from stored traces.
- Regex redaction adds per-attribute CPU cost; acceptable at Phase 1 scale (SQLite, single-node collector).

**Deferred to later phases**

- Field-level allowlists/blocklists beyond capture modes.
- LLM-as-judge or ML-based PII detection.
- Redaction audit metadata (what was redacted, without leaking content).

> See [ADR-001](ADR-001-agent-flight-recorder.md) for the overarching architecture. See also [docs/policies.md](../docs/policies.md) for policy-related risk detection.