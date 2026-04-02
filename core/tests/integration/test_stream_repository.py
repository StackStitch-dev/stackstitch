"""Integration tests for MongoStreamRepository."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from core.domain.entities.stream import Stream, StreamDataPoint
from core.domain.enums import StreamType
from core.infrastructure.adapters.mongodb.stream_repository import MongoStreamRepository


@pytest.fixture
async def repo(mongo_db: AsyncDatabase) -> MongoStreamRepository:
    repository = MongoStreamRepository(mongo_db)
    await repository.ensure_indexes()
    return repository


@pytest.mark.asyncio
async def test_save_and_get_by_key(repo: MongoStreamRepository) -> None:
    project_id = uuid4()
    dp1 = StreamDataPoint(
        timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        data={"pr_number": 42, "author": "alice"},
    )
    dp2 = StreamDataPoint(
        timestamp=datetime(2026, 1, 2, 14, 30, 0, tzinfo=timezone.utc),
        data={"pr_number": 43, "author": "bob"},
    )
    stream = Stream(
        source="github",
        stream_type=StreamType.PULL_REQUEST,
        project_id=project_id,
        data_points=[dp1, dp2],
    )

    await repo.save(stream)
    result = await repo.get_by_key("github", StreamType.PULL_REQUEST, project_id)

    assert result is not None
    assert result.source == "github"
    assert result.stream_type == StreamType.PULL_REQUEST
    assert result.project_id == project_id
    assert len(result.data_points) == 2
    timestamps = {dp.timestamp for dp in result.data_points}
    assert dp1.timestamp in timestamps
    assert dp2.timestamp in timestamps
    data_values = {dp.data["pr_number"] for dp in result.data_points}
    assert data_values == {42, 43}


@pytest.mark.asyncio
async def test_get_by_key_not_found(repo: MongoStreamRepository) -> None:
    result = await repo.get_by_key("nonexistent", StreamType.COMMIT, uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_save_appends_new_data_points(repo: MongoStreamRepository) -> None:
    project_id = uuid4()
    dp1 = StreamDataPoint(
        timestamp=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        data={"commit_sha": "abc123"},
    )
    stream = Stream(
        source="github",
        stream_type=StreamType.COMMIT,
        project_id=project_id,
        data_points=[dp1],
    )
    await repo.save(stream)

    dp2 = StreamDataPoint(
        timestamp=datetime(2026, 3, 2, 11, 0, 0, tzinfo=timezone.utc),
        data={"commit_sha": "def456"},
    )
    stream.data_points.append(dp2)
    await repo.save(stream)

    result = await repo.get_by_key("github", StreamType.COMMIT, project_id)
    assert result is not None
    assert len(result.data_points) == 2


@pytest.mark.asyncio
async def test_indexes_created(repo: MongoStreamRepository) -> None:
    indexes = await repo._collection.index_information()
    # Look for compound index on source, stream_type, project_id
    found = False
    for idx_info in indexes.values():
        keys = [k for k, _ in idx_info["key"]]
        if "source" in keys and "stream_type" in keys and "project_id" in keys:
            found = True
            break
    assert found, f"Compound index not found. Indexes: {indexes}"
