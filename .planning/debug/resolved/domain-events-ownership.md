---
status: resolved
trigger: "Domain events are being created in use cases instead of being created by entities. Some ports publish events when they shouldn't."
created: 2026-03-31T00:00:00Z
updated: 2026-03-31T00:00:00Z
---

## Current Focus

hypothesis: Events are created inline in use cases instead of by entity domain methods; MetricMonitor port docs say it publishes events internally
test: Read all entity, use case, and port files
expecting: Entities lack event creation in domain methods; use cases construct events manually; MetricMonitor port publishes events
next_action: Apply fix across all entities and use cases

## Symptoms

expected:
1. Domain entities create and collect their own events internally via domain methods
2. Use cases harvest events from entities after domain operations, then publish via EventPublisher
3. Ports never publish events -- only use cases publish events

actual:
1. Use cases create domain events directly (e.g. StreamDataPointCreated constructed in use case code)
2. MetricMonitor port docstring says it "emits AnomalyDetected events via an internal EventPublisher"
3. Stream and Metric entities have NO events collection mechanism; Investigation, Insight, Thread, Invocation have _events but domain methods don't populate them

errors: No errors -- architectural correction. All 108 tests pass currently.

reproduction: Read use case files and entity files to see the pattern.

started: Built this way from the start in phase 1.

## Eliminated

(none)

## Evidence

- timestamp: 2026-03-31T00:01:00Z
  checked: All 6 entity files
  found: Stream and Metric lack _events/collect_event/flush_events. Investigation, Insight, Thread, Invocation have the mechanism but domain methods (start, complete, fail, add_message, mark_processing, mark_done, add_data_point) do NOT create/collect events.
  implication: No entity self-generates events. All event creation happens in use cases.

- timestamp: 2026-03-31T00:02:00Z
  checked: All 7 use case files
  found: IngestStreamData, ProcessStreamDataPoint, ProcessStreamUpdate, RunInvestigation, HandleMessage all construct events inline and publish directly. MonitorMetric delegates to MetricMonitor port which is documented to emit events internally.
  implication: Use cases are doing event creation (should be entity responsibility) and MonitorMetric delegates event publishing to a port (should be use case responsibility).

- timestamp: 2026-03-31T00:03:00Z
  checked: MetricMonitor port interface
  found: Docstring says "emits AnomalyDetected events via an internal EventPublisher injected at adapter construction time". The port returns None from check(). No way for use case to get anomaly data.
  implication: MetricMonitor needs to return anomaly info so use case can create/publish events. Port interface must change.

## Resolution

root_cause: Three architectural violations: (1) Stream and Metric entities lack _events mechanism entirely. (2) All entities with _events have domain methods that don't collect events -- use cases create events manually instead. (3) MetricMonitor port publishes events internally instead of returning data for the use case to handle event creation/publishing.

fix:
1. Added _events/collect_event/flush_events to Stream and Metric entities
2. Stream.add_data_point() now collects StreamUpdated event
3. Metric.add_data_point() now collects MetricUpdated event
4. Thread.add_message() now collects MessageCreated event
5. Insight now collects InsightCreated event on construction via model_post_init
6. Use cases (ProcessStreamDataPoint, ProcessStreamUpdate, RunInvestigation, HandleMessage) now harvest events from entities via flush_events() and publish via publish_many()
7. MetricMonitor port changed from returning None to returning AnomalyResult | None
8. MonitorMetric use case now takes EventPublisher, creates/publishes AnomalyDetected from AnomalyResult
9. FakeMetricMonitor updated to return preset_anomaly
10. IngestStreamData unchanged (no entity involved -- creates value object directly)
11. Orchestrate unchanged (adds assistant messages but doesn't need to publish those events)

verification: All 117 tests pass (9 new tests added). 99% coverage.
files_changed:
- core/src/core/domain/entities/stream.py
- core/src/core/domain/entities/metric.py
- core/src/core/domain/entities/thread.py
- core/src/core/domain/entities/insight.py
- core/src/core/application/ports/metric_monitor.py
- core/src/core/application/use_cases/process_stream_data_point.py
- core/src/core/application/use_cases/process_stream_update.py
- core/src/core/application/use_cases/monitor_metric.py
- core/src/core/application/use_cases/run_investigation.py
- core/src/core/application/use_cases/handle_message.py
- core/tests/fakes/metric_monitor.py
- core/tests/use_cases/test_monitor_metric.py
- core/tests/domain/test_entities.py
- core/tests/test_fakes.py
