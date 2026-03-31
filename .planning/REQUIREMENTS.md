# Requirements: StackStitch

**Defined:** 2026-03-27
**Core Value:** Reduce engineering leaders' cognitive load by automatically correlating cross-platform data and surfacing actionable, narrative insights

## v1 Requirements

Requirements for initial open-source release. Each maps to roadmap phases.

### Data Ingestion

- [ ] **INGEST-01**: GitHub connector receives webhook events for PRs, commits, and reviews
- [ ] **INGEST-02**: GitHub connector supports polling as fallback when webhooks are unavailable
- [ ] **INGEST-03**: Connector implements debouncing to batch stream_updated events during high-density periods
- [ ] **INGEST-04**: Raw webhook/polling data is stored in an audit database before parsing
- [ ] **INGEST-05**: Raw data and parsed stream data points are linked via a generated correlation_id
- [ ] **INGEST-06**: Stream data points are normalized into standard format (type, source, project_id, timestamp, data)
- [ ] **INGEST-07**: Connector publishes stream_updated events to Kafka after debounce window

### Credentials & Configuration

- [ ] **CRED-01**: Credential store securely encrypts and stores external API tokens at rest
- [ ] **CRED-02**: User can configure their own LLM API key (BYOK) for AI investigators
- [ ] **CRED-03**: GitHub OAuth tokens can be stored and refreshed by the connector
- [ ] **CRED-04**: Credentials are never logged or exposed in API responses

### OAuth Management

- [ ] **OAUTH-01**: Web interface allows users to connect GitHub (and future platforms) via OAuth flow, storing tokens through Core's credential store

### Metrics

- [ ] **METR-01**: PR cycle time metric is calculated (time from PR open to merge)
- [ ] **METR-02**: PR throughput metric is calculated (PRs merged per time window)
- [ ] **METR-03**: Review turnaround time metric is calculated (time from review request to first review)
- [ ] **METR-04**: Metrics are computed for hourly time windows and aggregatable to daily/weekly/monthly
- [ ] **METR-05**: Metric calculators use retroactive upserts to handle async data correctly
- [ ] **METR-06**: Metric calculators implement debouncing before emitting metric_updated events
- [ ] **METR-07**: Stream consumers listen to stream_updated events and invoke relevant calculators

### Anomaly Detection

- [ ] **ANOM-01**: Monitoring service reacts to metric_updated events and runs statistical analysis on metric history
- [ ] **ANOM-02**: Anomaly detection emits anomaly_detected events when thresholds are exceeded
- [ ] **ANOM-03**: Anomaly detection supports configurable sensitivity thresholds
- [ ] **ANOM-04**: Anomaly alerts include severity tiers to prevent alert fatigue

### Intelligence

- [ ] **INTL-01**: Deterministic investigators generate scheduled reports on a cron schedule
- [ ] **INTL-02**: AI investigators correlate data across streams to explain anomalies with narrative context
- [ ] **INTL-03**: AI investigators can read past insights from the insight store to detect recurring patterns
- [ ] **INTL-04**: All investigators output structured Insights stored in the insight store
- [ ] **INTL-05**: AI investigators implement token budget limits per investigation to control LLM costs
- [ ] **INTL-06**: Investigators are implemented as ADK agents with tools to query stream, metric, and insight stores

### Delivery (Channels)

- [ ] **CHAN-01**: User-facing agent formats new insights and sends proactive alerts to Slack
- [ ] **CHAN-02**: User-facing agent accepts ad-hoc questions via Slack and invokes investigators to respond
- [ ] **CHAN-03**: Slack messages use Block Kit formatting for rich, readable output
- [ ] **CHAN-04**: Message history is stored per thread for conversation continuity
- [ ] **CHAN-05**: Proactive alerts are dispatched when new insights are deposited in the insight store

### Infrastructure

