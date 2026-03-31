"""Tests for MonitorMetric use case."""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.application.use_cases.monitor_metric import MonitorMetric
from core.domain.entities.metric import Metric
from core.domain.enums import MetricType
from tests.fakes.metric_monitor import FakeMetricMonitor
from tests.fakes.repositories import InMemoryMetricRepository


@pytest.fixture
def use_case(
    metric_repo: InMemoryMetricRepository,
    metric_monitor: FakeMetricMonitor,
) -> MonitorMetric:
    return MonitorMetric(
        metric_repo=metric_repo,
        metric_monitor=metric_monitor,
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
