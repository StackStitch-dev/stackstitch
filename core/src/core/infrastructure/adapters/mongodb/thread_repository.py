from __future__ import annotations

from collections import defaultdict
from uuid import UUID, NAMESPACE_URL, uuid5

from pymongo.asynchronous.database import AsyncDatabase

from core.application.ports.repositories import ThreadRepository
from core.domain.entities.thread import Message, Thread
from core.domain.enums import MessageRole


class MongoThreadRepository(ThreadRepository):
    """MongoDB adapter for Thread persistence.

    Uses decompose-on-write pattern (D-09): each Message is stored as an
    individual document in the 'threads' collection with a thread_id field.
    Thread is reassembled on read (D-12).
    """

    def __init__(self, db: AsyncDatabase) -> None:
        self._collection = db["threads"]

    async def ensure_indexes(self) -> None:
        """Create indexes for common query patterns."""
        await self._collection.create_index([("thread_id", 1)])
        await self._collection.create_index([("project_id", 1)])

    async def save(self, thread: Thread) -> None:
        for msg in thread.messages:
            # Deterministic _id prevents duplicates on re-save
            doc_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{thread.id}:{msg.role.value}:{msg.content}:{msg.timestamp.isoformat()}",
                )
            )
            doc = {
                "_id": doc_id,
                "thread_id": str(thread.id),
                "project_id": str(thread.project_id),
                "created_at": thread.created_at.isoformat(),
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            await self._collection.replace_one({"_id": doc_id}, doc, upsert=True)

    async def get_by_id(self, thread_id: UUID) -> Thread | None:
        docs = []
        async for doc in self._collection.find({"thread_id": str(thread_id)}):
            docs.append(doc)
        if not docs:
            return None
        return self._assemble_thread(thread_id, docs)

    async def get_by_project_id(self, project_id: UUID) -> list[Thread]:
        docs_by_thread: dict[str, list[dict]] = defaultdict(list)
        async for doc in self._collection.find({"project_id": str(project_id)}):
            docs_by_thread[doc["thread_id"]].append(doc)

        threads = []
        for tid, docs in docs_by_thread.items():
            threads.append(self._assemble_thread(UUID(tid), docs))
        return threads

    @staticmethod
    def _assemble_thread(thread_id: UUID, docs: list[dict]) -> Thread:
        """Reconstruct a Thread aggregate from its message documents."""
        # Sort by timestamp for consistent ordering
        docs.sort(key=lambda d: d["timestamp"])
        messages = [
            Message(
                role=MessageRole(doc["role"]),
                content=doc["content"],
                timestamp=doc["timestamp"],
            )
            for doc in docs
        ]
        first = docs[0]
        return Thread(
            id=thread_id,
            project_id=UUID(first["project_id"]),
            messages=messages,
            created_at=first["created_at"],
        )
