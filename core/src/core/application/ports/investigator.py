from __future__ import annotations

import abc
from typing import Any

from core.domain.entities.investigation import Investigation, InvestigatorResult


class Investigator(abc.ABC):
    """Port for running an investigation (D-67).

    The use case orchestrates; the Investigator just runs -- receives an
    Investigation entity plus context, returns an InvestigatorResult.
    """

    @abc.abstractmethod
    async def investigate(
        self, investigation: Investigation, context: dict[str, Any]
    ) -> InvestigatorResult: ...
