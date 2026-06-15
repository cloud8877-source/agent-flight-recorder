# Architecture

How Agent Flight Recorder is structured: OpenTelemetry as the base protocol, an agent-specific semantic layer on top, and components for ingestion, storage, replay, eval, and policy.

> Parent decision: [ADR-001](../adr/ADR-001-agent-flight-recorder.md)

## High-Level Architecture

```mermaid
flowchart TD
    A[Agent Application] --> B[Agent Flight Recorder SDK]

    B --> C[OpenTelemetry Spans]
    B --> D[Agent Events]

    C --> E[Collector API]
    D --> E[Collector API]

    E --> F[Ingestion Pipeline]
    F --> G[Redaction Engine]
    G --> H[Trace Storage]
    G --> I[Blob/Object Storage]

    H --> J[Web UI]
    H --> K[Replay Engine]
    H --> L[Eval Engine]
    H --> M[Policy Engine]

    K --> L
    M --> J
    L --> J

    F --> N[OTLP Exporter]
    N --> O[Sentry / Datadog / PostHog / Phoenix / Langfuse]

    J --> P[CI/CD Integration]
    L --> P
```

## Core Decision: OpenTelemetry + Agent Semantics

OpenTelemetry provides traces, spans, attributes, events, collector compatibility, and vendor neutrality. Raw OTel alone is insufficient for agent reliability — replay, evals, and policy require richer structure.

**Agent span types:**

```text
agent.run
agent.step
llm.call
tool.call
retrieval.query
memory.read
memory.write
policy.check
human.approval
eval.run
replay.run
```

See [ADR-001 Section 8](../adr/ADR-001-agent-flight-recorder.md#8-core-architectural-decision) for rationale.

## Components

### SDKs (Python, TypeScript)

- Create OTel-compatible traces and agent-specific spans
- Capture runs, model calls, tool calls, retrieval, memory, errors, cost, latency
- Local buffering, retry, sampling, configurable redaction
- Environment-based config via `AFR_*` variables

### Collector API

Endpoints:

```text
POST /v1/traces
POST /v1/events
POST /v1/replays
POST /v1/evals
GET  /health
```

Also supports OTLP HTTP ingestion. Validates, normalizes, redacts, and routes to storage and exporters.

### Ingestion Pipeline

```text
Receive → validate → normalize → enrich → redact → classify risk → store → export
```

Enrichment may add model cost estimates, tool risk levels, deployment/git metadata, and error classification.

### Storage

| Mode | Backends |
|------|----------|
| **Local** | SQLite |
| **Production** | Postgres (metadata), ClickHouse (events/spans), object storage (large payloads) |

Details: [ADR-002](../adr/ADR-002-storage-strategy.md) (stub).

### Engines

- **Replay** — reproduce prior runs under controlled conditions ([replay.md](replay.md))
- **Eval** — score traces and replay results ([evals.md](evals.md))
- **Policy** — detect forbidden/risky behavior ([policies.md](policies.md))

## Data Model

```mermaid
erDiagram
    PROJECT ||--o{ ENVIRONMENT : has
    PROJECT ||--o{ AGENT : has
    AGENT ||--o{ AGENT_RUN : executes
    AGENT_RUN ||--o{ SPAN : contains
    AGENT_RUN ||--o{ MODEL_CALL : contains
    AGENT_RUN ||--o{ TOOL_CALL : contains
    AGENT_RUN ||--o{ POLICY_CHECK : contains
    AGENT_RUN ||--o{ EVAL_RESULT : evaluated_by
    AGENT_RUN ||--o{ REPLAY_RUN : replayed_as

    PROJECT {
      uuid id
      string name
      datetime created_at
    }

    ENVIRONMENT {
      uuid id
      uuid project_id
      string name
    }

    AGENT {
      uuid id
      uuid project_id
      string name
      string version
    }

    AGENT_RUN {
      uuid id
      uuid agent_id
      string trace_id
      string user_id
      string session_id
      string status
      datetime started_at
      datetime ended_at
    }
```

Large payloads (prompts, tool I/O) are stored as blob references, not inline in relational/analytics stores.

## Event Taxonomy

Events follow a consistent `domain.action.status` pattern:

```text
agent.run.started / .completed / .failed
llm.call.started / .completed / .failed
tool.call.started / .completed / .failed
policy.check.started / .completed / .failed
replay.run.started / .completed / .failed
eval.run.started / .completed / .failed
```

Full list in [ADR-001 Section 11](../adr/ADR-001-agent-flight-recorder.md#11-agent-event-taxonomy).

## Technology Stack

| Layer | Choices |
|-------|---------|
| SDKs | Python, TypeScript, OpenTelemetry libraries |
| Backend | FastAPI or Node.js, background workers, OTLP HTTP |
| Storage (local) | SQLite |
| Storage (prod) | Postgres, ClickHouse, S3-compatible object storage |
| Frontend | Next.js, React, Tailwind, TanStack Query |
| Deployment | Docker Compose (local/self-hosted), Helm (later) |

## Related Docs

- [quickstart.md](quickstart.md) — get running in under five minutes
- [replay.md](replay.md) — replay modes and snapshots
- [evals.md](evals.md) — evaluation and regression testing
- [policies.md](policies.md) — policy engine and risk detection