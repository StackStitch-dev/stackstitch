"""IngestStreamData use case -- lightweight ingestion, no repository dependency (D-60)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from core.application.ports.event_publisher import EventPublisher
from core.domain.entities.stream import StreamDataPoint
from core.domain.events.domain_events import StreamDataPointCreated


class IngestStreamData:
    """Validates raw data and emits StreamDataPointCreated without touching any repository."""

    def __init__(self, event_publisher: EventPublisher) -> None:
        self._event_publisher = event_publisher

    async def execute(
        self,
        source: str,
        stream_type: str,
        project_id: UUID,
        timestamp: datetime,
        data: dict[str, Any],
    ) -> StreamDataPoint:
        # Pydantic validates the data point on construction
        data_point = StreamDataPoint(timestamp=timestamp, data=data)

        event = StreamDataPointCreated(
            source=source,
            stream_type=stream_type,
            project_id=project_id,
            timestamp=timestamp,
            data=data,
        )
        await self._event_publisher.publish(event)

        return data_point
