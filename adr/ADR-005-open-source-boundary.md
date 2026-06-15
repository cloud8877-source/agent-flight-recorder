# ADR-005: Open Source Core vs. Commercial Cloud Boundary

## Status

Proposed (stub)

## Date

2026-06-15

## Owner

<Your Name / Team>

## Related Decisions

- [ADR-001: Build an OpenTelemetry-Native Agent Flight Recorder](ADR-001-agent-flight-recorder.md)

## Context

Agent Flight Recorder is intended as an open-source project with a credible self-hosted path. Commercial opportunities may exist around hosted deployment, enterprise governance, and team collaboration — but the boundary must be clear to build developer trust and community contributions.

ADR-001 states the core product will be open source while listing potential paid features separately.

## Decision

**TBD.** This ADR will formalize:

- Exact open-source license choice
- Which components, features, and deployment modes are OSS vs. commercial
- Feature flag or packaging strategy (single repo vs. commercial overlay)
- Contribution and CLA policy
- Support and SLA tiers

### Open-source core (from ADR-001)

The open-source version should include:

- SDKs (Python, TypeScript)
- Local collector
- Local UI / trace viewer
- SQLite storage
- Replay engine
- Basic evals
- Basic policy checks
- Exporters (OTLP and integrations)
- Docker Compose deployment

### Future commercial features (from ADR-001)

Potential paid features:

- Hosted cloud
- Team collaboration
- SSO/SAML
- RBAC
- Long-term retention
- Advanced audit logs
- Compliance exports
- Advanced PII controls
- Enterprise policy packs
- High-scale ClickHouse deployment (managed)
- Managed eval workers
- Slack/Jira/GitHub integrations
- Approval workflows
- Private cloud deployment

### Explicitly out of MVP (commercial or otherwise)

- Full enterprise compliance workflows
- Multi-region deployment
- Full SOC 2 readiness
- Complete no-code policy builder

## Consequences

**TBD.** Expected topics:

- Risk of open-core backlash if boundary feels arbitrary
- Sustainability model (hosted cloud, support contracts, enterprise add-ons)
- How exporters keep OSS users integrated with existing paid observability stacks
- Community expectations for RBAC/SSO requests vs. commercial roadmap

> See [ADR-001](ADR-001-agent-flight-recorder.md) for the overarching architecture.