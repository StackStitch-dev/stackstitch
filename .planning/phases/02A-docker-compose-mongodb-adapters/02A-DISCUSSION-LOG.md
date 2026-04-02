# Phase 2a: Docker Compose & MongoDB Adapters - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 02A-docker-compose-mongodb-adapters
**Areas discussed:** Docker Compose topology, MongoDB document mapping, Adapter code location, Integration test strategy

---

## Docker Compose Topology

### Kafka Mode

| Option | Description | Selected |
|--------|-------------|----------|
| KRaft mode | Single Kafka container, no ZooKeeper. Simpler compose file. Modern approach (production-ready since Kafka 3.5+). | ✓ |
| ZooKeeper mode | Traditional setup with separate ZooKeeper container. More resources, but battle-tested. | |

**User's choice:** KRaft mode
**Notes:** None

### Dev Observability Tools

| Option | Description | Selected |
|--------|-------------|----------|
| Bare minimum | Only MongoDB, Kafka, and Core stub. Devs use CLI tools when needed. | |
| Include UI tools | Add Mongo Express and/or Kafka UI for easier debugging. | ✓ |

**User's choice:** Include UI tools — both Mongo Express and Kafka UI (Redpanda Console)
**Notes:** None

### Core Service Stub

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI health endpoint only | Minimal container that starts FastAPI with /health. Proves the service boots and connects to MongoDB. | ✓ |
| No Core container yet | Docker Compose only starts infrastructure. Core runs locally via `uv run`. | |
| Core + basic CRUD endpoints | FastAPI with health + basic REST endpoints for one or two entities. | |

**User's choice:** FastAPI health endpoint only
**Notes:** None

---

## MongoDB Document Mapping

### Composite Key Mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Compound _id object | Use _id: {source, stream_type, project_id}. Native MongoDB uniqueness. | ✓ |
| String _id concatenation | Concatenate key fields into string like "github:pull_request:uuid". | |
| Auto-generated _id + unique index | Let MongoDB auto-generate ObjectId. Add unique compound index. | |

**User's choice:** Compound _id object
**Notes:** None

### UUID Entity Mapping

| Option | Description | Selected |
|--------|-------------|----------|
| UUID string as _id | Store domain UUID directly as _id string. Clean 1:1 mapping. | ✓ |
| Binary UUID as _id | BSON Binary subtype 4. Smaller but harder to read. | |

**User's choice:** UUID string as _id
**Notes:** None

### DataPoint Storage Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Embed all, cap later | Embed all DataPoints in parent. Address growth later. | |
| Bucket from the start | Use MongoDB bucket pattern from day one. | |
| Separate documents (user-proposed) | Each DataPoint as its own document. No embedding. | ✓ |

**User's choice:** Each DataPoint must be stored in its own document, no embed process required
**Notes:** User explicitly stated: "each DataPoint must be stored in its own document, no embed process must be required"

### Scope of Separate Documents

| Option | Description | Selected |
|--------|-------------|----------|
| All separate documents | StreamDataPoints, MetricDataPoints, and Messages each get their own collection. | ✓ |
| Only DataPoints, keep Messages embedded | DataPoints separate, Thread embeds Messages. | |

**User's choice:** All separate documents. Domain model does not need to be mapped 1:1 with the DB model.
**Notes:** "at domain level we mostly deal with streams but at db level we mostly deal with datapoints"

### Parent Document Existence

| Option | Description | Selected |
|--------|-------------|----------|
| Virtual parents (no docs) | Stream, Metric, Thread have no documents. Only children persisted. Adapter assembles on read. | ✓ |
| Separate parent collection | Parent entities get their own collection/documents. | |

**User's choice:** All virtual parents — no parent documents
**Notes:** User clarified that `streams` collection contains StreamDataPoint docs, and `threads` contains Message docs (not Thread docs).

### Parent Reference in Children

| Option | Description | Selected |
|--------|-------------|----------|
| Parent composite key fields | Denormalized key fields on each child document. | ✓ |
| Parent _id reference | Store parent's compound _id as a reference object. | |

**User's choice:** Parent composite key fields
**Notes:** None

### Collection Naming

**User's choice:** Confirmed naming: streams, metrics, threads, insights, investigations, invocations
**Notes:** User corrected that `threads` must contain Message docs, not Thread docs.

### InvestigationSteps

| Option | Description | Selected |
|--------|-------------|----------|
| Embed steps in Investigation doc | Steps always read/written together. Low cardinality. | ✓ |
| Separate steps collection | Each step as its own document. | |

**User's choice:** Embed steps
**Notes:** None

### MongoDB Driver

| Option | Description | Selected |
|--------|-------------|----------|
| Raw Motor | Direct async driver. Full control, no abstraction layer. | ✓ |
| Beanie ODM | Pydantic-native ODM on top of Motor. | |

**User's choice:** Raw Motor
**Notes:** None

---

## Adapter Code Location

### Directory Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Inside core/ package | core/src/core/infrastructure/adapters/mongodb/ | ✓ |
| Separate infra package | New top-level package (core-infra/) | |
| Flat in infrastructure/ | core/src/core/infrastructure/mongodb_*.py | |

**User's choice:** Inside core/ package
**Notes:** None

### Connection Management

| Option | Description | Selected |
|--------|-------------|----------|
| Shared connection module | A connection.py providing Motor client/db. Adapters receive db via injection. | ✓ |
| Each adapter self-contained | Each adapter manages its own connection. | |

**User's choice:** Shared connection module in the infra layer
**Notes:** User specified "this shared connection module must live in the infra layer"

---

## Integration Test Strategy

### Test Infrastructure

| Option | Description | Selected |
|--------|-------------|----------|
| testcontainers | Tests spin up own MongoDB in Docker. Self-contained, CI-friendly. | ✓ |
| Docker Compose MongoDB | Tests connect to running docker compose. | |

**User's choice:** testcontainers
**Notes:** None

### Test Isolation

| Option | Description | Selected |
|--------|-------------|----------|
| Shared container, clean DB per test | One container per session. Fresh database per test. | ✓ |
| Shared container, clean collections | One container, truncate collections per test. | |
| Container per test | New container per test function. | |

**User's choice:** Shared container, clean DB per test
**Notes:** None

### Coverage Expectation

| Option | Description | Selected |
|--------|-------------|----------|
| Full round-trip per port method | Every port method has at least one integration test. | ✓ |
| Happy path only | Save + retrieve per repository only. | |
| Happy path + error cases | Save/retrieve plus not-found, duplicates, empty results. | |

**User's choice:** Full round-trip per port method
**Notes:** None

---

## Claude's Discretion

- Specific index definitions per collection
- Docker Compose port mappings and volume configuration
- Health endpoint implementation details
- Test fixture design and helper utilities
- Dockerfile multi-stage build structure

## Deferred Ideas

None — discussion stayed within phase scope
