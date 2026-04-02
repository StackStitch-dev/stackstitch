from __future__ import annotations

from uuid import uuid4

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from core.domain.entities.invocation import Invocation
from core.domain.enums import InvocationSource, InvocationStatus
from core.infrastructure.adapters.mongodb.invocation_repository import (
    MongoInvocationRepository,
)


@pytest.fixture
def repo(mongo_db: AsyncDatabase) -> MongoInvocationRepository:
    return MongoInvocationRepository(mongo_db)


def _make_invocation(**overrides) -> Invocation:
    defaults = {
        "thread_id": uuid4(),
        "project_id": uuid4(),
        "source": InvocationSource.USER_MESSAGE,
        "role": "user",
        "message": "Why is cycle time high?",
    }
    defaults.update(overrides)
    return Invocation(**defaults)


@pytest.mark.asyncio
async def test_save_and_get_by_id(repo: MongoInvocationRepository) -> None:
    inv = _make_invocation()
    await repo.save(inv)

    loaded = await repo.get_by_id(inv.id)
    assert loaded is not None
    assert loaded.id == inv.id
    assert loaded.thread_id == inv.thread_id
    assert loaded.project_id == inv.project_id
    assert loaded.source == InvocationSource.USER_MESSAGE
    assert loaded.role == "user"
    assert loaded.message == "Why is cycle time high?"
    assert loaded.status == InvocationStatus.PENDING
    assert loaded.created_at == inv.created_at


@pytest.mark.asyncio
async def test_get_by_id_not_found(repo: MongoInvocationRepository) -> None:
    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_save_many(repo: MongoInvocationRepository) -> None:
    inv1 = _make_invocation(message="q1")
    inv2 = _make_invocation(message="q2")
    inv3 = _make_invocation(message="q3")
    await repo.save_many([inv1, inv2, inv3])

    for inv in [inv1, inv2, inv3]:
        loaded = await repo.get_by_id(inv.id)
        assert loaded is not None
        assert loaded.message == inv.message


@pytest.mark.asyncio
async def test_get_pending_by_thread_id(repo: MongoInvocationRepository) -> None:
    thread_id = uuid4()
    inv1 = _make_invocation(thread_id=thread_id, message="pending1")
    inv2 = _make_invocation(thread_id=thread_id, message="pending2")
    inv3 = _make_invocation(thread_id=thread_id, message="processing")
    inv3.mark_processing()

    await repo.save(inv1)
    await repo.save(inv2)
    await repo.save(inv3)

    pending = await repo.get_pending_by_thread_id(thread_id)
    assert len(pending) == 2
    msgs = {p.message for p in pending}
    assert msgs == {"pending1", "pending2"}


@pytest.mark.asyncio
async def test_get_pending_by_thread_id_empty(repo: MongoInvocationRepository) -> None:
    result = await repo.get_pending_by_thread_id(uuid4())
    assert result == []


@pytest.mark.asyncio
async def test_save_overwrites_on_duplicate_id(repo: MongoInvocationRepository) -> None:
    inv = _make_invocation()
    await repo.save(inv)

    inv.mark_processing()
    await repo.save(inv)

    loaded = await repo.get_by_id(inv.id)
    assert loaded is not None
    assert loaded.status == InvocationStatus.PROCESSING
