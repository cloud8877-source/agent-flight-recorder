# ADR-005: Open Source Core vs. Commercial Cloud Boundary

## Status

Accepted

## Date

2026-06-15

## Owner

<Your Name / Team>

## Related Decisions

- [ADR-001: Build an OpenTelemetry-Native Agent Flight Recorder](ADR-001-agent-flight-recorder.md)

## Context

Agent Flight Recorder is intended as an open-source project with a credible self-hosted path. Commercial opportunities may exist around hosted deployment, enterprise governance, and team collaboration — but the boundary must be clear to build developer trust and community contributions.

ADR-001 states the core product will be open source while listing potential paid features separately. ADR-001 Section 21.3 flags open-core backlash as a risk if the commercial boundary feels arbitrary.

The project is OpenTelemetry-native; alignment with the OTel ecosystem's licensing norms reduces adoption friction for enterprises embedding SDKs and running self-hosted deployments.

## Decision

### License: Apache License 2.0

The entire open-source repository is licensed under **Apache 2.0**. See [LICENSE](../LICENSE).

**Rationale:**

| Requirement (from ADR-001) | Why Apache 2.0 |
|----------------------------|----------------|
| Maximum developer adoption | Permissive; legal teams routinely approve embedding in proprietary agent apps |
| OpenTelemetry compatibility layer | Same license family as OpenTelemetry itself |
| Credible self-hosting | No copyleft obligations for enterprise deployments |
| Commercial hosted offering later | Licensor can operate managed cloud and sell support/enterprise add-ons |
| Replay, eval, policy in OSS core | No license gating of differentiated features — monetization is service-based |
| Community contributions | Well-understood contribution terms; explicit patent grant |

**Rejected alternatives:**

- **AGPL-3.0** — Protects against uncompensated hosted forks but slows enterprise self-hosting and complicates a first-party hosted product.
- **BSL / SSPL** — Conflicts with the open-source wedge positioning and ADR-005 backlash risk.
- **Open-core license split** — Replay, eval, and policy are core OSS value; restricting them under a proprietary license would undermine differentiation.

### Open-source core (Apache 2.0)

The open-source version includes:

- SDKs (Python, TypeScript)
- Local collector
- Local UI / trace viewer
- SQLite storage
- Replay engine
- Basic evals
- Basic policy checks
- Exporters (OTLP and integrations)
- Docker Compose deployment

### Commercial boundary (separate from license)

Commercial offerings are **services and add-ons**, not proprietary forks of core code:

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
- Support and SLA tiers

Packaging strategy: **single Apache 2.0 monorepo** for the OSS core; commercial features ship as separate services, repos, or deployment overlays when introduced.

### Still TBD

- Contribution CLA requirement (if any)
- Trademark policy for "Agent Flight Recorder" name and logo
- Support tier definitions and pricing

### Explicitly out of MVP (commercial or otherwise)

- Full enterprise compliance workflows
- Multi-region deployment
- Full SOC 2 readiness
- Complete no-code policy builder

## Consequences

### Positive

- Enterprises can embed SDKs and self-host without copyleft review cycles
- Aligns with OpenTelemetry ecosystem expectations
- Clear, defensible commercial model: sell hosting, governance, and operations — not core reliability features
- Apache 2.0 patent grant reduces contributor and adopter risk

### Negative

- Cloud providers may offer managed builds of the OSS collector without contributing back (accepted trade-off for adoption)
- No license-based protection of the hosted business; differentiation must come from product velocity, support, and enterprise features

### Risks

| Risk | Mitigation |
|------|------------|
| Open-core backlash | Keep replay, eval, policy, and exporters in Apache 2.0 core permanently |
| Cloud vendor repackaging | Move fast on hosted offering; build brand and enterprise integrations |
| Community expects RBAC/SSO in OSS | Document commercial roadmap clearly in README and ADR-005 |

> See [ADR-001](ADR-001-agent-flight-recorder.md) for the overarching architecture.