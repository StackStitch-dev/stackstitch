# Phase 1: Core Domain & Ports - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

All domain entities, use case interfaces, port definitions, domain events, and in-memory fakes for the Core module (`core/`). This is the hexagonal skeleton — pure domain logic with no infrastructure dependencies. Every downstream phase implements against these stable contracts.

**NOT in scope:** Infrastructure adapters (MongoDB, Kafka, FastAPI), Docker setup, external integrations, query use cases, scheduled investigators. Credential entity and credential store belong to Connector Service, not Core.

</domain>

<decisions>
## Implementation Decisions

### Domain Modeling Style
- **D-01:** Hybrid domain models — entities own validation and single-entity business logic; use cases handle cross-entity orchestration
- **D-02:** Pydantic BaseModel as base class for all entities — built-in validation, serialization, aligns with FastAPI stack
- **D-03:** UUID identity generated at entity creation (`uuid4()`), not DB-assigned — entities have identity before persistence
- **D-04:** Entities collect domain events internally; use cases flush events after persistence via EventPublisher
- **D-05:** Typed domain events — specific event classes (StreamUpdated, MetricUpdated, etc.) in the domain layer; Kafka topic mapping is an adapter concern
- **D-06:** `created_at` as UTC datetime on all entities; `updated_at` managed at DB level only (not in domain)
- **D-07:** Channel-agnostic Thread/Message — no Slack-specific fields in Core; channel details are adapter concerns in channels-service
- **D-08:** Investigation is a full entity with its own lifecycle (pending/running/completed/failed), includes ordered list of typed InvestigationStep objects recording tool calls, reasoning, and observations with token tracking
- **D-09:** Consulted data sources are implicit in InvestigationStep trace — no separate tracking lists
- **D-10:** Single trigger per Investigation (anomaly | adhoc) with trigger_ref UUID and optional query string
- **D-11:** 1:1 relationship: one Investigation produces one Insight (or none on failure)
- **D-12:** Insight is semi-structured — typed core fields (id, project_id, investigation_id, title, narrative, insight_type) with flexible `metadata: dict[str, Any]` for extras
- **D-13:** Credential entity and credential store port belong entirely to Connector Service, NOT Core. Core has zero knowledge of credentials. CRED-01, CRED-02, CRED-04 should map to Connector Service phases.
- **D-14:** Project is NOT a domain entity — it's a virtual tenancy concept. A `project_id: UUID` on other entities defines data ownership. No Project class, no Project repository.
- **D-15:** All entities reference project_id as a loose UUID field — no object graph, queries filter by project_id

### Stream/StreamDataPoint Design
- **D-16:** Stream embeds StreamDataPoints (list of embedded value objects)
- **D-17:** Stream has no id and no created_at — identified by composite key `(source, stream_type, project_id)`
- **D-18:** StreamDataPoint.data is `dict[str, Any]` — flexible payload, shape varies by stream_type, validated at ingestion time

### Metric/MetricDataPoint Design
- **D-19:** Metric embeds MetricDataPoints (consistent with Stream pattern)
- **D-20:** Metric has no id — identified by composite key `(metric_type, project_id)`
- **D-21:** MetricDataPoint is minimal: just `value: float` + `timestamp: datetime` — no TimeWindow
- **D-22:** Aggregation strategy deferred to Phase 3 — depends on anomaly detection algorithm
- **D-23:** MetricsCalculator is a secondary port (called by use cases, not event-triggered)
- **D-24:** MetricMonitor is a secondary port, does not return anything — uses EventPublisher directly to emit AnomalyDetected events; EventPublisher injected at adapter construction

### Anomaly Detection
- **D-25:** Anomaly is a domain event only (AnomalyDetected), NOT a persisted entity — emitted by MetricMonitor, consumed by investigators

### Message/Thread Design
- **D-26:** Thread embeds Messages (consistent pattern), identified by UUID
- **D-27:** No direct link between Thread and Investigation — relationship is implicit through message content

### Invocation & Orchestration Design
- **D-28:** Invocation is a new domain entity — records every pending orchestration request with source (user_message | insight), role, message, status (pending | processing | done)
- **D-29:** Invocations are created by the use cases that emit triggering events: RunInvestigation creates insight invocations, HandleMessage creates user message invocations
- **D-30:** Orchestrate use case implements a drain loop: reads all pending invocations, passes to Agent, checks again for new arrivals, loops until empty, then delivers final response
- **D-31:** Agent receives full Thread + new pending invocations each iteration; intermediate responses stored in Thread for context but NOT delivered
- **D-32:** Only the final response (after drain loop completes) is delivered via MessageDeliverer
- **D-33:** Concurrency handled by Kafka consumer group sequential guarantees (partition by thread_id), NOT by application-level locks
- **D-34:** Agent has a single tool: RunInvestigation. Tool interface deferred to Phase 4 (ADK adapter concern).

### Port Granularity
- **D-35:** One repository port per aggregate, async throughout (`async def` on all port methods)
- **D-36:** Secondary (driven) ports: Repository ports per aggregate + EventPublisher + Investigator + MetricsCalculator + MetricMonitor + Agent + MessageDeliverer
- **D-37:** EventPublisher only (no EventSubscriber port) — event subscription is a primary adapter concern
- **D-38:** Primary port interfaces defined in Phase 1 — use cases ARE the primary ports (one class per use case)
- **D-39:** In-memory fakes for ALL ports shipped in Phase 1 alongside the port definitions
- **D-40:** Orchestrator port renamed: it's the Orchestrate use case, not a separate port. Agent is the secondary port it calls.
- **D-41:** Scheduler port removed — scheduled investigators deferred to v2

