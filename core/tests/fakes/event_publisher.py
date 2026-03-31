from __future__ import annotations

from core.application.ports.event_publisher import EventPublisher
from core.domain.events.domain_events import DomainEvent


class InMemoryEventPublisher(EventPublisher):
    """In-memory fake for EventPublisher. Collects events for test assertions."""

    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)

    async def publish_many(self, events: list[DomainEvent]) -> None:
        self.events.extend(events)

    def clear(self) -> None:
        """Helper for test resets."""
        self.events.clear()
