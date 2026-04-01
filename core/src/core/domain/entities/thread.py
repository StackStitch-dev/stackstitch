from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from core.domain.enums import MessageRole
from core.domain.events.domain_events import DomainEvent, MessageCreated


class Message(BaseModel):
    """Immutable value object representing a message in a thread."""

    model_config = ConfigDict(frozen=True)

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Thread(BaseModel):
    """Channel-agnostic conversation thread embedding messages."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.collect_event(
            MessageCreated(
                thread_id=self.id,
                message_content=message.content,
            )
        )

    def collect_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def flush_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events
