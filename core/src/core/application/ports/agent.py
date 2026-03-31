from __future__ import annotations

import abc

from core.domain.entities.invocation import Invocation
from core.domain.entities.thread import Thread


class Agent(abc.ABC):
    """Port for the AI agent that processes conversation threads (D-68).

    Receives full thread history plus pending invocations, returns response text.
    """

    @abc.abstractmethod
    async def process(self, thread: Thread, invocations: list[Invocation]) -> str: ...
