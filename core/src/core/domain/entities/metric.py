from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.domain.enums import MetricType


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

    def add_data_point(self, data_point: MetricDataPoint) -> None:
        self.data_points.append(data_point)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Metric):
            return NotImplemented
        return self.metric_type == other.metric_type and self.project_id == other.project_id

    def __hash__(self) -> int:
        return hash((self.metric_type, self.project_id))
