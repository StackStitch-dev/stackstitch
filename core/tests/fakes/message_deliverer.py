from __future__ import annotations

from uuid import UUID

from core.application.ports.message_deliverer import MessageDeliverer


class FakeMessageDeliverer(MessageDeliverer):
    """Fake MessageDeliverer that records deliveries for assertions."""

    def __init__(self) -> None:
        self.deliveries: list[tuple[UUID, str]] = []

    async def deliver(self, thread_id: UUID, message: str) -> None:
        self.deliveries.append((thread_id, message))
