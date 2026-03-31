---
phase: 01-core-domain-ports
plan: 03
subsystem: core-application-use-cases
tags: [use-cases, hexagonal, tdd, domain-logic]
dependency_graph:
  requires: [01-01, 01-02]
  provides: [all-7-use-cases, drain-loop-orchestrate, complete-core-domain]
  affects: [phase-2-adapters, phase-3-connectors]
tech_stack:
  added: []
  patterns: [constructor-injection, drain-loop, event-driven-use-cases]
key_files:
  created:
    - core/src/core/application/use_cases/ingest_stream_data.py
    - core/src/core/application/use_cases/process_stream_data_point.py
    - core/src/core/application/use_cases/process_stream_update.py
    - core/src/core/application/use_cases/monitor_metric.py
    - core/src/core/application/use_cases/run_investigation.py
    - core/src/core/application/use_cases/handle_message.py
    - core/src/core/application/use_cases/orchestrate.py
    - core/src/core/application/use_cases/__init__.py
    - core/tests/use_cases/test_ingest_stream_data.py
    - core/tests/use_cases/test_process_stream_data_point.py
    - core/tests/use_cases/test_process_stream_update.py
    - core/tests/use_cases/test_monitor_metric.py
    - core/tests/use_cases/test_run_investigation.py
    - core/tests/use_cases/test_handle_message.py
    - core/tests/use_cases/test_orchestrate.py
  modified: []
decisions:
  - Stream-to-metric type mapping uses simple 1:1 dict (PULL_REQUEST->PR_CYCLE_TIME, etc.) for Phase 1
  - ProcessStreamUpdate returns early with no event when calculator returns empty results
  - RunInvestigation creates Invocation pointing to trigger_ref as thread_id
metrics:
  duration: 6m
  completed: 2026-03-31
---

# Phase 1 Plan 3: Use Cases Summary

All 7 use cases implemented with TDD, full business logic operating on ports via constructor injection, and 97% test coverage using in-memory fakes.

## One-liner

Seven hexagonal use cases (stream pipeline, investigation, messaging, drain-loop orchestration) with 30 dedicated tests and 97% coverage, zero infrastructure dependencies.

## What Was Built

### Stream/Metric Pipeline (Task 1)
- **IngestStreamData**: Lightweight ingestion with no repository dependency (D-60). Takes raw data, creates StreamDataPoint via Pydantic validation, emits StreamDataPointCreated event.
- **ProcessStreamDataPoint**: Creates or appends to Stream, persists via StreamRepository, emits StreamUpdated (D-61).
- **ProcessStreamUpdate**: Fetches stream, runs MetricsCalculator, creates/updates Metric, emits MetricUpdated (D-62). Includes 1:1 StreamType-to-MetricType mapping for Phase 1.
- **MonitorMetric**: Fetches metric by key, delegates to MetricMonitor.check (D-63). Monitor handles AnomalyDetected emission internally.

### Investigation, Messaging, Orchestration (Task 2)
- **RunInvestigation**: Full lifecycle -- creates Investigation, transitions PENDING->RUNNING, calls Investigator port, creates Insight + Invocation on success, marks FAILED on exception (D-64).
- **HandleMessage**: Creates Thread on first message, appends Message, emits MessageCreated, creates Invocation with USER_MESSAGE source (D-65).
- **Orchestrate**: Drain loop pattern -- reads pending invocations, calls Agent.process, stores intermediate responses in Thread, continues if new invocations appear, delivers only final response via MessageDeliverer (D-30/31/32/66).

## Commits

| Hash | Message |
|------|---------|
| 8b19191 | test(01-03): add failing tests for stream/metric pipeline use cases |
| 3d13dea | feat(01-03): implement stream/metric pipeline use cases |
| 9c07161 | test(01-03): add failing tests for investigation, messaging, and orchestration use cases |
| 9b4f7ec | feat(01-03): implement investigation, messaging, and orchestration use cases |

## Test Results

- **108 tests pass** (full suite including domain entities + fakes + use cases)
- **30 use case tests** across 7 test files
- **97% coverage** across all domain and application code
- Zero infrastructure dependencies in core/src/

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **Stream-to-metric 1:1 mapping**: Used a simple dict mapping StreamType->MetricType for Phase 1. Real calculator adapter in Phase 3 will handle multiple metric types per stream.
2. **Early return on empty calculator results**: ProcessStreamUpdate skips metric save and event emission when calculator returns no data points, avoiding empty metric creation.
3. **Invocation thread_id from trigger_ref**: RunInvestigation creates its Invocation with thread_id set to trigger_ref, assuming the trigger reference points to the relevant thread.

## Known Stubs

None -- all use cases are fully wired to port interfaces with complete business logic.

## Self-Check: PASSED

- All 15 created files exist on disk
- All 4 commit hashes verified in git log
- 108 tests pass, 97% coverage confirmed