- [ ] **INFR-01**: All services run via a single Docker Compose command for local deployment
- [ ] **INFR-02**: MongoDB is used as the primary data store for streams, metrics, and insights
- [ ] **INFR-03**: Kafka handles async messaging between Connector Service and Core
- [ ] **INFR-04**: Structured JSON logging with correlation context across all services
- [x] **INFR-05**: Project scaffold follows DDD + Hexagonal Architecture for the Core service

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Additional Connectors

- **CONN-01**: Jira connector ingests issues, sprints, and status changes
- **CONN-02**: Sentry connector ingests errors and crash reports
- **CONN-03**: Google Calendar connector ingests meeting data
- **CONN-04**: Slack activity connector ingests channel activity metrics

### Enterprise Features

- **ENTR-01**: Multi-user authentication with login
- **ENTR-02**: Organization and project management (multi-tenant)
- **ENTR-03**: Role-based permissions and access control
- **ENTR-04**: Web channel as fallback for companies that restrict Slack apps

### Advanced Intelligence

- **ADVN-01**: Derived metrics (metrics computed from other metrics)
- **ADVN-02**: Custom metric definitions by users
- **ADVN-03**: WhatsApp channel with fallback logic from Slack

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Web dashboard / charts | Massive scope increase; Slack-first is the deliberate product position |
| Individual developer scoring / gamification | Industry backlash; dilutes positioning as a team-level tool |
| Real-time streaming dashboard | WebSocket infra + frontend framework needed; batch metrics sufficient |
| OAuth social login | Single-user OSS doesn't need auth; API key / env-var sufficient |
| Mobile app | Slack IS the mobile interface |
| Token billing / usage metering | BYOK eliminates this for OSS |
| DORA metric labeling | Contested/political; compute raw data, let users interpret |
| Workflow automation (auto-assign, auto-close) | Read-only intelligence platform; never mutate external tools |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFR-05 | Phase 1 | Complete |
| INFR-01 | Phase 2 | Pending |
| INFR-02 | Phase 2 | Pending |
| INFR-03 | Phase 2 | Pending |
| INFR-04 | Phase 2 | Pending |
| CRED-01 | Phase 2 | Pending |
| CRED-02 | Phase 2 | Pending |
| CRED-04 | Phase 2 | Pending |
| METR-01 | Phase 3 | Pending |
| METR-02 | Phase 3 | Pending |
| METR-03 | Phase 3 | Pending |
| METR-04 | Phase 3 | Pending |
| METR-05 | Phase 3 | Pending |
| METR-06 | Phase 3 | Pending |
| METR-07 | Phase 3 | Pending |
| ANOM-01 | Phase 3 | Pending |
| ANOM-02 | Phase 3 | Pending |
| ANOM-03 | Phase 3 | Pending |
| ANOM-04 | Phase 3 | Pending |
| INTL-01 | Phase 4 | Pending |
| INTL-02 | Phase 4 | Pending |
| INTL-03 | Phase 4 | Pending |
| INTL-04 | Phase 4 | Pending |
| INTL-05 | Phase 4 | Pending |
| INTL-06 | Phase 4 | Pending |
| INGEST-01 | Phase 5 | Pending |
| INGEST-02 | Phase 5 | Pending |
| INGEST-03 | Phase 5 | Pending |
| INGEST-04 | Phase 5 | Pending |
| INGEST-05 | Phase 5 | Pending |
| INGEST-06 | Phase 5 | Pending |
| INGEST-07 | Phase 5 | Pending |
| CRED-03 | Phase 5 | Pending |
| OAUTH-01 | Phase 6 | Pending |
| CHAN-01 | Phase 7 | Pending |
| CHAN-02 | Phase 7 | Pending |
| CHAN-03 | Phase 7 | Pending |
| CHAN-04 | Phase 7 | Pending |
| CHAN-05 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0

---
*Requirements defined: 2026-03-27*
*Last updated: 2026-03-27 after roadmap revision (monorepo restructure)*
