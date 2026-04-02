"""MongoDB adapter for MetricRepository port."""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

import pymongo
from pymongo.asynchronous.database import AsyncDatabase

from core.application.ports.repositories import MetricRepository
from core.domain.entities.metric import Metric, MetricDataPoint
from core.domain.enums import MetricType


class MongoMetricRepository(MetricRepository):
    """Decompose-on-write / assemble-on-read adapter for Metric aggregates."""

    def __init__(self, db: AsyncDatabase) -> None:
        self._collection = db["metrics"]

    async def ensure_indexes(self) -> None:
        """Create compound index for composite key lookups."""
        await self._collection.create_index(
            [("metric_type", pymongo.ASCENDING), ("project_id", pymongo.ASCENDING)],
        )

    async def save(self, metric: Metric) -> None:
        """Persist each data point as an individual document with deterministic _id."""
        for dp in metric.data_points:
            doc_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{metric.metric_type.value}:{metric.project_id}:{dp.timestamp.isoformat()}",
                )
            )
            doc = {
                "_id": doc_id,
                "metric_type": metric.metric_type.value,
                "project_id": str(metric.project_id),
                "value": dp.value,
                "timestamp": dp.timestamp,
            }
            await self._collection.replace_one({"_id": doc_id}, doc, upsert=True)

    async def get_by_key(
        self, metric_type: MetricType, project_id: UUID
    ) -> Metric | None:
        """Reassemble Metric aggregate from child documents."""
        query = {
            "metric_type": metric_type.value,
            "project_id": str(project_id),
        }
        docs = await self._collection.find(query).to_list()
        if not docs:
            return None

        data_points = [
            MetricDataPoint(value=doc["value"], timestamp=doc["timestamp"])
            for doc in docs
        ]
        return Metric(
            metric_type=metric_type,
            project_id=project_id,
            data_points=data_points,
        )
