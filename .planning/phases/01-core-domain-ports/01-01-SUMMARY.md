---
phase: 01-core-domain-ports
plan: 01
subsystem: domain
tags: [pydantic, ddd, hexagonal-architecture, domain-events, python]

# Dependency graph
requires: []
provides:
  - "All domain entities (Stream, Metric, Investigation, Insight, Thread, Invocation)"
  - "All domain events (6 frozen Pydantic models)"
  - "All domain enums (10 string enums)"
  - "Domain exception hierarchy with typed context"
  - "Core project scaffold with hexagonal directory structure"
affects: [01-02, 01-03, 02-core-infrastructure]

# Tech tracking
tech-stack:
  added: [pydantic 2.12, pytest 9.0, pytest-asyncio, ruff, mypy, hatchling]
  patterns: [pydantic-basemodel-entities, frozen-value-objects, composite-key-equality, private-attr-event-collection, domain-exception-hierarchy]

key-files:
  created:
    - core/pyproject.toml
    - core/src/core/domain/enums.py
    - core/src/core/domain/exceptions.py
    - core/src/core/domain/events/domain_events.py
    - core/src/core/domain/entities/stream.py
    - core/src/core/domain/entities/metric.py
    - core/src/core/domain/entities/investigation.py
    - core/src/core/domain/entities/insight.py
    - core/src/core/domain/entities/thread.py
    - core/src/core/domain/entities/invocation.py
    - core/tests/domain/test_entities.py
    - core/tests/domain/test_events.py
    - core/tests/domain/test_exceptions.py
  modified: []

key-decisions:
  - "Used hatchling build backend instead of uv_build for reliable src layout support"
  - "InvalidEntityStateError accepts Any for entity_id to support composite-key entities without UUID"

patterns-established:
  - "Pydantic BaseModel with ConfigDict(validate_assignment=True) for mutable entities"
  - "Pydantic BaseModel with ConfigDict(frozen=True) for immutable value objects"
  - "PrivateAttr(default_factory=list) for domain event collection on entities"
  - "Composite-key __eq__/__hash__ for Stream (source, stream_type, project_id) and Metric (metric_type, project_id)"
  - "String enums (str, Enum) for all domain enumerations"
  - "DomainError hierarchy with typed context kwargs"

requirements-completed: [INFR-05]

# Metrics
duration: 5min
completed: 2026-03-31
---

# Phase 1 Plan 01: Domain Entities Summary

**Complete domain layer with 6 entity types, 10 enums, 6 frozen domain events, exception hierarchy, and 56 passing TDD tests -- zero infrastructure dependencies**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-31T23:18:53Z
- **Completed:** 2026-03-31T23:23:39Z
- **Tasks:** 2
- **Files modified:** 24

## Accomplishments
- Full core project scaffold with hexagonal directory structure (domain/entities, domain/events, application/ports, application/use_cases)
- All 6 domain entities implemented with Pydantic v2: Stream, Metric, Investigation, Insight, Thread, Invocation
- Investigation state machine (PENDING->RUNNING->COMPLETED|FAILED) with InvalidEntityStateError guards
- 56 domain tests passing via TDD (RED-GREEN cycle) covering entities, events, and exceptions

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffold, base types, enums, exceptions, and domain events** - `22345d3` (feat)
2. **Task 2 RED: Failing tests for entities, events, exceptions** - `f3fefd8` (test)
3. **Task 2 GREEN: Implement all domain entities** - `ec0ff4a` (feat)
4. **Chore: Add gitignore and lockfile** - `b17f651` (chore)

## Files Created/Modified
- `core/pyproject.toml` - Project config with pydantic, pytest, ruff, mypy (strict mode)
- `core/src/core/domain/enums.py` - 10 string enums (StreamType, MetricType, InvestigationStatus, etc.)
- `core/src/core/domain/exceptions.py` - DomainError hierarchy with typed context fields
- `core/src/core/domain/events/domain_events.py` - 6 frozen domain events (StreamDataPointCreated through MessageCreated)
- `core/src/core/domain/entities/stream.py` - Stream + StreamDataPoint with composite-key equality
- `core/src/core/domain/entities/metric.py` - Metric + MetricDataPoint with composite-key equality
- `core/src/core/domain/entities/investigation.py` - Investigation state machine + InvestigationStep + InvestigatorResult
- `core/src/core/domain/entities/insight.py` - Semi-structured Insight with metadata dict
- `core/src/core/domain/entities/thread.py` - Thread + frozen Message value object
- `core/src/core/domain/entities/invocation.py` - Invocation with PENDING->PROCESSING->DONE transitions
- `core/tests/domain/test_entities.py` - 28 entity tests
- `core/tests/domain/test_events.py` - 12 event tests (instantiation + immutability)
- `core/tests/domain/test_exceptions.py` - 9 exception tests

## Decisions Made
- Used hatchling build backend instead of uv_build -- uv_build could not resolve the `core` module name from `stackstitch-core` package name in src layout
- Made InvalidEntityStateError.entity_id accept Any type instead of UUID only -- Investigation entities use UUID but composite-key entities (Stream, Metric) don't have a UUID id

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Switched build backend from uv_build to hatchling**
- **Found during:** Task 1 (project scaffold)
- **Issue:** uv_build expected module at `src/stackstitch_core/__init__.py` but our module is `core` at `src/core/__init__.py`
- **Fix:** Replaced uv_build with hatchling and added `[tool.hatch.build.targets.wheel] packages = ["src/core"]`
- **Files modified:** core/pyproject.toml
- **Verification:** `uv sync` succeeds, all imports work
- **Committed in:** 22345d3

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Build backend change was necessary to make the src layout work. No functional impact -- hatchling is a well-established build backend.

## Issues Encountered
None beyond the build backend deviation above.

## Known Stubs
None -- all entities are fully implemented with complete domain logic.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All domain types are stable contracts for Plan 02 (ports) and Plan 03 (use cases) to build against
- Entity re-exports available via `core.domain.entities` for convenient imports
- Test infrastructure (pytest with asyncio_mode=auto) is ready for async port and use case tests

---
*Phase: 01-core-domain-ports*
*Completed: 2026-03-31*

## Self-Check: PASSED
- All 13 key files exist on disk
- All 4 commit hashes verified in git log
