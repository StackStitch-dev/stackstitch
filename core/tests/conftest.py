"""Shared pytest fixtures for core tests.

Provides pre-wired in-memory fakes for all application ports.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.domain.entities.investigation import InvestigatorResult, InvestigationStep
from core.domain.enums import InvestigationStepType
from tests.fakes import (
    FakeAgent,
    FakeInvestigator,
    FakeMessageDeliverer,
    FakeMetricMonitor,
    FakeMetricsCalculator,
    InMemoryEventPublisher,
    InMemoryInsightRepository,
    InMemoryInvocationRepository,
    InMemoryInvestigationRepository,
    InMemoryMetricRepository,
    InMemoryStreamRepository,
    InMemoryThreadRepository,
)


@pytest.fixture
def event_publisher() -> InMemoryEventPublisher:
    return InMemoryEventPublisher()


@pytest.fixture
def stream_repo() -> InMemoryStreamRepository:
    return InMemoryStreamRepository()


@pytest.fixture
def metric_repo() -> InMemoryMetricRepository:
    return InMemoryMetricRepository()


@pytest.fixture
def insight_repo() -> InMemoryInsightRepository:
    return InMemoryInsightRepository()


@pytest.fixture
def investigation_repo() -> InMemoryInvestigationRepository:
    return InMemoryInvestigationRepository()


@pytest.fixture
def thread_repo() -> InMemoryThreadRepository:
    return InMemoryThreadRepository()


@pytest.fixture
def invocation_repo() -> InMemoryInvocationRepository:
    return InMemoryInvocationRepository()


@pytest.fixture
def investigator() -> FakeInvestigator:
    preset_result = InvestigatorResult(
        steps=[InvestigationStep(step_type=InvestigationStepType.REASONING, reasoning="test")],
        findings="test findings",
        tokens_used=50,
    )
    return FakeInvestigator(preset_result=preset_result)


@pytest.fixture
def metrics_calculator() -> FakeMetricsCalculator:
    return FakeMetricsCalculator(preset_results=[])


@pytest.fixture
def metric_monitor() -> FakeMetricMonitor:
    return FakeMetricMonitor()


@pytest.fixture
def agent() -> FakeAgent:
    return FakeAgent(preset_response="test response")


@pytest.fixture
def message_deliverer() -> FakeMessageDeliverer:
    return FakeMessageDeliverer()
