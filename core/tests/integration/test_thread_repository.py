from __future__ import annotations

from uuid import uuid4

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from core.domain.entities.thread import Message, Thread
from core.domain.enums import MessageRole
from core.infrastructure.adapters.mongodb.thread_repository import MongoThreadRepository


@pytest.fixture
def repo(mongo_db: AsyncDatabase) -> MongoThreadRepository:
    return MongoThreadRepository(mongo_db)


def _make_thread(**overrides) -> Thread:
    defaults = {"project_id": uuid4()}
    defaults.update(overrides)
    return Thread(**defaults)


@pytest.mark.asyncio
async def test_save_and_get_by_id(repo: MongoThreadRepository) -> None:
    thread = _make_thread()
    msg1 = Message(role=MessageRole.USER, content="Hello")
    msg2 = Message(role=MessageRole.ASSISTANT, content="Hi there")
    thread.messages = [msg1, msg2]

    await repo.save(thread)
    loaded = await repo.get_by_id(thread.id)

    assert loaded is not None
    assert loaded.id == thread.id
    assert loaded.project_id == thread.project_id
    assert loaded.created_at == thread.created_at
    assert len(loaded.messages) == 2
    assert loaded.messages[0].role == MessageRole.USER
    assert loaded.messages[0].content == "Hello"
    assert loaded.messages[0].timestamp == msg1.timestamp
    assert loaded.messages[1].role == MessageRole.ASSISTANT
    assert loaded.messages[1].content == "Hi there"
    assert loaded.messages[1].timestamp == msg2.timestamp


@pytest.mark.asyncio
async def test_get_by_id_not_found(repo: MongoThreadRepository) -> None:
    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_by_project_id(repo: MongoThreadRepository) -> None:
    project_a = uuid4()
    project_b = uuid4()
    t1 = _make_thread(project_id=project_a)
    t1.messages = [Message(role=MessageRole.USER, content="msg1")]
    t2 = _make_thread(project_id=project_a)
    t2.messages = [Message(role=MessageRole.USER, content="msg2")]
    t3 = _make_thread(project_id=project_b)
    t3.messages = [Message(role=MessageRole.USER, content="msg3")]

    await repo.save(t1)
    await repo.save(t2)
    await repo.save(t3)

    threads = await repo.get_by_project_id(project_a)
    assert len(threads) == 2
    ids = {t.id for t in threads}
    assert t1.id in ids
    assert t2.id in ids


@pytest.mark.asyncio
async def test_get_by_project_id_empty(repo: MongoThreadRepository) -> None:
    threads = await repo.get_by_project_id(uuid4())
    assert threads == []


@pytest.mark.asyncio
async def test_save_appends_new_messages(repo: MongoThreadRepository) -> None:
    thread = _make_thread()
    msg1 = Message(role=MessageRole.USER, content="first")
    thread.messages = [msg1]
    await repo.save(thread)

    msg2 = Message(role=MessageRole.ASSISTANT, content="second")
    thread.messages.append(msg2)
    await repo.save(thread)

    loaded = await repo.get_by_id(thread.id)
    assert loaded is not None
    assert len(loaded.messages) == 2
    assert loaded.messages[0].content == "first"
    assert loaded.messages[1].content == "second"
