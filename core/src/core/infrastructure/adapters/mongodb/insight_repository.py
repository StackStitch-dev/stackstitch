"""MongoDB adapter for InsightRepository port."""

from __future__ import annotations

from uuid import UUID

import pymongo
from pymongo.asynchronous.database import AsyncDatabase

from core.application.ports.repositories import InsightRepository
from core.domain.entities.insight import Insight


class MongoInsightRepository(InsightRepository):
    """UUID-as-string _id adapter for Insight entities."""

    def __init__(self, db: AsyncDatabase) -> None:
        self._collection = db["insights"]

    async def ensure_indexes(self) -> None:
        """Create index on project_id for future queries."""
        await self._collection.create_index(
            [("project_id", pymongo.ASCENDING)],
        )

    async def save(self, insight: Insight) -> None:
        """Persist Insight with UUID string as _id."""
        doc = insight.model_dump(mode="json")
        doc["_id"] = doc.pop("id")
        # Defensive: remove _events if present (PrivateAttr should not serialize)
        doc.pop("_events", None)
        await self._collection.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    async def get_by_id(self, insight_id: UUID) -> Insight | None:
        """Retrieve Insight by UUID, returning None if not found."""
        doc = await self._collection.find_one({"_id": str(insight_id)})
        if doc is None:
            return None
        doc["id"] = doc.pop("_id")
        return Insight.model_validate(doc)
