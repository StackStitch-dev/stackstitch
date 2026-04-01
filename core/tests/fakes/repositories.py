from __future__ import annotations

from uuid import UUID

from core.application.ports.repositories import (
    InsightRepository,
    InvocationRepository,
    InvestigationRepository,
    MetricRepository,
    StreamRepository,
    ThreadRepository,
)
from core.domain.entities.insight import Insight
from core.domain.entities.investigation import Investigation
from core.domain.entities.invocation import Invocation
from core.domain.entities.metric import Metric
from core.domain.entities.stream import Stream
from core.domain.entities.thread import Thread
from core.domain.enums import InvocationStatus, MetricType, StreamType


class InMemoryStreamRepository(StreamRepository):
    """In-memory fake for StreamRepository, keyed by (source, stream_type, project_id)."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, StreamType, UUID], Stream] = {}

    async def save(self, stream: Stream) -> None:
        key = (stream.source, stream.stream_type, stream.project_id)
        self._store[key] = stream

    async def get_by_key(
        self, source: str, stream_type: StreamType, project_id: UUID
    ) -> Stream | None:
        return self._store.get((source, stream_type, project_id))


class InMemoryMetricRepository(MetricRepository):
    """In-memory fake for MetricRepository, keyed by (metric_type, project_id)."""

    def __init__(self) -> None:
        self._store: dict[tuple[MetricType, UUID], Metric] = {}

    async def save(self, metric: Metric) -> None:
        key = (metric.metric_type, metric.project_id)
        self._store[key] = metric

    async def get_by_key(
        self, metric_type: MetricType, project_id: UUID
    ) -> Metric | None:
        return self._store.get((metric_type, project_id))


class InMemoryInsightRepository(InsightRepository):
    """In-memory fake for InsightRepository, keyed by UUID."""

    def __init__(self) -> None:
        self._store: dict[UUID, Insight] = {}

    async def save(self, insight: Insight) -> None:
        self._store[insight.id] = insight

    async def get_by_id(self, insight_id: UUID) -> Insight | None:
        return self._store.get(insight_id)


class InMemoryInvestigationRepository(InvestigationRepository):
    """In-memory fake for InvestigationRepository, keyed by UUID."""

    def __init__(self) -> None:
        self._store: dict[UUID, Investigation] = {}

    async def save(self, investigation: Investigation) -> None:
        self._store[investigation.id] = investigation

    async def get_by_id(self, investigation_id: UUID) -> Investigation | None:
        return self._store.get(investigation_id)


class InMemoryThreadRepository(ThreadRepository):
    """In-memory fake for ThreadRepository, keyed by UUID."""

    def __init__(self) -> None:
        self._store: dict[UUID, Thread] = {}

    async def save(self, thread: Thread) -> None:
        self._store[thread.id] = thread

    async def get_by_id(self, thread_id: UUID) -> Thread | None:
        return self._store.get(thread_id)

    async def get_by_project_id(self, project_id: UUID) -> list[Thread]:
        return [t for t in self._store.values() if t.project_id == project_id]


class InMemoryInvocationRepository(InvocationRepository):
    """In-memory fake for InvocationRepository.

    Supports the Orchestrate drain loop via get_pending_by_thread_id.
    """

    def __init__(self) -> None:
        self._store: dict[UUID, Invocation] = {}

    async def save(self, invocation: Invocation) -> None:
        self._store[invocation.id] = invocation

    async def save_many(self, invocations: list[Invocation]) -> None:
        for invocation in invocations:
            self._store[invocation.id] = invocation

    async def get_by_id(self, invocation_id: UUID) -> Invocation | None:
        return self._store.get(invocation_id)

    async def get_pending_by_thread_id(self, thread_id: UUID) -> list[Invocation]:
        return [
            inv
            for inv in self._store.values()
            if inv.thread_id == thread_id and inv.status == InvocationStatus.PENDING
        ]
