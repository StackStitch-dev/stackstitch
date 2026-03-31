from __future__ import annotations

from typing import Any

from core.application.ports.investigator import Investigator
from core.domain.entities.investigation import Investigation, InvestigatorResult


class FakeInvestigator(Investigator):
    """Fake Investigator that returns a preset result and records calls."""

    def __init__(self, preset_result: InvestigatorResult) -> None:
        self.preset_result = preset_result
        self.calls: list[tuple[Investigation, dict[str, Any]]] = []

    async def investigate(
        self, investigation: Investigation, context: dict[str, Any]
    ) -> InvestigatorResult:
        self.calls.append((investigation, context))
        return self.preset_result
