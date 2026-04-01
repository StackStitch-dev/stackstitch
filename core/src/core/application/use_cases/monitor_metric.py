"""MonitorMetric use case -- runs MetricMonitor.check and publishes anomaly events (D-63)."""

from __future__ import annotations

from uuid import UUID

from core.application.ports.event_publisher import EventPublisher
from core.application.ports.metric_monitor import MetricMonitor
from core.application.ports.repositories import MetricRepository
from core.domain.enums import MetricType
from core.domain.events.domain_events import AnomalyDetected


class MonitorMetric:
    """Fetches a metric by key, invokes MetricMonitor.check, and publishes AnomalyDetected if found.

    Event publishing is the use case's responsibility -- ports only return data.
    """

    def __init__(
        self,
        metric_repo: MetricRepository,
        metric_monitor: MetricMonitor,
        event_publisher: EventPublisher,
    ) -> None:
        self._metric_repo = metric_repo
        self._metric_monitor = metric_monitor
        self._event_publisher = event_publisher

    async def execute(self, metric_type: str, project_id: UUID) -> None:
        metric_type_enum = MetricType(metric_type)

        metric = await self._metric_repo.get_by_key(metric_type_enum, project_id)
        if metric is None:
            return  # noop

        anomaly = await self._metric_monitor.check(metric)
        if anomaly is not None:
            event = AnomalyDetected(
                metric_type=metric_type,
                project_id=project_id,
                severity=anomaly.severity,
                description=anomaly.description,
                metric_value=anomaly.metric_value,
                threshold=anomaly.threshold,
            )
            await self._event_publisher.publish(event)
