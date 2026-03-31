from __future__ import annotations

import abc
from uuid import UUID

from core.domain.entities.insight import Insight
from core.domain.entities.investigation import Investigation
from core.domain.entities.invocation import Invocation
from core.domain.entities.metric import Metric
from core.domain.entities.stream import Stream
from core.domain.entities.thread import Thread
from core.domain.enums import MetricType, StreamType


class StreamRepository(abc.ABC):
    """Port for persisting and retrieving Stream aggregates by composite key."""

    @abc.abstractmethod
    async def save(self, stream: Stream) -> None: ...

    @abc.abstractmethod
    async def get_by_key(
        self, source: str, stream_type: StreamType, project_id: UUID
    ) -> Stream | None: ...


class MetricRepository(abc.ABC):
    """Port for persisting and retrieving Metric aggregates by composite key."""

    @abc.abstractmethod
    async def save(self, metric: Metric) -> None: ...

    @abc.abstractmethod
    async def get_by_key(
        self, metric_type: MetricType, project_id: UUID
    ) -> Metric | None: ...


class InsightRepository(abc.ABC):
    """Port for persisting and retrieving Insight entities."""

    @abc.abstractmethod
    async def save(self, insight: Insight) -> None: ...

    @abc.abstractmethod
    async def get_by_id(self, insight_id: UUID) -> Insight | None: ...


class InvestigationRepository(abc.ABC):
    """Port for persisting and retrieving Investigation entities."""

    @abc.abstractmethod
    async def save(self, investigation: Investigation) -> None: ...

    @abc.abstractmethod
    async def get_by_id(self, investigation_id: UUID) -> Investigation | None: ...


class ThreadRepository(abc.ABC):
    """Port for persisting and retrieving Thread aggregates."""

    @abc.abstractmethod
    async def save(self, thread: Thread) -> None: ...

    @abc.abstractmethod
    async def get_by_id(self, thread_id: UUID) -> Thread | None: ...


class InvocationRepository(abc.ABC):
    """Port for persisting and retrieving Invocation entities.

    Supports the Orchestrate drain loop via get_pending_by_thread_id (D-30).
    """

    @abc.abstractmethod
    async def save(self, invocation: Invocation) -> None: ...

    @abc.abstractmethod
    async def save_many(self, invocations: list[Invocation]) -> None: ...

    @abc.abstractmethod
    async def get_by_id(self, invocation_id: UUID) -> Invocation | None: ...

    @abc.abstractmethod
    async def get_pending_by_thread_id(self, thread_id: UUID) -> list[Invocation]: ...
