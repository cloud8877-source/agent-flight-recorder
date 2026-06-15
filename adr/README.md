# Architecture Decision Records

This directory contains architecture decision records (ADRs) for **Agent Flight Recorder**.

## Status Lifecycle

ADRs move through these states:

- **Proposed** — under review, not yet committed to
- **Accepted** — active decision guiding implementation
- **Deprecated** — superseded or no longer applicable

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](ADR-001-agent-flight-recorder.md) | Build an OpenTelemetry-Native Agent Flight Recorder | Accepted |
| [ADR-002](ADR-002-storage-strategy.md) | Storage Strategy for Agent Traces and Replay Data | Proposed (stub) |
| [ADR-003](ADR-003-redaction-privacy.md) | Redaction and Privacy Model for Prompt/Response Logging | Accepted |
| [ADR-004](ADR-004-evaluation-regression.md) | Evaluation and Regression Testing Strategy | Accepted |
| [ADR-005](ADR-005-open-source-boundary.md) | Open Source Core vs. Commercial Cloud Boundary | Accepted |

[ADR-001](ADR-001-agent-flight-recorder.md) is the parent decision. ADRs 002–005 expand on specific areas deferred from that document.