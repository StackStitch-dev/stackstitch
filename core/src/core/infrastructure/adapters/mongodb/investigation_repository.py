from __future__ import annotations

from uuid import UUID

from pymongo.asynchronous.database import AsyncDatabase

from core.application.ports.repositories import InvestigationRepository
from core.domain.entities.investigation import Investigation


class MongoInvestigationRepository(InvestigationRepository):
    """MongoDB adapter for Investigation persistence.

    Stores investigations as single documents with embedded InvestigationStep
    objects (D-10). Uses UUID string as _id (D-07).
    """

    def __init__(self, db: AsyncDatabase) -> None:
        self._collection = db["investigations"]

    async def ensure_indexes(self) -> None:
        """Create indexes for common query patterns."""
        await self._collection.create_index([("project_id", 1)])

    async def save(self, investigation: Investigation) -> None:
        doc = investigation.model_dump(mode="json")
        doc["_id"] = doc.pop("id")
        # Remove private attributes that Pydantic doesn't serialize but guard anyway
        doc.pop("_events", None)
        await self._collection.replace_one(
            {"_id": doc["_id"]}, doc, upsert=True
        )

    async def get_by_id(self, investigation_id: UUID) -> Investigation | None:
        doc = await self._collection.find_one({"_id": str(investigation_id)})
        if doc is None:
            return None
        doc["id"] = doc.pop("_id")
        return Investigation.model_validate(doc)
