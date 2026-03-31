from __future__ import annotations

import abc

from core.domain.events.domain_events import DomainEvent


class EventPublisher(abc.ABC):
    """Port for publishing domain events (D-37).

    Only publishes -- subscription is a primary adapter concern.
    """

    @abc.abstractmethod
    async def publish(self, event: DomainEvent) -> None: ...

    @abc.abstractmethod
    async def publish_many(self, events: list[DomainEvent]) -> None: ...
