from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from core.domain.enums import MetricType
from core.domain.events.domain_events import DomainEvent, MetricUpdated


class MetricDataPoint(BaseModel):
    """Immutable value object embedded in Metric."""

    model_config = ConfigDict(frozen=True)

    value: float
    timestamp: datetime


class Metric(BaseModel):
    """Identified by composite key (metric_type, project_id). No UUID, no created_at."""

    model_config = ConfigDict(validate_assignment=True)

    metric_type: MetricType
    project_id: UUID
    data_points: list[MetricDataPoint] = Field(default_factory=list)

    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def collect_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def flush_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events

    def add_data_point(self, data_point: MetricDataPoint) -> None:
        self.data_points.append(data_point)
        self.collect_event(
            MetricUpdated(
                metric_type=self.metric_type.value,
                project_id=self.project_id,
            )
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Metric):
            return NotImplemented
        return self.metric_type == other.metric_type and self.project_id == other.project_id

    def __hash__(self) -> int:
        return hash((self.metric_type, self.project_id))
