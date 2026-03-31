from __future__ import annotations

from core.application.ports.metrics_calculator import MetricsCalculator
from core.domain.entities.metric import MetricDataPoint
from core.domain.entities.stream import Stream


class FakeMetricsCalculator(MetricsCalculator):
    """Fake MetricsCalculator that returns preset results and records calls."""

    def __init__(self, preset_results: list[MetricDataPoint] | None = None) -> None:
        self.preset_results: list[MetricDataPoint] = preset_results or []
        self.calls: list[Stream] = []

    async def calculate(self, stream: Stream) -> list[MetricDataPoint]:
        self.calls.append(stream)
        return self.preset_results
