from __future__ import annotations

import abc

from core.domain.entities.metric import MetricDataPoint
from core.domain.entities.stream import Stream


class MetricsCalculator(abc.ABC):
    """Port for computing metric data points from stream data (D-23).

    Called by use cases as a secondary port, not event-triggered.
    """

    @abc.abstractmethod
    async def calculate(self, stream: Stream) -> list[MetricDataPoint]: ...
