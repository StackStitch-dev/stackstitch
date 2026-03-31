"""HandleMessage use case -- adds message to thread, emits event, creates invocation (D-65)."""

from __future__ import annotations

from uuid import UUID

from core.application.ports.event_publisher import EventPublisher
from core.application.ports.repositories import InvocationRepository, ThreadRepository
from core.domain.entities.invocation import Invocation
from core.domain.entities.thread import Message, Thread
from core.domain.enums import InvocationSource, MessageRole
from core.domain.events.domain_events import MessageCreated


class HandleMessage:
    """Creates or appends to a Thread, emits MessageCreated, creates Invocation."""

    def __init__(
        self,
        thread_repo: ThreadRepository,
        invocation_repo: InvocationRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._thread_repo = thread_repo
        self._invocation_repo = invocation_repo
        self._event_publisher = event_publisher

    async def execute(
        self,
        thread_id: UUID,
        project_id: UUID,
        content: str,
    ) -> None:
        thread = await self._thread_repo.get_by_id(thread_id)
        if thread is None:
            thread = Thread(id=thread_id, project_id=project_id)

        message = Message(role=MessageRole.USER, content=content)
        thread.add_message(message)

        await self._thread_repo.save(thread)

        event = MessageCreated(
            thread_id=thread_id,
            message_content=content,
        )
        await self._event_publisher.publish(event)

        invocation = Invocation(
            thread_id=thread_id,
            project_id=project_id,
            source=InvocationSource.USER_MESSAGE,
            role="user",
            message=content,
        )
        await self._invocation_repo.save(invocation)
