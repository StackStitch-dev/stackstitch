"""Integration tests for MongoMetricRepository."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from core.domain.entities.metric import Metric, MetricDataPoint
from core.domain.enums import MetricType
from core.infrastructure.adapters.mongodb.metric_repository import MongoMetricRepository


@pytest.fixture
async def repo(mongo_db: AsyncDatabase) -> MongoMetricRepository:
    repository = MongoMetricRepository(mongo_db)
    await repository.ensure_indexes()
    return repository


@pytest.mark.asyncio
async def test_save_and_get_by_key(repo: MongoMetricRepository) -> None:
    project_id = uuid4()
    dp1 = MetricDataPoint(
        value=3.5,
        timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    dp2 = MetricDataPoint(
        value=7.2,
        timestamp=datetime(2026, 1, 2, 14, 30, 0, tzinfo=timezone.utc),
    )
    metric = Metric(
        metric_type=MetricType.PR_CYCLE_TIME,
        project_id=project_id,
        data_points=[dp1, dp2],
    )

    await repo.save(metric)
    result = await repo.get_by_key(MetricType.PR_CYCLE_TIME, project_id)

    assert result is not None
    assert result.metric_type == MetricType.PR_CYCLE_TIME
    assert result.project_id == project_id
    assert len(result.data_points) == 2
    values = {dp.value for dp in result.data_points}
    assert values == {3.5, 7.2}


@pytest.mark.asyncio
async def test_get_by_key_not_found(repo: MongoMetricRepository) -> None:
    result = await repo.get_by_key(MetricType.PR_THROUGHPUT, uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_save_appends_new_data_points(repo: MongoMetricRepository) -> None:
    project_id = uuid4()
    dp1 = MetricDataPoint(
        value=1.0,
        timestamp=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    metric = Metric(
        metric_type=MetricType.REVIEW_TURNAROUND_TIME,
        project_id=project_id,
        data_points=[dp1],
    )
    await repo.save(metric)

    dp2 = MetricDataPoint(
        value=2.5,
        timestamp=datetime(2026, 3, 2, 11, 0, 0, tzinfo=timezone.utc),
    )
    metric.data_points.append(dp2)
    await repo.save(metric)

    result = await repo.get_by_key(MetricType.REVIEW_TURNAROUND_TIME, project_id)
    assert result is not None
    assert len(result.data_points) == 2
