from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from core.domain.enums import StreamType
from core.domain.events.domain_events import DomainEvent, StreamUpdated


class StreamDataPoint(BaseModel):
    """Immutable value object embedded in Stream."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    data: dict[str, Any]


class Stream(BaseModel):
    """Identified by composite key (source, stream_type, project_id). No UUID, no created_at."""

    model_config = ConfigDict(validate_assignment=True)

    source: str
    stream_type: StreamType
    project_id: UUID
    data_points: list[StreamDataPoint] = Field(default_factory=list)

    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def collect_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def flush_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events

    def add_data_point(self, data_point: StreamDataPoint) -> None:
        self.data_points.append(data_point)
        self.collect_event(
            StreamUpdated(
                source=self.source,
                stream_type=self.stream_type.value,
                project_id=self.project_id,
            )
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Stream):
            return NotImplemented
        return (
            self.source == other.source
            and self.stream_type == other.stream_type
            and self.project_id == other.project_id
        )

    def __hash__(self) -> int:
        return hash((self.source, self.stream_type, self.project_id))
