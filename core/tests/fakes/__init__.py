"""In-memory fakes for all application ports -- zero infrastructure dependencies."""

from tests.fakes.agent import FakeAgent
from tests.fakes.event_publisher import InMemoryEventPublisher
from tests.fakes.investigator import FakeInvestigator
from tests.fakes.message_deliverer import FakeMessageDeliverer
from tests.fakes.metric_monitor import FakeMetricMonitor
from tests.fakes.metrics_calculator import FakeMetricsCalculator
from tests.fakes.repositories import (
    InMemoryInsightRepository,
    InMemoryInvocationRepository,
    InMemoryInvestigationRepository,
    InMemoryMetricRepository,
    InMemoryStreamRepository,
    InMemoryThreadRepository,
)

__all__ = [
    "FakeAgent",
    "FakeInvestigator",
    "FakeMessageDeliverer",
    "FakeMetricMonitor",
    "FakeMetricsCalculator",
    "InMemoryEventPublisher",
    "InMemoryInsightRepository",
    "InMemoryInvocationRepository",
    "InMemoryInvestigationRepository",
    "InMemoryMetricRepository",
    "InMemoryStreamRepository",
    "InMemoryThreadRepository",
]
