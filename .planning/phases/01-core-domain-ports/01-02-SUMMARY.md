---
phase: 01-core-domain-ports
plan: 02
subsystem: domain
tags: [hexagonal-architecture, ports, abc, in-memory-fakes, pytest-fixtures, tdd]

requires:
  - phase: 01-core-domain-ports/01
    provides: "Domain entities, enums, events, exceptions used in port signatures"
provides:
  - "12 secondary port ABCs (6 repositories + 6 service ports)"
  - "12 in-memory fakes for all ports"
  - "12 pytest fixtures for use case testing"
affects: [01-core-domain-ports/03, 02-core-infrastructure]

tech-stack:
  added: []
  patterns: ["ABC ports with async-only methods", "In-memory fakes inheriting from port ABCs", "Composite key lookups for Stream/Metric repos", "Pytest fixtures providing pre-wired fakes"]

key-files:
  created:
    - core/src/core/application/ports/repositories.py
    - core/src/core/application/ports/event_publisher.py
    - core/src/core/application/ports/investigator.py
    - core/src/core/application/ports/metrics_calculator.py
    - core/src/core/application/ports/metric_monitor.py
    - core/src/core/application/ports/agent.py
    - core/src/core/application/ports/message_deliverer.py
    - core/src/core/application/ports/__init__.py
    - core/tests/fakes/repositories.py
    - core/tests/fakes/event_publisher.py
    - core/tests/fakes/investigator.py
    - core/tests/fakes/metrics_calculator.py
    - core/tests/fakes/metric_monitor.py
    - core/tests/fakes/agent.py
    - core/tests/fakes/message_deliverer.py
    - core/tests/fakes/__init__.py
    - core/tests/test_fakes.py
  modified:
    - core/tests/conftest.py

key-decisions:
  - "All port methods async-only per D-35 -- no sync alternatives"
  - "Composite key tuples for Stream/Metric in-memory stores match domain identity pattern"
  - "FakeMetricMonitor does not emit events -- real adapter handles that via internal EventPublisher per D-24"

patterns-established:
  - "Port pattern: abc.ABC base class with @abstractmethod async methods"
  - "Fake pattern: in-memory dict storage, preset returns for service fakes, call recording for assertions"
  - "Fixture pattern: one pytest fixture per fake, pre-wired with sensible defaults"

requirements-completed: [INFR-05]

duration: 4min
completed: 2026-03-31
---

# Phase 1 Plan 2: Ports & In-Memory Fakes Summary

**12 secondary port ABCs with async contracts and matching in-memory fakes enabling zero-infrastructure use case testing**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-31T23:27:53Z
- **Completed:** 2026-03-31T23:31:26Z
- **Tasks:** 2
- **Files modified:** 18

## Accomplishments
- All 12 secondary port interfaces defined as ABCs with async-only methods
- Complete set of in-memory fakes for every port (6 repos, event publisher, 4 service fakes, message deliverer)
- 12 pytest fixtures in conftest.py ready for Plan 03 use case testing
- 22 tests verifying fake correctness (save/retrieve, composite key lookup, pending filtering, call recording)

## Task Commits

Each task was committed atomically:

1. **Task 1: Port interface definitions** - `8a50255` (feat)
2. **Task 2 RED: Failing tests for fakes** - `ab37568` (test)
3. **Task 2 GREEN: In-memory fakes and fixtures** - `282065c` (feat)

## Files Created/Modified
- `core/src/core/application/ports/repositories.py` - 6 repository port ABCs (Stream, Metric, Insight, Investigation, Thread, Invocation)
- `core/src/core/application/ports/event_publisher.py` - EventPublisher ABC with publish/publish_many
- `core/src/core/application/ports/investigator.py` - Investigator ABC per D-67
- `core/src/core/application/ports/metrics_calculator.py` - MetricsCalculator ABC per D-23
- `core/src/core/application/ports/metric_monitor.py` - MetricMonitor ABC per D-24
- `core/src/core/application/ports/agent.py` - Agent ABC per D-68
- `core/src/core/application/ports/message_deliverer.py` - MessageDeliverer ABC per D-32
- `core/src/core/application/ports/__init__.py` - Re-exports all 12 port classes
- `core/tests/fakes/repositories.py` - 6 InMemory*Repository implementations
- `core/tests/fakes/event_publisher.py` - InMemoryEventPublisher with clear() helper
- `core/tests/fakes/investigator.py` - FakeInvestigator with preset results and call recording
- `core/tests/fakes/metrics_calculator.py` - FakeMetricsCalculator with preset results
- `core/tests/fakes/metric_monitor.py` - FakeMetricMonitor recording checked metrics
- `core/tests/fakes/agent.py` - FakeAgent with preset response
- `core/tests/fakes/message_deliverer.py` - FakeMessageDeliverer recording deliveries
- `core/tests/fakes/__init__.py` - Re-exports all 12 fakes
- `core/tests/test_fakes.py` - 22 tests verifying fake behavior
- `core/tests/conftest.py` - 12 pytest fixtures for use case testing

## Decisions Made
- All port methods are async-only per D-35 -- consistent with the async-first architecture
- In-memory repository fakes use tuple keys matching domain composite identity (Stream, Metric) and UUID keys for entities with IDs
- FakeMetricMonitor only records calls, does not emit events -- the real adapter injects EventPublisher per D-24
- Added core/README.md (Rule 3 - blocking: hatch build required it)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added core/README.md for hatch build**
- **Found during:** Task 1 verification
- **Issue:** pyproject.toml references readme = "README.md" but file did not exist, causing `uv run` to fail
- **Fix:** Created minimal README.md for the core package
- **Files modified:** core/README.md
- **Verification:** `uv run python -c "from core.application.ports import ..."` succeeds
- **Committed in:** 8a50255 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Trivial fix to unblock build. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All ports and fakes ready for Plan 03 (use cases)
- Pytest fixtures provide pre-wired fakes so use case tests need zero infrastructure
- InvocationRepository.get_pending_by_thread_id ready for Orchestrate drain loop

---
*Phase: 01-core-domain-ports*
*Completed: 2026-03-31*
