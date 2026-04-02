"""Integration tests for MongoInsightRepository."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from core.domain.entities.insight import Insight
from core.domain.enums import InsightType
from core.infrastructure.adapters.mongodb.insight_repository import MongoInsightRepository


@pytest.fixture
async def repo(mongo_db: AsyncDatabase) -> MongoInsightRepository:
    repository = MongoInsightRepository(mongo_db)
    await repository.ensure_indexes()
    return repository


@pytest.mark.asyncio
async def test_save_and_get_by_id(repo: MongoInsightRepository) -> None:
    insight_id = uuid4()
    project_id = uuid4()
    investigation_id = uuid4()
    created = datetime(2026, 2, 15, 10, 30, 0, tzinfo=timezone.utc)

    insight = Insight(
        id=insight_id,
        project_id=project_id,
        investigation_id=investigation_id,
        title="PR cycle time spike detected",
        narrative="Cycle time increased 3x this week due to large refactoring PRs.",
        insight_type=InsightType.ANOMALY_EXPLANATION,
        metadata={"severity": "high", "affected_prs": [101, 102]},
        created_at=created,
    )

    await repo.save(insight)
    result = await repo.get_by_id(insight_id)

    assert result is not None
    assert result.id == insight_id
    assert result.project_id == project_id
    assert result.investigation_id == investigation_id
    assert result.title == "PR cycle time spike detected"
    assert result.narrative == "Cycle time increased 3x this week due to large refactoring PRs."
    assert result.insight_type == InsightType.ANOMALY_EXPLANATION
    assert result.metadata == {"severity": "high", "affected_prs": [101, 102]}
    assert result.thread_id is None
    # Compare timestamps with millisecond tolerance (MongoDB may truncate)
    assert abs((result.created_at - created).total_seconds()) < 0.001


@pytest.mark.asyncio
async def test_get_by_id_not_found(repo: MongoInsightRepository) -> None:
    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_save_with_optional_thread_id(repo: MongoInsightRepository) -> None:
    thread_id = uuid4()
    insight = Insight(
        id=uuid4(),
        project_id=uuid4(),
        investigation_id=uuid4(),
        thread_id=thread_id,
        title="Pattern detected",
        narrative="Recurring slow reviews on Fridays.",
        insight_type=InsightType.PATTERN_DETECTION,
    )

    await repo.save(insight)
    result = await repo.get_by_id(insight.id)

    assert result is not None
    assert result.thread_id == thread_id


@pytest.mark.asyncio
async def test_save_overwrites_on_duplicate_id(repo: MongoInsightRepository) -> None:
    insight_id = uuid4()
    insight = Insight(
        id=insight_id,
        project_id=uuid4(),
        investigation_id=uuid4(),
        title="Original title",
        narrative="Original narrative.",
        insight_type=InsightType.AD_HOC_RESPONSE,
    )

    await repo.save(insight)
    insight.title = "Updated title"
    await repo.save(insight)

    result = await repo.get_by_id(insight_id)
    assert result is not None
    assert result.title == "Updated title"
