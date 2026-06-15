# ADR-002: Storage Strategy for Agent Traces and Replay Data

## Status

Proposed (stub)

## Date

2026-06-15

## Owner

<Your Name / Team>

## Related Decisions

- [ADR-001: Build an OpenTelemetry-Native Agent Flight Recorder](ADR-001-agent-flight-recorder.md)

## Context

Agent Flight Recorder must support both frictionless local development and production-scale trace ingestion. Traces include high-volume span/event data, relational metadata, and large payloads (prompts, tool I/O, replay snapshots).

From ADR-001, the initial direction is:

- **Local development:** SQLite for fast setup, demos, and zero-infrastructure workflows
- **Production:** Postgres for relational metadata, ClickHouse for time-series trace analytics, and S3-compatible object storage for large blobs

ADR-001 Section 20.5 considered storing everything in Postgres. That approach is partially accepted for early/simple deployments but rejected as the sole production strategy due to poor fit for high-volume event analytics.

## Decision

**TBD.** This ADR will formalize:

- SQLite schema and migration strategy for local mode
- Postgres entity model (projects, agents, evals, policies, replay jobs)
- ClickHouse table design for spans, events, and metrics
- Object storage layout for prompts, responses, tool payloads, and replay snapshots
- Retention policies and tiering between hot (ClickHouse) and cold (object storage) data
- When teams should stay on SQLite vs. upgrade to production storage

### Provisional split (from ADR-001)

| Store | Responsibility |
|-------|----------------|
| **SQLite** (local) | All data for single-developer / demo use |
| **Postgres** (production) | Projects, environments, users, API keys, agents, eval definitions, policy definitions, replay jobs, dataset metadata, access control |
| **ClickHouse** (production) | Spans, events, model calls, tool calls, token usage, cost/latency/error metrics |
| **Object storage** (production) | Large prompts, responses, tool payloads, attachments, replay snapshots |

## Consequences

**TBD.** Expected topics:

- Operational complexity of three storage backends in production
- Migration path from SQLite local exports to production stores
- Query patterns for trace search vs. analytics aggregation
- Cost model at millions of spans per day

## Exit Criteria (Phase 4)

From ADR-001 implementation plan:

- System can handle higher-volume trace ingestion
- Postgres, ClickHouse, and object storage are integrated
- Teams can run production deployments without SQLite limitations

> See [ADR-001](ADR-001-agent-flight-recorder.md) for the overarching architecture.