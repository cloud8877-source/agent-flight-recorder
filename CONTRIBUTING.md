# Contributing

Thanks for helping build Agent Flight Recorder.

## Prerequisites

- Node.js 20+
- pnpm 9+ (`corepack enable`)
- Python 3.11+
- Docker (optional, for full stack)

## Local setup

```bash
cp .env.example .env
make setup    # creates .venv, installs JS + Python deps
make db-init
```

## Run the stack

**Option A — Docker Compose (recommended):**

```bash
make dev
```

- Collector: http://localhost:4318/health
- Web UI: http://localhost:3000

**Option B — native processes:**

```bash
# terminal 1
make collector

# terminal 2
make web

# terminal 3
make demo
```

## Repository layout

```text
apps/collector   FastAPI trace ingestion API (Python)
apps/web         Next.js trace viewer
packages/sdk-js  TypeScript SDK
packages/sdk-python  Python SDK
packages/shared-schema  Span types and JSON schemas
examples/        Demo agents
infra/           Docker Compose and SQLite schema
adr/             Architecture decision records
docs/            Product and developer guides
```

## Stack decisions (locked for Phase 1)

| Layer | Choice |
|-------|--------|
| Collector | **FastAPI** (Python) |
| Monorepo (JS) | **pnpm workspaces** + Turborepo |
| Monorepo (Python) | pip editable installs per package |
| Local storage | **SQLite** |
| Web UI | **Next.js** |

## Before opening a PR

1. Link to an issue or ADR section when relevant
2. Keep changes scoped to one concern
3. Update docs if you change public SDK or API behavior
4. Run `make lint` when touching JS/TS packages

## Architecture decisions

Major changes should update or add an ADR in [`adr/`](adr/). See [ADR-001](adr/ADR-001-agent-flight-recorder.md) for the parent architecture.