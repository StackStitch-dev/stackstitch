from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class DomainEvent(BaseModel):
    """Base domain event -- immutable, timestamped, uniquely identified."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StreamDataPointCreated(DomainEvent):
    """Emitted by IngestStreamData when raw data is received."""

    source: str
    stream_type: str
    project_id: UUID
    timestamp: datetime
    data: dict[str, Any]


class StreamUpdated(DomainEvent):
    """Emitted by ProcessStreamDataPoint after persisting a data point."""

    source: str
    stream_type: str
    project_id: UUID


class MetricUpdated(DomainEvent):
    """Emitted by ProcessStreamUpdate after metric calculation."""

    metric_type: str
    project_id: UUID


class AnomalyDetected(DomainEvent):
    """Emitted by MetricMonitor when a metric exceeds statistical thresholds."""

    metric_type: str
    project_id: UUID
    severity: str
    description: str
    metric_value: float
    threshold: float


class InsightCreated(DomainEvent):
    """Emitted by RunInvestigation after producing an Insight.

    thread_id is set when the insight targets a specific thread (ad-hoc).
    When None, the insight is broadcast to all project threads (anomaly).
    """

    insight_id: UUID
    investigation_id: UUID
    project_id: UUID
    thread_id: UUID | None = None


class MessageCreated(DomainEvent):
    """Emitted by HandleMessage when a user sends a message."""

    thread_id: UUID
    message_content: str
