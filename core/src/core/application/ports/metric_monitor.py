from __future__ import annotations

import abc

from pydantic import BaseModel, ConfigDict

from core.domain.entities.metric import Metric


class AnomalyResult(BaseModel):
    """Value object returned by MetricMonitor when an anomaly is detected."""

    model_config = ConfigDict(frozen=True)

    severity: str
    description: str
    metric_value: float
    threshold: float


class MetricMonitor(abc.ABC):
    """Port for monitoring metrics and detecting anomalies (D-24).

    Returns anomaly data when detected; None when no anomaly.
    Event publishing is the use case's responsibility.
    """

    @abc.abstractmethod
    async def check(self, metric: Metric) -> AnomalyResult | None: ...
