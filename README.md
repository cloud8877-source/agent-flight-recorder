# Agent Flight Recorder

An open-source, **OpenTelemetry-native** reliability platform for AI agents. Capture production agent behavior, replay failures, turn traces into regression tests, evaluate changes, and maintain an auditable record of every agent decision and tool call.

## Reliability Loop

```text
trace → replay → eval → regression test → policy check → audit trail
```

Agent Flight Recorder is not primarily another LLM observability dashboard. It focuses on the workflow enterprises need before trusting agents with meaningful autonomy.

## Quick Start (Target Experience)

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
  {
    name: "refund-agent",
    userId: "user_123",
  },
  async () => {
    return await agent.invoke("Refund my latest order");
  }
);
```

See [docs/quickstart.md](docs/quickstart.md) for full setup.

### Run locally

```bash
cp .env.example .env
make setup
make dev
```

- Collector: http://localhost:4318/health
- Web UI: http://localhost:3000

See [CONTRIBUTING.md](CONTRIBUTING.md) for native (non-Docker) development.

Verify the full Phase 1 loop:

```bash
make e2e
```

Run CI regression tests (Phase 2):

```bash
make test
make policy-test
```

CLI examples:

```bash
afr replay run_abc123 --model gpt-4.1-mini
afr eval run examples/evals/refund_tool_correctness.yml --run-id run_abc123
afr test ./examples/afr-tests/
afr policy check <run_id>
afr policy load examples/policies/require_approval_for_large_refunds.yml
```

## Documentation

| Doc | Description |
|-----|-------------|
| [quickstart.md](docs/quickstart.md) | Install, configure, and capture your first agent run |
| [architecture.md](docs/architecture.md) | System components, data model, and tech stack |
| [replay.md](docs/replay.md) | Replay modes, snapshots, and CLI usage |
| [evals.md](docs/evals.md) | Evaluator types, YAML config, and CI regression tests |
| [policies.md](docs/policies.md) | Policy rules, risk detection, and violation handling |

## Architecture Decisions

| ADR | Title |
|-----|-------|
| [ADR-001](adr/ADR-001-agent-flight-recorder.md) | Build an OpenTelemetry-Native Agent Flight Recorder |
| [ADR-002](adr/ADR-002-storage-strategy.md) | Storage Strategy for Agent Traces and Replay Data |
| [ADR-003](adr/ADR-003-redaction-privacy.md) | Redaction and Privacy Model |
| [ADR-004](adr/ADR-004-evaluation-regression.md) | Evaluation and Regression Testing Strategy |
| [ADR-005](adr/ADR-005-open-source-boundary.md) | Open Source Core vs. Commercial Cloud Boundary |

Full index: [adr/README.md](adr/README.md)

## MVP Scope

### Must Have

Python & TypeScript SDKs, manual instrumentation, OTel-compatible traces, local collector, SQLite storage, trace timeline UI, model/tool call capture, cost/latency/error tracking, basic redaction, replay from stored trace, manual evals, trace-to-regression-test conversion, Docker Compose, demo support agent.

### Should Have

OpenAI Agents SDK & LangGraph integrations, OTLP export, basic policy checks, prompt/model replay comparison, JSON/YAML eval config, GitHub Actions regression example.

### Could Have

ClickHouse/Postgres storage, hosted cloud, team accounts, SSO/RBAC, Slack alerts, advanced PII detection, MCP governance, LLM-as-judge evals.

## Implementation Phases

| Phase | Focus | Exit Criteria |
|-------|-------|---------------|
| **1** | Local trace capture ✅ | Capture agent run locally; inspect model/tool calls; cost/latency/redaction/search/replay/eval; `make e2e` passes |
| **2** | Replay & regression ✅ | `afr` CLI; model replay; `afr test` CI gate; GitHub Actions regression workflow |
| **3** | Policy & risk ✅ | Policy YAML; tool risk + PII detection; violation UI; `make policy-test` |
| **4** | Production storage & export | Postgres + ClickHouse + object storage; OTLP and third-party exporters |

## Key Architectural Bet

> OpenTelemetry should be the **compatibility layer**, but agent-specific replay, evaluation, policy, and audit semantics should be the **differentiation layer**.

## Repository layout

```text
apps/collector      FastAPI ingestion API
apps/web            Next.js trace viewer
packages/sdk-js     TypeScript SDK
packages/sdk-python Python SDK
packages/cli          afr CLI (replay, eval, test)
packages/shared-schema  Span types and JSON schemas
examples/           Demo agents
infra/              Docker Compose and SQLite schema
```

## License

[Apache License 2.0](LICENSE).

You may self-host, modify, and embed the SDKs in proprietary applications. A separate hosted or enterprise offering (SSO, RBAC, managed retention, support SLAs) may be offered commercially without restricting the open-source core. See [ADR-005](adr/ADR-005-open-source-boundary.md).