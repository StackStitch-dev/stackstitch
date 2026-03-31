"""Tests for HandleMessage use case."""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.application.use_cases.handle_message import HandleMessage
from core.domain.entities.thread import Thread
from core.domain.enums import InvocationSource, MessageRole
from core.domain.events.domain_events import MessageCreated
from tests.fakes.event_publisher import InMemoryEventPublisher
from tests.fakes.repositories import InMemoryInvocationRepository, InMemoryThreadRepository


@pytest.fixture
def use_case(
    thread_repo: InMemoryThreadRepository,
    invocation_repo: InMemoryInvocationRepository,
    event_publisher: InMemoryEventPublisher,
) -> HandleMessage:
    return HandleMessage(
        thread_repo=thread_repo,
        invocation_repo=invocation_repo,
        event_publisher=event_publisher,
    )


@pytest.mark.asyncio
async def test_creates_thread_if_not_exists(
    use_case: HandleMessage,
    thread_repo: InMemoryThreadRepository,
) -> None:
    thread_id = uuid4()
    project_id = uuid4()

    await use_case.execute(thread_id=thread_id, project_id=project_id, content="Hello")

    thread = await thread_repo.get_by_id(thread_id)
    assert thread is not None
    assert thread.id == thread_id
    assert len(thread.messages) == 1
    assert thread.messages[0].content == "Hello"
    assert thread.messages[0].role == MessageRole.USER


@pytest.mark.asyncio
async def test_adds_message_to_existing_thread(
    use_case: HandleMessage,
    thread_repo: InMemoryThreadRepository,
) -> None:
    thread_id = uuid4()
    project_id = uuid4()
    existing = Thread(id=thread_id, project_id=project_id)
    await thread_repo.save(existing)

    await use_case.execute(thread_id=thread_id, project_id=project_id, content="Follow up")

    thread = await thread_repo.get_by_id(thread_id)
    assert thread is not None
    assert len(thread.messages) == 1
    assert thread.messages[0].content == "Follow up"


@pytest.mark.asyncio
async def test_emits_message_created(
    use_case: HandleMessage,
    event_publisher: InMemoryEventPublisher,
) -> None:
    thread_id = uuid4()

    await use_case.execute(thread_id=thread_id, project_id=uuid4(), content="Test msg")

    assert len(event_publisher.events) == 1
    event = event_publisher.events[0]
    assert isinstance(event, MessageCreated)
    assert event.thread_id == thread_id
    assert event.message_content == "Test msg"


@pytest.mark.asyncio
async def test_creates_invocation_for_user_message(
    use_case: HandleMessage,
    invocation_repo: InMemoryInvocationRepository,
) -> None:
    thread_id = uuid4()
    project_id = uuid4()

    await use_case.execute(thread_id=thread_id, project_id=project_id, content="Question")

    invocations = list(invocation_repo._store.values())
    assert len(invocations) == 1
    inv = invocations[0]
    assert inv.source == InvocationSource.USER_MESSAGE
    assert inv.thread_id == thread_id
    assert inv.project_id == project_id
    assert inv.role == "user"
    assert inv.message == "Question"