### Value Objects & Types
- **D-42:** Plain UUIDs for all entity identifiers — no NewType wrappers or value object classes
- **D-43:** String enums `(str, Enum)` for all domain enums — natural JSON/MongoDB serialization
- **D-44:** Value objects beyond enums at Claude's discretion — determine which concepts warrant dedicated types based on where domain logic benefits

### Error Handling
- **D-45:** Custom exception hierarchy with `DomainError` base class
- **D-46:** Each exception carries typed context fields (entity_type, entity_id, etc.) — not just message strings
- **D-47:** Exception class names serve as error codes — no separate ErrorCode enum system

### Module Boundaries
- **D-48:** Inter-service communication is HTTP only. Kafka events are internal to Core (between Core's own components).
- **D-49:** Each service defines its own request/response models independently — no shared contracts imported from Core
- **D-50:** Debouncing is purely an infrastructure/adapter concern — domain is oblivious. No debounce awareness in Phase 1.

### Use Case Design
- **D-51:** One class per use case with `execute()` method
- **D-52:** Use cases accept primitive inputs directly (no input DTOs), return domain entities
- **D-53:** Constructor injection for dependencies — ports passed via `__init__`, wired at composition root

### Domain Events (6 total)
- **D-54:** StreamDataPointCreated — emitted by IngestStreamData (no DB write, for latency)
- **D-55:** StreamUpdated — emitted by ProcessStreamDataPoint after persisting
- **D-56:** MetricUpdated — emitted by ProcessStreamUpdate after metric calculation
- **D-57:** AnomalyDetected — emitted by MetricMonitor via EventPublisher
- **D-58:** InsightCreated — emitted by RunInvestigation after producing an Insight
- **D-59:** MessageCreated — emitted by HandleMessage, triggers Orchestrate

### Use Cases (7 total)
- **D-60:** IngestStreamData — receives raw data, validates in memory via Pydantic, emits StreamDataPointCreated only (no DB write, no repository dependency — just EventPublisher)
- **D-61:** ProcessStreamDataPoint — reacts to StreamDataPointCreated, stores data point to DB, emits StreamUpdated
- **D-62:** ProcessStreamUpdate — reacts to StreamUpdated, runs MetricsCalculator, saves metric, emits MetricUpdated
- **D-63:** MonitorMetric — reacts to MetricUpdated, runs MetricMonitor (which emits AnomalyDetected via EventPublisher internally)
- **D-64:** RunInvestigation — reacts to AnomalyDetected or ad-hoc trigger, creates Investigation entity, calls Investigator port (returns InvestigatorResult with steps + findings + tokens_used), creates Insight from result, persists both, emits InsightCreated, creates Invocation record
- **D-65:** HandleMessage — receives user message, adds to Thread, emits MessageCreated, creates Invocation record
- **D-66:** Orchestrate — reacts to MessageCreated and InsightCreated via drain loop: reads pending Invocations, passes (thread + invocations) to Agent, loops until drained, stores all responses in Thread, delivers only final response via MessageDeliverer

### Investigator Port
- **D-67:** Use case orchestrates, Investigator just runs — receives Investigation entity + context dict, returns InvestigatorResult (steps, findings narrative, tokens_used). Use case creates Insight from result.

### Agent Port
- **D-68:** Agent.process(thread: Thread, invocations: list[Invocation]) -> str — receives full thread history + pending invocations, returns response text

### Deferred to v2
- **D-69:** Scheduled/deterministic investigators (INTL-01) — deferred to v2
- **D-70:** Query use cases (GetMetrics, GetInsights, etc.) — deferred to v2

### Claude's Discretion
- Which domain concepts warrant dedicated value objects beyond enums and plain types
- Specific method signatures on repository ports (beyond save/get_by_id)
- Internal structure of InvestigatorResult and InvestigationStep fields

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Project vision, constraints, team context, key decisions
- `.planning/REQUIREMENTS.md` — v1 requirements with traceability to phases
- `.planning/ROADMAP.md` — Phase breakdown with success criteria

### Architecture (pending)
- Architecture diagram — user will share before planning. Naming conventions (e.g., "Investigator" not "InvestigationRunner") come from this diagram.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None yet — Phase 1 establishes all patterns

### Integration Points
- Core exposes HTTP endpoints consumed by Connector Service and Channels Service
- Core uses Kafka internally for event-driven communication between its own components
- No shared contracts — each service defines its own models independently

</code_context>

<specifics>
## Specific Ideas

- Naming must follow the architecture diagram (to be shared): "Investigator" (not InvestigationRunner), "MetricsCalculator", "MetricMonitor", "Orchestrate" (use case), "Agent" (secondary port)
- Stream and Metric use composite keys instead of UUIDs — they are logical buckets, not independently identifiable entities
- IngestStreamData is deliberately lightweight (no DB write) for latency — the persistence happens in ProcessStreamDataPoint downstream
- The Orchestrate drain loop pattern is a core architectural decision — it solves back-to-back messages and rapid insight arrivals elegantly using Kafka partition ordering guarantees

</specifics>

<deferred>
## Deferred Ideas

- Scheduled/deterministic investigators — deferred to v2 (removes Scheduler port from Phase 1)
- Query use cases (read-only endpoints) — deferred to v2
- Time window aggregation strategy for metrics — deferred to Phase 3 (depends on anomaly detection algorithm)
- Agent tool wiring (ADK-specific) — deferred to Phase 4
- Credential entity and store — belongs to Connector Service domain, not Core

### Requirement Remapping Needed
- CRED-01, CRED-02, CRED-04 currently mapped to Phase 2 (Core Infrastructure) but should map to Connector Service phases since credentials are not a Core concern

</deferred>

---

*Phase: 01-core-domain-ports*
*Context gathered: 2026-03-29*
