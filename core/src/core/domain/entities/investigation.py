from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from core.domain.enums import InvestigationStatus, InvestigationStepType, InvestigationTrigger
from core.domain.events.domain_events import DomainEvent
from core.domain.exceptions import InvalidEntityStateError


class InvestigationStep(BaseModel):
    """Immutable value object recording a single step in an investigation."""

    model_config = ConfigDict(frozen=True)

    step_type: InvestigationStepType
    tool_name: str | None = None
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""
    tokens_used: int = 0


class InvestigatorResult(BaseModel):
    """Immutable value object returned by the Investigator port."""

    model_config = ConfigDict(frozen=True)

    steps: list[InvestigationStep]
    findings: str
    tokens_used: int


class Investigation(BaseModel):
    """Full entity with lifecycle: PENDING -> RUNNING -> COMPLETED | FAILED."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    trigger: InvestigationTrigger
    trigger_ref: UUID
    query: str | None = None
    status: InvestigationStatus = InvestigationStatus.PENDING
    steps: list[InvestigationStep] = Field(default_factory=list)
    findings: str | None = None
    tokens_used: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def collect_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def flush_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events

    def start(self) -> None:
        """Transition PENDING -> RUNNING."""
        if self.status != InvestigationStatus.PENDING:
            raise InvalidEntityStateError(
                "Investigation", self.id, f"must be PENDING to start, currently {self.status.value}"
            )
        self.status = InvestigationStatus.RUNNING

    def complete(self, result: InvestigatorResult) -> None:
        """Transition RUNNING -> COMPLETED with investigation result."""
        if self.status != InvestigationStatus.RUNNING:
            raise InvalidEntityStateError(
                "Investigation",
                self.id,
                f"must be RUNNING to complete, currently {self.status.value}",
            )
        self.status = InvestigationStatus.COMPLETED
        self.steps = list(result.steps)
        self.findings = result.findings
        self.tokens_used = result.tokens_used

    def fail(self, reason: str) -> None:
        """Transition RUNNING -> FAILED with failure reason."""
        if self.status != InvestigationStatus.RUNNING:
            raise InvalidEntityStateError(
                "Investigation",
                self.id,
                f"must be RUNNING to fail, currently {self.status.value}",
            )
        self.status = InvestigationStatus.FAILED
        self.findings = reason
