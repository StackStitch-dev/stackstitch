from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from core.domain.enums import InsightType
from core.domain.events.domain_events import DomainEvent, InsightCreated


class Insight(BaseModel):
    """Semi-structured insight produced by an investigation."""

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    investigation_id: UUID
    thread_id: UUID | None = None
    title: str
    narrative: str
    insight_type: InsightType
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        self.collect_event(
            InsightCreated(
                insight_id=self.id,
                investigation_id=self.investigation_id,
                project_id=self.project_id,
                thread_id=self.thread_id,
            )
        )

    def collect_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def flush_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events
