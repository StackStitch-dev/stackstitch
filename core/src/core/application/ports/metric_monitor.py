from __future__ import annotations

import abc

from core.domain.entities.metric import Metric


class MetricMonitor(abc.ABC):
    """Port for monitoring metrics and detecting anomalies (D-24).

    Returns nothing -- emits AnomalyDetected events via an internal
    EventPublisher injected at adapter construction time.
    """

    @abc.abstractmethod
    async def check(self, metric: Metric) -> None: ...
