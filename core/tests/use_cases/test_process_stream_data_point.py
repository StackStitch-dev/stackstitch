"""Tests for ProcessStreamDataPoint use case."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from core.application.use_cases.process_stream_data_point import ProcessStreamDataPoint
from core.domain.entities.stream import Stream
from core.domain.enums import StreamType
from core.domain.events.domain_events import StreamUpdated
from tests.fakes.event_publisher import InMemoryEventPublisher
from tests.fakes.repositories import InMemoryStreamRepository


@pytest.fixture
def use_case(
    stream_repo: InMemoryStreamRepository,
    event_publisher: InMemoryEventPublisher,
) -> ProcessStreamDataPoint:
    return ProcessStreamDataPoint(
        stream_repo=stream_repo,
        event_publisher=event_publisher,
    )


@pytest.mark.asyncio
async def test_creates_new_stream_if_not_exists(
    use_case: ProcessStreamDataPoint,
    stream_repo: InMemoryStreamRepository,
) -> None:
    project_id = uuid4()
    ts = datetime.now(timezone.utc)

    await use_case.execute(
        source="github",
        stream_type="pull_request",
        project_id=project_id,
        timestamp=ts,
        data={"action": "opened"},
    )

    stream = await stream_repo.get_by_key("github", StreamType.PULL_REQUEST, project_id)
    assert stream is not None
    assert len(stream.data_points) == 1
    assert stream.data_points[0].data == {"action": "opened"}


@pytest.mark.asyncio
async def test_appends_to_existing_stream(
    use_case: ProcessStreamDataPoint,
    stream_repo: InMemoryStreamRepository,
) -> None:
    project_id = uuid4()
    existing = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=project_id)
    await stream_repo.save(existing)

    await use_case.execute(
        source="github",
        stream_type="pull_request",
        project_id=project_id,
        timestamp=datetime.now(timezone.utc),
        data={"action": "merged"},
    )

    stream = await stream_repo.get_by_key("github", StreamType.PULL_REQUEST, project_id)
    assert stream is not None
    assert len(stream.data_points) == 1
    assert stream.data_points[0].data == {"action": "merged"}


@pytest.mark.asyncio
async def test_emits_stream_updated(
    use_case: ProcessStreamDataPoint,
    event_publisher: InMemoryEventPublisher,
) -> None:
    project_id = uuid4()

    await use_case.execute(
        source="github",
        stream_type="pull_request",
        project_id=project_id,
        timestamp=datetime.now(timezone.utc),
        data={"action": "opened"},
    )

    assert len(event_publisher.events) == 1
    event = event_publisher.events[0]
    assert isinstance(event, StreamUpdated)
    assert event.source == "github"
    assert event.stream_type == "pull_request"
    assert event.project_id == project_id
