# StackStitch

## What This Is

An open-source AI operational intelligence engine that unifies data from engineering tools (GitHub, Jira, Sentry, Calendar, Slack), computes delivery metrics, detects anomalies, and generates context-aware narrative insights. Engineers interact with it through Slack — receiving proactive alerts when friction is detected, and asking ad-hoc questions that the system investigates across all connected data sources.

## Core Value

Reduce engineering leaders' cognitive load by automatically correlating cross-platform data and surfacing actionable, narrative insights — so they spend time removing blockers, not searching for them.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] GitHub connector ingests PRs, commits, and reviews via webhooks and polling
- [ ] Raw data is stored for audit trail with correlation IDs linking to parsed streams
- [ ] Stream data points are normalized into a standard format (type, source, project_id, timestamp, data)
- [ ] Connectors implement debouncing to prevent downstream overload during high-density events
- [ ] Metric calculators compute delivery metrics (PR frequency, cycle time, etc.) from streams
- [ ] Metrics support time-window aggregations (hourly base, aggregatable to daily/weekly/monthly)
- [ ] Anomaly detection monitors metrics and emits events when statistical thresholds are exceeded
- [ ] Deterministic investigators generate scheduled reports (predictable, template-based)
- [ ] AI investigators correlate data across streams to explain anomalies with narrative context
- [ ] Investigators output structured Insights stored in an insight store
- [ ] AI investigators can read past insights to detect recurring patterns
- [ ] User-facing agent formats new insights and sends proactive alerts to Slack
- [ ] User-facing agent accepts ad-hoc questions via Slack and invokes investigators to respond
- [ ] Credential store securely manages external API tokens and keys
- [ ] Users provide their own LLM API key (no token billing by StackStitch)
- [ ] Single-user, single-project setup — no auth, no organizations (OSS v1 scope)
- [ ] Deployable via containerized setup for local self-hosting

### Out of Scope

- WhatsApp channel — postponed due to complexity (templates, 24h window, Meta approval)
- Web channel / dashboard UI — deferred to v2
- Multi-user auth, organizations, permissions — enterprise/private version scope (v2)
- Derived metrics (metrics computed from other metrics) — viable but deferred
- OAuth social login — email/password or API key sufficient for OSS
- Jira, Sentry, Calendar connectors — v1 focuses on GitHub only; others come after
- Mobile app — not planned
- Token billing model — replaced by BYOK (bring your own key)

## Context

- **Team:** Jorge, Whitman, Gustavo — three co-founders, all contributing code
- **18 technical design sessions** completed (March 2026) covering architecture, domain model, connectors, metrics, investigators, channels, and business model
- **Architecture:** Three main services — Connector Service, Core, Channel System — communicating via Kafka (async) and HTTP (sync between services)
- **Domain model entities:** Stream, StreamDataPoint, Metric, MetricDataPoint, Insight, Investigation, Message, Thread, Project
- **Debouncing at two levels:** Connectors (before emitting stream_updated) and Calculators (before emitting metric_updated)
- **ADK (Google Agent Development Kit)** chosen for agent implementation — investigators are agents with tools to query stream/metric/insight stores
- **Landing page** live at stackstitch.dev
- **Open Source strategy:** Full OSS with permissive-but-no-commercial-redistribution license. Complexity of scaling is the monetization lever. Enterprise version adds users, orgs, permissions.
- **Core implements first** — testeable in isolation, then connectors, then channels

## Constraints

- **Language:** Python — chosen for AI ecosystem compatibility (ADK, LLM libraries)
- **Architecture:** Domain Driven Design + Hexagonal Architecture for the Core
- **Database:** MongoDB — handles variable schema of operational data from diverse sources
- **Message Broker:** Kafka — guarantees ordered message processing between services
- **Agent Framework:** Google ADK — for implementing investigators and user-facing agent
- **Channel v1:** Slack only — other channels deferred
- **Connector v1:** GitHub only — others deferred
- **OSS scope:** Single user, single project, no login — everything inferred by default

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full Open Source | Complexity of deploying at scale generates paying customers | — Pending |
| BYOK for LLM keys | Avoids token billing complexity; users control their AI costs | — Pending |
| Python as primary language | Best ecosystem for AI/ML, ADK, and LLM integrations | — Pending |
| Kafka over lighter alternatives | Ordered message processing guarantee needed for correct metric calculation | — Pending |
| MongoDB over relational DB | Flexible schema handles diverse data shapes from different connectors | — Pending |
| Core-first implementation | Testeable in isolation without external dependencies | — Pending |
| WhatsApp removed from MVP | Template approval, 24h window, Meta complexity — not worth for v1 | — Pending |
| No multi-user in OSS | Keeps OSS simple; enterprise features drive paid version | — Pending |
| DDD + Hexagonal for Core | Clean domain boundaries, testable, extensible for community connectors | — Pending |
| Google ADK for agents | Mature framework with tool-use patterns that fit investigator architecture | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-27 after initialization*
