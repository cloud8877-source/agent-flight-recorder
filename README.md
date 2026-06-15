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

See [docs/quickstart.md](docs/quickstart.md) for environment variables, Docker Compose setup, and Phase 1 exit criteria.

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
| **1** | Local trace capture | Capture agent run locally; inspect model/tool calls; Docker Compose works |
| **2** | Replay & regression | Trace → regression test; CI fails on eval score below threshold |
| **3** | Policy & risk | Define policies; detect risky/forbidden tool calls; violation UI |
| **4** | Production storage & export | Postgres + ClickHouse + object storage; OTLP and third-party exporters |

## Key Architectural Bet

> OpenTelemetry should be the **compatibility layer**, but agent-specific replay, evaluation, policy, and audit semantics should be the **differentiation layer**.

## License

TBD