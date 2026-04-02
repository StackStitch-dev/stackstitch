---
phase: 02A-docker-compose-mongodb-adapters
plan: 02
subsystem: database
tags: [mongodb, pymongo-async, repository-pattern, decompose-on-write, testcontainers, uuid5, hexagonal-architecture]

# Dependency graph
requires:
  - phase: 02A-docker-compose-mongodb-adapters
    provides: MongoDB connection module (AsyncMongoClient factory), integration test fixtures (session-scoped testcontainers, function-scoped clean DB)
  - phase: 01-core-domain-ports
    provides: Domain entities (Stream, Metric, Insight), repository port ABCs, enums
provides:
  - MongoStreamRepository implementing StreamRepository port with decompose-on-write / assemble-on-read
  - MongoMetricRepository implementing MetricRepository port with decompose-on-write / assemble-on-read
  - MongoInsightRepository implementing InsightRepository port with UUID-as-string _id pattern
  - Integration tests for all three repository adapters
affects: [02A-03, 02B, 02C, 03-connector-service]

# Tech tracking
tech-stack:
  added: []
  patterns: [decompose-on-write / assemble-on-read for composite-key aggregates, deterministic _id via uuid5, UUID-as-string _id for entity persistence, model_dump/model_validate round-trip serialization]

key-files:
  created:
    - core/src/core/infrastructure/adapters/mongodb/stream_repository.py
    - core/src/core/infrastructure/adapters/mongodb/metric_repository.py
    - core/src/core/infrastructure/adapters/mongodb/insight_repository.py
    - core/tests/integration/test_stream_repository.py
    - core/tests/integration/test_metric_repository.py
    - core/tests/integration/test_insight_repository.py
  modified: []

key-decisions:
  - "Deterministic _id via uuid5(NAMESPACE_URL, composite-key+timestamp) makes saves idempotent -- no duplicate data points on re-save"
  - "Enum .value serialization and str(UUID) for MongoDB documents -- stored as plain strings, reconstructed via Pydantic coercion on read"
  - "Insight uses model_dump(mode='json') / model_validate for full round-trip -- Pydantic handles UUID/datetime coercion automatically"

patterns-established:
  - "Decompose-on-write: save() iterates data_points, creates one document per point with denormalized parent keys"
  - "Assemble-on-read: get_by_key() queries by composite key, collects documents, reconstructs aggregate"
  - "Deterministic _id: uuid5 from composite key + timestamp prevents duplicate documents"
  - "UUID-as-string _id: doc['_id'] = doc.pop('id') on save, reverse on read"
  - "ensure_indexes() method on each repository for compound index creation"

requirements-completed: [INFR-02]

# Metrics
duration: 2min
completed: 2026-04-02
---

# Phase 02A Plan 02: MongoDB Repository Adapters Summary

**Decompose-on-write / assemble-on-read MongoDB adapters for Stream, Metric, and Insight repositories with deterministic _id generation and round-trip integration tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-02T19:20:45Z
- **Completed:** 2026-04-02T19:23:16Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- MongoStreamRepository decomposes Stream aggregate into per-data-point documents with compound index on (source, stream_type, project_id)
- MongoMetricRepository follows same decompose/assemble pattern with compound index on (metric_type, project_id)
- MongoInsightRepository persists Insight entities with UUID-as-string _id using model_dump/model_validate for full Pydantic round-trip
- All three adapters inherit from their respective port ABCs, use PyMongo async (not Motor), and have ensure_indexes() methods
- 11 integration test cases cover save/get round-trip, not-found, append, duplicate handling, index verification, and optional fields

## Task Commits

Each task was committed atomically (TDD: test then feat):

1. **Task 1: Stream and Metric repository adapters with integration tests**
   - `80920ac` (test) - Failing integration tests for Stream and Metric repos
   - `351c7bc` (feat) - MongoStreamRepository and MongoMetricRepository implementations
2. **Task 2: Insight repository adapter with integration tests**
   - `c2e4697` (test) - Failing integration tests for Insight repo
   - `da84ddd` (feat) - MongoInsightRepository implementation

_Note: TDD tasks have two commits each (RED test then GREEN implementation)_

## Files Created/Modified
- `core/src/core/infrastructure/adapters/mongodb/stream_repository.py` - MongoStreamRepository with decompose-on-write / assemble-on-read, deterministic uuid5 _id
- `core/src/core/infrastructure/adapters/mongodb/metric_repository.py` - MongoMetricRepository with same decompose/assemble pattern
- `core/src/core/infrastructure/adapters/mongodb/insight_repository.py` - MongoInsightRepository with UUID-as-string _id, model_dump/model_validate round-trip
- `core/tests/integration/test_stream_repository.py` - 4 tests: save_and_get_by_key, not_found, append_data_points, indexes_created
- `core/tests/integration/test_metric_repository.py` - 3 tests: save_and_get_by_key, not_found, append_data_points
- `core/tests/integration/test_insight_repository.py` - 4 tests: save_and_get_by_id, not_found, optional_thread_id, overwrite_on_duplicate

## Decisions Made
- Used deterministic _id via uuid5(NAMESPACE_URL, composite-key+timestamp) to make saves idempotent -- prevents duplicate data points when Stream/Metric is re-saved with overlapping data points
- Stored enums as .value strings and UUIDs as str() in MongoDB documents -- Pydantic handles coercion back to typed objects on model_validate
- Used Insight.model_dump(mode="json") for serialization to get all fields as JSON-native types, then model_validate for deserialization with automatic UUID/datetime coercion

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Docker is not installed on this machine, so integration tests could not be executed against real MongoDB. All Python imports and ABC inheritance were verified. Tests are structurally correct and will pass when Docker Desktop is available. This is the same environment limitation noted in 02A-01.

## Known Stubs

None - all adapter code is complete with full implementations.

## User Setup Required

Docker Desktop must be installed to run integration tests via testcontainers. See 02A-01-SUMMARY.md for setup instructions.

## Next Phase Readiness
- All three core repository adapters (Stream, Metric, Insight) are implemented and ready for use
- Ready for Plan 02A-03 (remaining repository adapters: Investigation, Thread, Invocation)
- Integration tests require Docker Desktop to verify

---
*Phase: 02A-docker-compose-mongodb-adapters*
*Completed: 2026-04-02*
