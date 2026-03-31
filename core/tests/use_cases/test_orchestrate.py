"""Tests for Orchestrate use case (drain loop pattern)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.application.use_cases.orchestrate import Orchestrate
from core.domain.entities.invocation import Invocation
from core.domain.entities.thread import Thread
from core.domain.enums import InvocationSource, InvocationStatus, MessageRole
from tests.fakes.agent import FakeAgent
from tests.fakes.message_deliverer import FakeMessageDeliverer
from tests.fakes.repositories import InMemoryInvocationRepository, InMemoryThreadRepository


@pytest.fixture
def use_case(
    thread_repo: InMemoryThreadRepository,
    invocation_repo: InMemoryInvocationRepository,
    agent: FakeAgent,
    message_deliverer: FakeMessageDeliverer,
) -> Orchestrate:
    return Orchestrate(
        thread_repo=thread_repo,
        invocation_repo=invocation_repo,
        agent=agent,
        message_deliverer=message_deliverer,
    )


@pytest.mark.asyncio
async def test_drain_loop_processes_pending_invocations(
    use_case: Orchestrate,
    thread_repo: InMemoryThreadRepository,
    invocation_repo: InMemoryInvocationRepository,
    agent: FakeAgent,
) -> None:
    thread_id = uuid4()
    project_id = uuid4()
    thread = Thread(id=thread_id, project_id=project_id)
    await thread_repo.save(thread)

    inv1 = Invocation(
        thread_id=thread_id, project_id=project_id,
        source=InvocationSource.USER_MESSAGE, role="user", message="msg1",
    )
    inv2 = Invocation(
        thread_id=thread_id, project_id=project_id,
        source=InvocationSource.INSIGHT, role="system", message="msg2",
    )
    await invocation_repo.save(inv1)
    await invocation_repo.save(inv2)

    await use_case.execute(thread_id=thread_id)

    assert len(agent.calls) == 1
    # Both invocations processed
    stored_inv1 = await invocation_repo.get_by_id(inv1.id)
    stored_inv2 = await invocation_repo.get_by_id(inv2.id)
    assert stored_inv1 is not None and stored_inv1.status == InvocationStatus.DONE
    assert stored_inv2 is not None and stored_inv2.status == InvocationStatus.DONE


@pytest.mark.asyncio
async def test_drain_loop_continues_if_new_invocations_arrive(
    thread_repo: InMemoryThreadRepository,
    invocation_repo: InMemoryInvocationRepository,
    message_deliverer: FakeMessageDeliverer,
) -> None:
    """First iteration processes 1, agent creates another pending, second iteration processes it."""
    thread_id = uuid4()
    project_id = uuid4()
    thread = Thread(id=thread_id, project_id=project_id)
    await thread_repo.save(thread)

    inv1 = Invocation(
        thread_id=thread_id, project_id=project_id,
        source=InvocationSource.USER_MESSAGE, role="user", message="first",
    )
    await invocation_repo.save(inv1)

    call_count = 0

    class SpawningAgent(FakeAgent):
        async def process(self, thread_arg, invocations):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Simulate a new invocation appearing after first processing
                new_inv = Invocation(
                    thread_id=thread_id, project_id=project_id,
                    source=InvocationSource.INSIGHT, role="system", message="spawned",
                )
                await invocation_repo.save(new_inv)
                return "intermediate"
            return "final"

    agent = SpawningAgent(preset_response="")
    use_case = Orchestrate(
        thread_repo=thread_repo,
        invocation_repo=invocation_repo,
        agent=agent,
        message_deliverer=message_deliverer,
    )

    await use_case.execute(thread_id=thread_id)

    assert call_count == 2
    # Final message delivered
    assert len(message_deliverer.deliveries) == 1
    assert message_deliverer.deliveries[0][1] == "final"


@pytest.mark.asyncio
async def test_delivers_only_final_response(
    use_case: Orchestrate,
    thread_repo: InMemoryThreadRepository,
    invocation_repo: InMemoryInvocationRepository,
    message_deliverer: FakeMessageDeliverer,
    agent: FakeAgent,
) -> None:
    thread_id = uuid4()
    project_id = uuid4()
    thread = Thread(id=thread_id, project_id=project_id)
    await thread_repo.save(thread)

    inv = Invocation(
        thread_id=thread_id, project_id=project_id,
        source=InvocationSource.USER_MESSAGE, role="user", message="q",
    )
    await invocation_repo.save(inv)
    agent.preset_response = "the final answer"

    await use_case.execute(thread_id=thread_id)

    assert len(message_deliverer.deliveries) == 1
    assert message_deliverer.deliveries[0] == (thread_id, "the final answer")


@pytest.mark.asyncio
async def test_stores_intermediate_responses_in_thread(
    use_case: Orchestrate,
    thread_repo: InMemoryThreadRepository,
    invocation_repo: InMemoryInvocationRepository,
    agent: FakeAgent,
) -> None:
    thread_id = uuid4()
    project_id = uuid4()
    thread = Thread(id=thread_id, project_id=project_id)
    await thread_repo.save(thread)

    inv = Invocation(
        thread_id=thread_id, project_id=project_id,
        source=InvocationSource.USER_MESSAGE, role="user", message="q",
    )
    await invocation_repo.save(inv)
    agent.preset_response = "response text"

    await use_case.execute(thread_id=thread_id)

    updated_thread = await thread_repo.get_by_id(thread_id)
    assert updated_thread is not None
    assert len(updated_thread.messages) == 1
    assert updated_thread.messages[0].role == MessageRole.ASSISTANT
    assert updated_thread.messages[0].content == "response text"


@pytest.mark.asyncio
async def test_noop_when_no_pending_invocations(
    use_case: Orchestrate,
    thread_repo: InMemoryThreadRepository,
    message_deliverer: FakeMessageDeliverer,
    agent: FakeAgent,
) -> None:
    thread_id = uuid4()
    project_id = uuid4()
    thread = Thread(id=thread_id, project_id=project_id)
    await thread_repo.save(thread)

    await use_case.execute(thread_id=thread_id)

    assert len(agent.calls) == 0
    assert len(message_deliverer.deliveries) == 0
