"""ProcessStreamUpdate use case -- runs calculator, saves metric, publishes entity events (D-62)."""

from __future__ import annotations

from uuid import UUID

from core.application.ports.event_publisher import EventPublisher
from core.application.ports.metrics_calculator import MetricsCalculator
from core.application.ports.repositories import MetricRepository, StreamRepository
from core.domain.entities.metric import Metric
from core.domain.enums import MetricType, StreamType

# Simple 1:1 mapping for Phase 1. Real calculator adapter in Phase 3 handles multiple metric types.
STREAM_TO_METRIC_TYPE: dict[StreamType, MetricType] = {
    StreamType.PULL_REQUEST: MetricType.PR_CYCLE_TIME,
    StreamType.COMMIT: MetricType.PR_THROUGHPUT,
    StreamType.REVIEW: MetricType.REVIEW_TURNAROUND_TIME,
}


class ProcessStreamUpdate:
    """Runs MetricsCalculator on a stream, saves the resulting metric, publishes entity events."""

    def __init__(
        self,
        stream_repo: StreamRepository,
        metric_repo: MetricRepository,
        metrics_calculator: MetricsCalculator,
        event_publisher: EventPublisher,
    ) -> None:
        self._stream_repo = stream_repo
        self._metric_repo = metric_repo
        self._metrics_calculator = metrics_calculator
        self._event_publisher = event_publisher

    async def execute(
        self,
        source: str,
        stream_type: str,
        project_id: UUID,
    ) -> None:
        stream_type_enum = StreamType(stream_type)

        stream = await self._stream_repo.get_by_key(source, stream_type_enum, project_id)
        if stream is None:
            return  # noop

        new_data_points = await self._metrics_calculator.calculate(stream)
        if not new_data_points:
            return  # nothing to update

        metric_type = STREAM_TO_METRIC_TYPE[stream_type_enum]

        metric = await self._metric_repo.get_by_key(metric_type, project_id)
        if metric is None:
            metric = Metric(metric_type=metric_type, project_id=project_id)

        for dp in new_data_points:
            metric.add_data_point(dp)

        await self._metric_repo.save(metric)

        events = metric.flush_events()
        await self._event_publisher.publish_many(events)
