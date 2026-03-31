"""Tests for ProcessStreamUpdate use case."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from core.application.use_cases.process_stream_update import ProcessStreamUpdate
from core.domain.entities.metric import MetricDataPoint
from core.domain.entities.stream import Stream, StreamDataPoint
from core.domain.enums import MetricType, StreamType
from core.domain.events.domain_events import MetricUpdated
from tests.fakes.event_publisher import InMemoryEventPublisher
from tests.fakes.metrics_calculator import FakeMetricsCalculator
from tests.fakes.repositories import InMemoryMetricRepository, InMemoryStreamRepository


@pytest.fixture
def use_case(
    stream_repo: InMemoryStreamRepository,
    metric_repo: InMemoryMetricRepository,
    metrics_calculator: FakeMetricsCalculator,
    event_publisher: InMemoryEventPublisher,
) -> ProcessStreamUpdate:
    return ProcessStreamUpdate(
        stream_repo=stream_repo,
        metric_repo=metric_repo,
        metrics_calculator=metrics_calculator,
        event_publisher=event_publisher,
    )


@pytest.mark.asyncio
async def test_fetches_stream_and_runs_calculator(
    use_case: ProcessStreamUpdate,
    stream_repo: InMemoryStreamRepository,
    metrics_calculator: FakeMetricsCalculator,
) -> None:
    project_id = uuid4()
    stream = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=project_id)
    stream.add_data_point(StreamDataPoint(timestamp=datetime.now(timezone.utc), data={"n": 1}))
    await stream_repo.save(stream)

    await use_case.execute(
        source="github",
        stream_type="pull_request",
        project_id=project_id,
    )

    assert len(metrics_calculator.calls) == 1
    assert metrics_calculator.calls[0] == stream


@pytest.mark.asyncio
async def test_saves_metric_with_new_data_points(
    use_case: ProcessStreamUpdate,
    stream_repo: InMemoryStreamRepository,
    metric_repo: InMemoryMetricRepository,
    metrics_calculator: FakeMetricsCalculator,
) -> None:
    project_id = uuid4()
    stream = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=project_id)
    await stream_repo.save(stream)

    dp = MetricDataPoint(value=42.0, timestamp=datetime.now(timezone.utc))
    metrics_calculator.preset_results = [dp]

    await use_case.execute(
        source="github",
        stream_type="pull_request",
        project_id=project_id,
    )

    metric = await metric_repo.get_by_key(MetricType.PR_CYCLE_TIME, project_id)
    assert metric is not None
    assert len(metric.data_points) == 1
    assert metric.data_points[0].value == 42.0


@pytest.mark.asyncio
async def test_creates_new_metric_if_not_exists(
    use_case: ProcessStreamUpdate,
    stream_repo: InMemoryStreamRepository,
    metric_repo: InMemoryMetricRepository,
    metrics_calculator: FakeMetricsCalculator,
) -> None:
    project_id = uuid4()
    stream = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=project_id)
    await stream_repo.save(stream)

    dp = MetricDataPoint(value=10.0, timestamp=datetime.now(timezone.utc))
    metrics_calculator.preset_results = [dp]

    await use_case.execute(
        source="github",
        stream_type="pull_request",
        project_id=project_id,
    )

    metric = await metric_repo.get_by_key(MetricType.PR_CYCLE_TIME, project_id)
    assert metric is not None
    assert metric.metric_type == MetricType.PR_CYCLE_TIME


@pytest.mark.asyncio
async def test_emits_metric_updated(
    use_case: ProcessStreamUpdate,
    stream_repo: InMemoryStreamRepository,
    metrics_calculator: FakeMetricsCalculator,
    event_publisher: InMemoryEventPublisher,
) -> None:
    project_id = uuid4()
    stream = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=project_id)
    await stream_repo.save(stream)

    dp = MetricDataPoint(value=5.0, timestamp=datetime.now(timezone.utc))
    metrics_calculator.preset_results = [dp]

    await use_case.execute(
        source="github",
        stream_type="pull_request",
        project_id=project_id,
    )

    assert len(event_publisher.events) == 1
    event = event_publisher.events[0]
    assert isinstance(event, MetricUpdated)
    assert event.metric_type == "pr_cycle_time"
    assert event.project_id == project_id


@pytest.mark.asyncio
async def test_noop_when_stream_not_found(
    use_case: ProcessStreamUpdate,
    metrics_calculator: FakeMetricsCalculator,
    event_publisher: InMemoryEventPublisher,
) -> None:
    await use_case.execute(
        source="github",
        stream_type="pull_request",
        project_id=uuid4(),
    )

    assert len(metrics_calculator.calls) == 0
    assert len(event_publisher.events) == 0
