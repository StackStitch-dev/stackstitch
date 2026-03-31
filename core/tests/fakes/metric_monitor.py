from __future__ import annotations

from core.application.ports.metric_monitor import MetricMonitor
from core.domain.entities.metric import Metric


class FakeMetricMonitor(MetricMonitor):
    """Fake MetricMonitor that records checked metrics for assertions."""

    def __init__(self) -> None:
        self.checked_metrics: list[Metric] = []

    async def check(self, metric: Metric) -> None:
        self.checked_metrics.append(metric)
