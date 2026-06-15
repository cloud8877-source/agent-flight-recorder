# Quickstart

Get Agent Flight Recorder capturing agent runs locally in under five minutes.

> Parent decision: [ADR-001](../adr/ADR-001-agent-flight-recorder.md)

> **Note:** Application code (SDK, collector, UI) is not yet implemented. This guide describes the target Phase 1 developer experience from the architecture decision.

## Prerequisites

- Python 3.11+ or Node.js 20+
- Docker and Docker Compose (for local stack)

## 1. Start the Local Stack

Once `infra/docker-compose.yml` exists:

```bash
docker compose -f infra/docker-compose.yml up -d
```

This starts the collector, SQLite-backed storage, and web UI.

## 2. Configure Environment

```bash
export AFR_API_KEY=dev_key
export AFR_ENDPOINT=http://localhost:4318
export AFR_ENVIRONMENT=development
export AFR_CAPTURE_PROMPTS=true
export AFR_CAPTURE_RESPONSES=true
export AFR_REDACTION_MODE=strict
```

| Variable | Description |
|----------|-------------|
| `AFR_API_KEY` | Project API key |
| `AFR_ENDPOINT` | Collector URL (OTLP HTTP compatible) |
| `AFR_ENVIRONMENT` | `development`, `staging`, or `production` |
| `AFR_CAPTURE_PROMPTS` | Whether to capture prompt content |
| `AFR_CAPTURE_RESPONSES` | Whether to capture model responses |
| `AFR_REDACTION_MODE` | `strict`, or custom per [ADR-003](../adr/ADR-003-redaction-privacy.md) |

Production default should be `capture_mode: redacted` with `redaction_mode: strict` — see [policies.md](policies.md).

## 3. Install the SDK

**Python** (target):

```bash
pip install agent-flight-recorder
```

**TypeScript** (target):

```bash
npm install @agent-flight-recorder/node
```

## 4. Instrument Your Agent

**Python:**

```python
from agent_flight_recorder import recorder

recorder.init(
    app_name="support-agent",
    environment="development"
)

with recorder.agent_run(name="refund-agent", user_id="user_123") as run:
    result = agent.invoke("Refund my latest order")
```

**TypeScript:**

```ts
import { recorder } from "@agent-flight-recorder/node";

recorder.init({
  appName: "support-agent",
  environment: "development",
});

await recorder.agentRun(
  { name: "refund-agent", userId: "user_123" },
  async () => agent.invoke("Refund my latest order")
);
```

### What Gets Captured

Each `agent_run` produces spans for:

- Model calls (provider, model, tokens, cost, latency)
- Tool calls (name, arguments, results, risk level)
- Retrieval queries, memory reads/writes
- Errors, policy checks, human approvals

## 5. View Traces

Open the local UI (default `http://localhost:3000`) and:

1. Search by user ID, trace ID, or agent name
2. Open the trace timeline
3. Inspect model calls, tool calls, cost, and latency breakdown

## Phase 1 Exit Criteria

From [ADR-001](../adr/ADR-001-agent-flight-recorder.md):

- [ ] Developer can capture an agent run locally
- [ ] Developer can inspect model calls and tool calls in the UI
- [ ] Setup works through Docker Compose

## Next Steps

- [replay.md](replay.md) — replay a captured run with different prompt/model/tool config
- [evals.md](evals.md) — define evaluators and convert a failure into a regression test
- [architecture.md](architecture.md) — full system design