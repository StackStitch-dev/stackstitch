from __future__ import annotations

import abc
from uuid import UUID


class MessageDeliverer(abc.ABC):
    """Port for delivering messages to the user's channel (D-32).

    Only the final response (after the Orchestrate drain loop completes)
    is delivered via this port.
    """

    @abc.abstractmethod
    async def deliver(self, thread_id: UUID, message: str) -> None: ...
