"""Tests for MonitorMetric use case."""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.application.ports.metric_monitor import AnomalyResult
from core.application.use_cases.monitor_metric import MonitorMetric
from core.domain.entities.metric import Metric
from core.domain.enums import MetricType
from core.domain.events.domain_events import AnomalyDetected
from tests.fakes.event_publisher import InMemoryEventPublisher
from tests.fakes.metric_monitor import FakeMetricMonitor
from tests.fakes.repositories import InMemoryMetricRepository


@pytest.fixture
def use_case(
    metric_repo: InMemoryMetricRepository,
    metric_monitor: FakeMetricMonitor,
    event_publisher: InMemoryEventPublisher,
) -> MonitorMetric:
    return MonitorMetric(
        metric_repo=metric_repo,
        metric_monitor=metric_monitor,
        event_publisher=event_publisher,
    )


@pytest.mark.asyncio
async def test_fetches_metric_and_calls_monitor(
    use_case: MonitorMetric,
    metric_repo: InMemoryMetricRepository,
    metric_monitor: FakeMetricMonitor,
) -> None:
    project_id = uuid4()
    metric = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=project_id)
    await metric_repo.save(metric)

    await use_case.execute(metric_type="pr_cycle_time", project_id=project_id)

    assert len(metric_monitor.checked_metrics) == 1
    assert metric_monitor.checked_metrics[0] == metric


@pytest.mark.asyncio
async def test_noop_when_metric_not_found(
    use_case: MonitorMetric,
    metric_monitor: FakeMetricMonitor,
) -> None:
    await use_case.execute(metric_type="pr_cycle_time", project_id=uuid4())

    assert len(metric_monitor.checked_metrics) == 0


@pytest.mark.asyncio
async def test_publishes_anomaly_detected_when_anomaly_found(
    metric_repo: InMemoryMetricRepository,
    event_publisher: InMemoryEventPublisher,
) -> None:
    anomaly = AnomalyResult(
        severity="high",
        description="PR cycle time exceeded threshold",
        metric_value=15.0,
        threshold=10.0,
    )
    monitor = FakeMetricMonitor(preset_anomaly=anomaly)

    use_case = MonitorMetric(
        metric_repo=metric_repo,
        metric_monitor=monitor,
        event_publisher=event_publisher,
    )

    project_id = uuid4()
    metric = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=project_id)
    await metric_repo.save(metric)

    await use_case.execute(metric_type="pr_cycle_time", project_id=project_id)

    assert len(event_publisher.events) == 1
    event = event_publisher.events[0]
    assert isinstance(event, AnomalyDetected)
    assert event.severity == "high"
    assert event.metric_value == 15.0
    assert event.threshold == 10.0
    assert event.project_id == project_id


@pytest.mark.asyncio
async def test_no_event_when_no_anomaly(
    use_case: MonitorMetric,
    metric_repo: InMemoryMetricRepository,
    event_publisher: InMemoryEventPublisher,
) -> None:
    project_id = uuid4()
    metric = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=project_id)
    await metric_repo.save(metric)

    await use_case.execute(metric_type="pr_cycle_time", project_id=project_id)

    assert len(event_publisher.events) == 0
