from __future__ import annotations

from core.application.ports.agent import Agent
from core.domain.entities.invocation import Invocation
from core.domain.entities.thread import Thread


class FakeAgent(Agent):
    """Fake Agent that returns a preset response and records calls."""

    def __init__(self, preset_response: str = "") -> None:
        self.preset_response = preset_response
        self.calls: list[tuple[Thread, list[Invocation]]] = []

    async def process(self, thread: Thread, invocations: list[Invocation]) -> str:
        self.calls.append((thread, invocations))
        return self.preset_response
