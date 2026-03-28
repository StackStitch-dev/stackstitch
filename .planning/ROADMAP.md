# Roadmap: StackStitch

## Overview

StackStitch is built as a monorepo with four independent projects: `core/` (domain model, use cases, ports, then infrastructure adapters), `connector-service/` (GitHub ingestion), `web/` (OAuth connection management UI), and `channels-service/` (Slack delivery). The Core is built first following true hexagonal architecture -- domain and ports defined before any infrastructure adapter. Once Core is complete and testable in isolation, the Connector Service brings real GitHub data in, the Web interface enables OAuth connections, and the Channels Service delivers insights to engineers via Slack.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Core Domain & Ports** - Domain model entities, use case interfaces, and port definitions for the entire system (hexagonal skeleton)
- [ ] **Phase 2: Core Infrastructure Adapters** - MongoDB adapters, Kafka producers/consumers, credential encryption, Docker Compose environment, and structured logging
- [ ] **Phase 3: Core Metric & Anomaly Engine** - Metric calculators, time-window aggregations, retroactive upserts, anomaly detection with severity tiers
- [ ] **Phase 4: Core Intelligence Engine** - Deterministic and AI investigators (ADK agents), insight store, token budgets, and pattern detection
- [ ] **Phase 5: Connector Service (GitHub)** - Webhook/polling ingestion, raw audit storage, stream normalization, debounced Kafka publishing
- [ ] **Phase 6: Web OAuth Interface** - Simple web UI for users to connect GitHub (and future platforms) via OAuth
- [ ] **Phase 7: Channels Service (Slack)** - Proactive insight alerts, ad-hoc question handling, Block Kit formatting, conversation threads

## Phase Details

### Phase 1: Core Domain & Ports
**Goal**: All domain entities, use case interfaces, and port definitions exist in `core/` so that every downstream phase implements against stable contracts -- no infrastructure, just pure domain logic
**Depends on**: Nothing (first phase)
**Requirements**: INFR-05
**Success Criteria** (what must be TRUE):
  1. Domain entities (Stream, StreamDataPoint, Metric, MetricDataPoint, Insight, Investigation, Credential, Project) are defined with validation rules and can be instantiated in tests
  2. Port interfaces (repository ports, message broker ports, credential store port) are defined as abstract contracts that adapters will implement
  3. Use case classes for stream ingestion, metric calculation, anomaly detection, and insight creation exist with business logic that operates on ports (not concrete implementations)
  4. All domain logic is testable with in-memory fakes -- no external dependencies required
  5. Directory structure follows `core/domain/`, `core/application/ports/`, `core/application/use_cases/` hexagonal layout
**Plans**: TBD

### Phase 2: Core Infrastructure Adapters
**Goal**: Core's ports have concrete implementations (MongoDB, Kafka, encryption) and all services start with one Docker Compose command, making the Core fully functional with real infrastructure
**Depends on**: Phase 1
**Requirements**: INFR-01, INFR-02, INFR-03, INFR-04, CRED-01, CRED-02, CRED-04
**Success Criteria** (what must be TRUE):
  1. Running `docker compose up` starts MongoDB, Kafka, and the Core service stub without errors
  2. MongoDB adapters implement all repository ports and can persist/retrieve domain entities
  3. Kafka adapters implement message broker ports and can publish/consume events
  4. A credential can be stored encrypted, retrieved decrypted, and is never visible in logs or API responses
  5. User can configure their own LLM API key via environment variable and it persists encrypted
  6. All services emit structured JSON logs with correlation context
**Plans**: TBD

### Phase 3: Core Metric & Anomaly Engine
**Goal**: Stream data flowing through Core is automatically transformed into engineering delivery metrics, and deviations from normal patterns are detected and emitted as structured anomaly events
**Depends on**: Phase 2
**Requirements**: METR-01, METR-02, METR-03, METR-04, METR-05, METR-06, METR-07, ANOM-01, ANOM-02, ANOM-03, ANOM-04
**Success Criteria** (what must be TRUE):
  1. PR cycle time, PR throughput, and review turnaround time are computed from stream data inserted via test fixtures
  2. Metrics are stored at hourly granularity and can be aggregated to daily, weekly, and monthly views
  3. Late-arriving stream data triggers retroactive upserts that correct affected metric windows
  4. When a metric_updated event arrives, anomaly detection runs statistical analysis and emits anomaly_detected events when thresholds are exceeded
  5. Anomaly sensitivity thresholds are configurable per metric type, and anomaly events include severity tiers
