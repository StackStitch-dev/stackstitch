# Phase 2a: Docker Compose & MongoDB Adapters - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Docker Compose environment that starts all infrastructure with one command, plus MongoDB repository adapters implementing all 6 port interfaces defined in Phase 1. This is the first infrastructure phase — bringing real persistence to the pure domain layer.

**NOT in scope:** Kafka consumers/producers (Phase 2b), credential encryption (Phase 2c), REST API endpoints beyond health check, any business logic changes to domain layer.

</domain>

<decisions>
## Implementation Decisions

### Docker Compose Topology
- **D-01:** Kafka runs in KRaft mode (no ZooKeeper container). Single Kafka container with built-in metadata management.
- **D-02:** Dev observability tools included: Mongo Express (MongoDB web UI) and Kafka UI (Redpanda Console or similar) for debugging.
- **D-03:** Core service runs as a Docker container with a minimal FastAPI stub — only a `/health` endpoint. Proves the service boots and connects to MongoDB. No Kafka consumers in this phase.

### MongoDB Document Mapping
- **D-04:** Domain model does NOT map 1:1 to DB model. Parent entities (Stream, Metric, Thread) are virtual — they have no documents. Only child/leaf entities are persisted as individual documents.
- **D-05:** Collection naming follows the aggregate name, containing child documents:
  - `streams` → StreamDataPoint documents
  - `metrics` → MetricDataPoint documents
  - `threads` → Message documents
  - `insights` → Insight documents
  - `investigations` → Investigation documents (with InvestigationSteps embedded)
  - `invocations` → Invocation documents
- **D-06:** Composite-key entities (StreamDataPoint, MetricDataPoint) reference their logical parent via denormalized key fields (e.g., `source`, `stream_type`, `project_id` on each StreamDataPoint document). No parent_id reference object.
- **D-07:** UUID-identified entities (Insight, Investigation, Invocation) use UUID string as MongoDB `_id`. No ObjectId, no Binary UUID.
- **D-08:** StreamDataPoint and MetricDataPoint documents use their domain UUID as `_id` (string).
- **D-09:** Message documents in the `threads` collection reference their parent thread via `thread_id` field.
- **D-10:** InvestigationStep objects are embedded within the Investigation document (not a separate collection). Low cardinality, always loaded together.
- **D-11:** Adapters ensure indexes on startup (ensure_index/create_index). No separate migration scripts.
- **D-12:** Repository `get_by_key()` (for Stream, Metric) and `get_by_id()` (for Thread) assembles the virtual parent entity by querying the child collection and constructing the domain object with the adapter. Domain layer stays unchanged.

### MongoDB Driver
- **D-13:** Raw Motor (async) driver. No Beanie ODM. The adapter IS the mapping layer — aligns with hexagonal architecture. No extra abstraction between ports and MongoDB.

### Adapter Code Location
- **D-14:** MongoDB adapters live inside the core package: `core/src/core/infrastructure/adapters/mongodb/`
- **D-15:** Shared MongoDB connection module in the infrastructure layer (e.g., `core/src/core/infrastructure/adapters/mongodb/connection.py`). Provides Motor client and database object. Adapters receive `AsyncIOMotorDatabase` via constructor injection.
- **D-16:** One adapter file per repository port (e.g., `stream_repository.py`, `metric_repository.py`, etc.)

### Integration Test Strategy
- **D-17:** Integration tests use testcontainers to spin up real MongoDB in Docker. Self-contained, no dependency on docker compose running. CI-friendly.
- **D-18:** Shared container per test session, clean database per test function (drop/create). Fast startup, good isolation.
- **D-19:** Full round-trip coverage: every repository port method (save, get_by_key, get_by_id, get_pending_by_thread_id, save_many, get_by_project_id, etc.) has at least one integration test.

### Claude's Discretion
- Specific index definitions per collection (compound indexes on key fields, etc.)
- Docker Compose port mappings and volume configuration
- Health endpoint implementation details
- Test fixture design and helper utilities
- Dockerfile multi-stage build structure for Core service

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Project vision, constraints, team context, key decisions
- `.planning/REQUIREMENTS.md` — v1 requirements with traceability (INFR-01, INFR-02 for this phase)
- `.planning/ROADMAP.md` — Phase breakdown with success criteria

### Phase 1 Domain Layer
- `core/src/core/application/ports/repositories.py` — All 6 repository port interfaces that adapters must implement
- `core/src/core/domain/entities/` — All domain entity definitions (Stream, Metric, Insight, Investigation, Thread, Invocation)
- `core/src/core/domain/enums.py` — Domain enums (StreamType, MetricType, etc.)
- `.planning/phases/01-core-domain-ports/01-CONTEXT.md` — Phase 1 decisions (D-16 through D-27 on entity design, D-35 on async ports)

### Stack Reference
- `CLAUDE.md` §Technology Stack — Motor, PyMongo, testcontainers, FastAPI, Docker versions and rationale

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- 6 repository port ABCs in `core/src/core/application/ports/repositories.py` — exact method signatures adapters must implement
- Domain entities with Pydantic BaseModel — serialization to dict is built-in (`model_dump()`)
- In-memory fake repositories in Phase 1 tests — can reference for expected behavior patterns
- `core/pyproject.toml` — existing project config to extend with Motor dependency

### Established Patterns
- All port methods are `async def` (D-35) — adapters must be async (Motor)
- Constructor injection for dependencies (D-53) — adapters will receive `AsyncIOMotorDatabase`
- Pydantic BaseModel entities with `model_dump()` / `model_validate()` — natural dict conversion for MongoDB documents
- Composite keys for Stream `(source, stream_type, project_id)` and Metric `(metric_type, project_id)` — not UUIDs
- UUID identity for Insight, Investigation, Thread, Invocation — generated at creation

### Integration Points
- Docker Compose: MongoDB (port 27017), Kafka (port 9092), Core FastAPI (port TBD), Mongo Express (port 8081), Kafka UI (port TBD)
- Core service connects to MongoDB via Motor async client
- Kafka is present in compose but not consumed until Phase 2b

</code_context>

<specifics>
## Specific Ideas

- The key insight is that domain model and DB model are intentionally different. Domain has rich aggregates (Stream with embedded DataPoints), but MongoDB stores flat child documents. The adapter is the translation layer that decomposes on write and assembles on read.
- Collection names match the aggregate name (`streams`, `metrics`, `threads`) but contain child documents, not parent documents.
- This pattern avoids MongoDB's 16MB document limit entirely — no embedded arrays that grow unboundedly.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02A-docker-compose-mongodb-adapters*
*Context gathered: 2026-04-02*
