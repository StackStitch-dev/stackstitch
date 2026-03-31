"""MonitorMetric use case -- runs MetricMonitor.check on a metric (D-63)."""

from __future__ import annotations

from uuid import UUID

from core.application.ports.metric_monitor import MetricMonitor
from core.application.ports.repositories import MetricRepository
from core.domain.enums import MetricType


class MonitorMetric:
    """Fetches a metric by key and invokes MetricMonitor.check.

    MetricMonitor emits AnomalyDetected internally via its own EventPublisher (D-24).
    """

    def __init__(
        self,
        metric_repo: MetricRepository,
        metric_monitor: MetricMonitor,
    ) -> None:
        self._metric_repo = metric_repo
        self._metric_monitor = metric_monitor

    async def execute(self, metric_type: str, project_id: UUID) -> None:
        metric_type_enum = MetricType(metric_type)

        metric = await self._metric_repo.get_by_key(metric_type_enum, project_id)
        if metric is None:
            return  # noop

        await self._metric_monitor.check(metric)
