# ADR-002: Storage Strategy for Agent Traces and Replay Data

## Status

Accepted (Phase 4 scope)

## Date

2026-06-15

## Owner

Agent Flight Recorder contributors

## Related Decisions

- [ADR-001: Build an OpenTelemetry-Native Agent Flight Recorder](ADR-001-agent-flight-recorder.md)

## Context

Agent Flight Recorder must support both frictionless local development and production-scale trace ingestion. Traces include high-volume span/event data, relational metadata, and large payloads (prompts, tool I/O, replay snapshots).

## Decision

### Storage modes

| Mode | Backend | Use case |
|------|---------|----------|
| **SQLite** (default) | `AFR_STORAGE_BACKEND=sqlite` | Local dev, demos, CI |
| **Postgres** | `AFR_STORAGE_BACKEND=postgres` + `AFR_DATABASE_URL` | Production metadata and relational queries |

Schema files:

- `infra/sqlite/schema.sql`
- `infra/postgres/schema.sql`

The collector uses a unified DB interface (`collector/storage/`) with `?` placeholders converted for Postgres.

### ClickHouse analytics (optional)

High-volume span events are written asynchronously to ClickHouse when `AFR_CLICKHOUSE_URL` is set.

- Schema: `infra/clickhouse/schema.sql`
- Table: `span_events` (MergeTree, partitioned by month)
- Writer: `collector/analytics/clickhouse.py` (fire-and-forget on ingest)

### Object storage (optional)

Large span attributes (prompts, responses, tool payloads) exceeding `AFR_BLOB_THRESHOLD_BYTES` (default 4096) are offloaded to S3-compatible storage when `AFR_OBJECT_STORAGE_ENDPOINT` is set.

- References stored in `spans.blob_refs_json`
- Large replay snapshots use `replay_snapshots.snapshot_blob_key`
- Implementation: `collector/blob_store.py` (boto3 / MinIO)

### OTLP export

Traces can be forwarded to external OTLP endpoints on ingest:

- `AFR_OTLP_EXPORT_ENDPOINT` — generic collector
- `LANGFUSE_*` — Langfuse OTLP API
- `PHOENIX_OTLP_ENDPOINT` — Arize Phoenix

See `examples/exporters/README.md`.

### Production stack

`infra/docker-compose.prod.yml` runs Postgres + ClickHouse + MinIO + collector.

```bash
make prod-up      # start production compose stack
make storage-test # verify Postgres ingest + ClickHouse analytics
```

## Consequences

**Positive**

- Local SQLite workflow unchanged for Phase 1–3 developers.
- Production path scales metadata (Postgres) and analytics (ClickHouse) independently.
- Large payloads do not bloat relational rows.
- OTLP forwarding integrates with existing observability stacks.

**Trade-offs**

- Three optional backends increase operational surface in production.
- ClickHouse and object storage writes are best-effort async (ingest does not fail if they are down).
- Full migration tooling from SQLite exports to production stores is deferred.

## Exit criteria (met)

- Postgres backend integrated (`AFR_STORAGE_BACKEND=postgres`)
- ClickHouse span analytics integrated
- Object storage blob offload integrated
- OTLP export to external targets (Langfuse, Phoenix examples)
- `make storage-test` verifies production storage path