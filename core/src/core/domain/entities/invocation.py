from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from core.domain.enums import InvocationSource, InvocationStatus
from core.domain.events.domain_events import DomainEvent
from core.domain.exceptions import InvalidEntityStateError


class Invocation(BaseModel):
    """Records a pending orchestration request (user message or insight trigger)."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    thread_id: UUID
    project_id: UUID
    source: InvocationSource
    role: str
    message: str
    status: InvocationStatus = InvocationStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def collect_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def flush_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events

    def mark_processing(self) -> None:
        """Transition PENDING -> PROCESSING."""
        if self.status != InvocationStatus.PENDING:
            raise InvalidEntityStateError(
                "Invocation",
                self.id,
                f"must be PENDING to process, currently {self.status.value}",
            )
        self.status = InvocationStatus.PROCESSING

    def mark_done(self) -> None:
        """Transition PROCESSING -> DONE."""
        if self.status != InvocationStatus.PROCESSING:
            raise InvalidEntityStateError(
                "Invocation",
                self.id,
                f"must be PROCESSING to mark done, currently {self.status.value}",
            )
        self.status = InvocationStatus.DONE
