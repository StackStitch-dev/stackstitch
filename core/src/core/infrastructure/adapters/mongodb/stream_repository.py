"""MongoDB adapter for StreamRepository port."""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

import pymongo
from pymongo.asynchronous.database import AsyncDatabase

from core.application.ports.repositories import StreamRepository
from core.domain.entities.stream import Stream, StreamDataPoint
from core.domain.enums import StreamType


class MongoStreamRepository(StreamRepository):
    """Decompose-on-write / assemble-on-read adapter for Stream aggregates."""

    def __init__(self, db: AsyncDatabase) -> None:
        self._collection = db["streams"]

    async def ensure_indexes(self) -> None:
        """Create compound index for composite key lookups."""
        await self._collection.create_index(
            [("source", pymongo.ASCENDING), ("stream_type", pymongo.ASCENDING), ("project_id", pymongo.ASCENDING)],
        )

    async def save(self, stream: Stream) -> None:
        """Persist each data point as an individual document with deterministic _id."""
        for dp in stream.data_points:
            doc_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{stream.source}:{stream.stream_type.value}:{stream.project_id}:{dp.timestamp.isoformat()}",
                )
            )
            doc = {
                "_id": doc_id,
                "source": stream.source,
                "stream_type": stream.stream_type.value,
                "project_id": str(stream.project_id),
                "timestamp": dp.timestamp,
                "data": dp.data,
            }
            await self._collection.replace_one({"_id": doc_id}, doc, upsert=True)

    async def get_by_key(
        self, source: str, stream_type: StreamType, project_id: UUID
    ) -> Stream | None:
        """Reassemble Stream aggregate from child documents."""
        query = {
            "source": source,
            "stream_type": stream_type.value,
            "project_id": str(project_id),
        }
        docs = await self._collection.find(query).to_list()
        if not docs:
            return None

        data_points = [
            StreamDataPoint(timestamp=doc["timestamp"], data=doc["data"])
            for doc in docs
        ]
        return Stream(
            source=source,
            stream_type=stream_type,
            project_id=project_id,
            data_points=data_points,
        )
