"""Tests for IngestStreamData use case."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from core.application.use_cases.ingest_stream_data import IngestStreamData
from core.domain.events.domain_events import StreamDataPointCreated
from tests.fakes.event_publisher import InMemoryEventPublisher


@pytest.fixture
def use_case(event_publisher: InMemoryEventPublisher) -> IngestStreamData:
    return IngestStreamData(event_publisher=event_publisher)


@pytest.mark.asyncio
async def test_ingest_emits_stream_data_point_created(
    use_case: IngestStreamData,
    event_publisher: InMemoryEventPublisher,
) -> None:
    project_id = uuid4()
    ts = datetime.now(timezone.utc)

    await use_case.execute(
        source="github",
        stream_type="pull_request",
        project_id=project_id,
        timestamp=ts,
        data={"action": "opened", "number": 42},
    )

    assert len(event_publisher.events) == 1
    event = event_publisher.events[0]
    assert isinstance(event, StreamDataPointCreated)
    assert event.source == "github"
    assert event.stream_type == "pull_request"
    assert event.project_id == project_id


@pytest.mark.asyncio
async def test_ingest_returns_stream_data_point(
    use_case: IngestStreamData,
) -> None:
    project_id = uuid4()
    ts = datetime.now(timezone.utc)
    data = {"action": "opened", "number": 42}

    result = await use_case.execute(
        source="github",
        stream_type="pull_request",
        project_id=project_id,
        timestamp=ts,
        data=data,
    )

    assert result.timestamp == ts
    assert result.data == data


@pytest.mark.asyncio
async def test_ingest_validates_data_via_pydantic(
    use_case: IngestStreamData,
) -> None:
    """Invalid types should raise a validation error."""
    with pytest.raises((TypeError, ValueError)):
        await use_case.execute(
            source="github",
            stream_type="pull_request",
            project_id=uuid4(),
            timestamp="not-a-datetime",  # type: ignore[arg-type]
            data="not-a-dict",  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_ingest_has_no_repository_dependency() -> None:
    """IngestStreamData.__init__ only takes EventPublisher -- no repo dependency."""
    import inspect

    sig = inspect.signature(IngestStreamData.__init__)
    params = [p for p in sig.parameters if p != "self"]
    assert params == ["event_publisher"]
