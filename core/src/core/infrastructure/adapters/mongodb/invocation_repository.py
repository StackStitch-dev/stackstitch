from __future__ import annotations

from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from core.application.ports.repositories import InvocationRepository
from core.domain.entities.invocation import Invocation


class MongoInvocationRepository(InvocationRepository):
    """MongoDB adapter for Invocation persistence.

    Simple UUID entity with _id mapping (D-07). Supports the Orchestrate
    drain loop via get_pending_by_thread_id (D-30).
    """

    def __init__(self, db: AsyncDatabase) -> None:
        self._collection = db["invocations"]

    async def ensure_indexes(self) -> None:
        """Create compound index for the pending-by-thread query."""
        await self._collection.create_index([("thread_id", 1), ("status", 1)])

    async def save(self, invocation: Invocation) -> None:
        doc = invocation.model_dump(mode="json")
        doc["_id"] = doc.pop("id")
        doc.pop("_events", None)
        await self._collection.replace_one(
            {"_id": doc["_id"]}, doc, upsert=True
        )

    async def save_many(self, invocations: list[Invocation]) -> None:
        for invocation in invocations:
            await self.save(invocation)

    async def get_by_id(self, invocation_id: UUID) -> Invocation | None:
        doc = await self._collection.find_one({"_id": str(invocation_id)})
        if doc is None:
            return None
        doc["id"] = doc.pop("_id")
        return Invocation.model_validate(doc)

    async def get_pending_by_thread_id(self, thread_id: UUID) -> list[Invocation]:
        results = []
        async for doc in self._collection.find(
            {"thread_id": str(thread_id), "status": "pending"}
        ):
            doc["id"] = doc.pop("_id")
            results.append(Invocation.model_validate(doc))
        return results
