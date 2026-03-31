"""Orchestrate use case -- drain loop pattern (D-30, D-31, D-32, D-66)."""

from __future__ import annotations

from uuid import UUID

from core.application.ports.agent import Agent
from core.application.ports.message_deliverer import MessageDeliverer
from core.application.ports.repositories import InvocationRepository, ThreadRepository
from core.domain.entities.thread import Message
from core.domain.enums import MessageRole


class Orchestrate:
    """Implements the drain loop: reads pending invocations, calls Agent, loops until empty.

    Only the final response is delivered to the user's channel (D-32).
    Intermediate responses are stored in the Thread (D-31).
    """

    def __init__(
        self,
        thread_repo: ThreadRepository,
        invocation_repo: InvocationRepository,
        agent: Agent,
        message_deliverer: MessageDeliverer,
    ) -> None:
        self._thread_repo = thread_repo
        self._invocation_repo = invocation_repo
        self._agent = agent
        self._message_deliverer = message_deliverer

    async def execute(self, thread_id: UUID) -> None:
        thread = await self._thread_repo.get_by_id(thread_id)
        if thread is None:
            return  # nothing to orchestrate

        last_response: str | None = None

        # Drain loop: keep processing until no pending invocations remain
        while True:
            pending = await self._invocation_repo.get_pending_by_thread_id(thread_id)
            if not pending:
                break

            for inv in pending:
                inv.mark_processing()
                await self._invocation_repo.save(inv)

            response = await self._agent.process(thread, pending)
            last_response = response

            # Store intermediate response in thread (D-31)
            assistant_msg = Message(role=MessageRole.ASSISTANT, content=response)
            thread.add_message(assistant_msg)
            await self._thread_repo.save(thread)

            for inv in pending:
                inv.mark_done()
                await self._invocation_repo.save(inv)

        # Deliver only final response (D-32)
        if last_response is not None:
            await self._message_deliverer.deliver(thread_id, last_response)
