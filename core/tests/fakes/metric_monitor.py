from __future__ import annotations

from core.application.ports.metric_monitor import AnomalyResult, MetricMonitor
from core.domain.entities.metric import Metric


class FakeMetricMonitor(MetricMonitor):
    """Fake MetricMonitor that records checked metrics and returns preset anomaly result."""

    def __init__(self, preset_anomaly: AnomalyResult | None = None) -> None:
        self.checked_metrics: list[Metric] = []
        self.preset_anomaly = preset_anomaly

    async def check(self, metric: Metric) -> AnomalyResult | None:
        self.checked_metrics.append(metric)
        return self.preset_anomaly