**Plans**: TBD

### Phase 4: Core Intelligence Engine
**Goal**: Anomalies and schedules trigger investigations that produce narrative insights explaining what happened and why, completing the Core's full processing pipeline
**Depends on**: Phase 3
**Requirements**: INTL-01, INTL-02, INTL-03, INTL-04, INTL-05, INTL-06
**Success Criteria** (what must be TRUE):
  1. Deterministic investigators run on a cron schedule and produce template-based reports stored as insights
  2. AI investigators are triggered by anomaly_detected events and produce narrative explanations correlating data across streams
  3. AI investigators can query past insights and detect recurring patterns across investigations
  4. All investigators are implemented as ADK agents with tools to query stream, metric, and insight stores
  5. Each AI investigation respects a token budget limit and logs tokens consumed
**Plans**: TBD

### Phase 5: Connector Service (GitHub)
**Goal**: Real GitHub activity (PRs, commits, reviews) flows into `connector-service/`, is stored for audit, normalized, and published to Kafka where Core's metric engine picks it up
**Depends on**: Phase 2
**Requirements**: INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05, INGEST-06, INGEST-07, CRED-03
**Success Criteria** (what must be TRUE):
  1. A GitHub webhook event for a PR, commit, or review is received, verified (HMAC), and stored as raw audit data
  2. A polling fallback retrieves the same data when webhooks are unavailable
  3. Raw data and parsed stream data points are linked by a correlation_id that traces back to the original event
  4. Stream data points are published in the standard normalized format (type, source, project_id, timestamp, data)
  5. After the debounce window, a stream_updated event is published to Kafka and Core's calculators process it
**Plans**: TBD

### Phase 6: Web OAuth Interface
**Goal**: Users can connect their GitHub account (and later other platforms) to StackStitch through a simple web interface that manages OAuth flows and token storage
**Depends on**: Phase 5
**Requirements**: OAUTH-01
**Success Criteria** (what must be TRUE):
  1. User can visit the web interface and initiate a GitHub OAuth connection flow
  2. After completing OAuth, the access token is stored encrypted via Core's credential store
  3. The connector service can retrieve the stored OAuth token to authenticate GitHub API requests
**Plans**: TBD
**UI hint**: yes

### Phase 7: Channels Service (Slack)
**Goal**: Engineers receive proactive insight alerts in Slack and can ask ad-hoc questions that the system investigates and answers in conversational threads
**Depends on**: Phase 4
**Requirements**: CHAN-01, CHAN-02, CHAN-03, CHAN-04, CHAN-05
**Success Criteria** (what must be TRUE):
  1. When a new insight is deposited in the insight store, a formatted Slack message is sent to the configured channel
  2. A user can type an ad-hoc question in Slack and receive an investigator-generated response in a thread
  3. Slack messages use Block Kit formatting for structured, readable output
  4. Message history is stored per thread so follow-up questions have conversation context
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7
Note: Phase 5 depends on Phase 2 (not Phase 4), so Phases 3-4 and Phase 5 could theoretically run in parallel, but sequential execution keeps things simple.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Domain & Ports | 0/TBD | Not started | - |
| 2. Core Infrastructure Adapters | 0/TBD | Not started | - |
| 3. Core Metric & Anomaly Engine | 0/TBD | Not started | - |
| 4. Core Intelligence Engine | 0/TBD | Not started | - |
| 5. Connector Service (GitHub) | 0/TBD | Not started | - |
| 6. Web OAuth Interface | 0/TBD | Not started | - |
| 7. Channels Service (Slack) | 0/TBD | Not started | - |
