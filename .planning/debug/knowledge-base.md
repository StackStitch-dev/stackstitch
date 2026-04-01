# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## domain-events-ownership -- Domain events created in use cases instead of entities; port publishes events
- **Date:** 2026-03-31
- **Error patterns:** domain events, use case creates events, entity events, port publishes events, MetricMonitor, EventPublisher, _events, flush_events, collect_event, StreamUpdated, MetricUpdated, InsightCreated, MessageCreated, AnomalyDetected
- **Root cause:** Three architectural violations: (1) Stream and Metric entities lacked _events mechanism entirely. (2) All entities with _events had domain methods that did not collect events -- use cases created events manually instead. (3) MetricMonitor port published events internally instead of returning data for the use case to handle event creation/publishing.
- **Fix:** Added _events/collect_event/flush_events to Stream and Metric. Made entity domain methods (add_data_point, add_message, model_post_init) collect appropriate events. Changed use cases to harvest events via flush_events() and publish via publish_many(). Changed MetricMonitor port to return AnomalyResult instead of publishing events internally. MonitorMetric use case now creates/publishes AnomalyDetected from returned data.
- **Files changed:** core/src/core/domain/entities/stream.py, core/src/core/domain/entities/metric.py, core/src/core/domain/entities/thread.py, core/src/core/domain/entities/insight.py, core/src/core/application/ports/metric_monitor.py, core/src/core/application/use_cases/process_stream_data_point.py, core/src/core/application/use_cases/process_stream_update.py, core/src/core/application/use_cases/monitor_metric.py, core/src/core/application/use_cases/run_investigation.py, core/src/core/application/use_cases/handle_message.py, core/tests/fakes/metric_monitor.py, core/tests/use_cases/test_monitor_metric.py, core/tests/domain/test_entities.py, core/tests/test_fakes.py
---
