"""ProcessStreamDataPoint use case -- persists data point and publishes entity events (D-61)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from core.application.ports.event_publisher import EventPublisher
from core.application.ports.repositories import StreamRepository
from core.domain.entities.stream import Stream, StreamDataPoint
from core.domain.enums import StreamType


class ProcessStreamDataPoint:
    """Persists a stream data point to StreamRepository and publishes entity-collected events."""

    def __init__(
        self,
        stream_repo: StreamRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._stream_repo = stream_repo
        self._event_publisher = event_publisher

    async def execute(
        self,
        source: str,
        stream_type: str,
        project_id: UUID,
        timestamp: datetime,
        data: dict[str, Any],
    ) -> None:
        stream_type_enum = StreamType(stream_type)

        stream = await self._stream_repo.get_by_key(source, stream_type_enum, project_id)
        if stream is None:
            stream = Stream(
                source=source,
                stream_type=stream_type_enum,
                project_id=project_id,
            )

        data_point = StreamDataPoint(timestamp=timestamp, data=data)
        stream.add_data_point(data_point)

        await self._stream_repo.save(stream)

        events = stream.flush_events()
        await self._event_publisher.publish_many(events)
