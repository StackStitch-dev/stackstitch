# Architecture Patterns

**Domain:** Engineering Operational Intelligence Platform
**Researched:** 2026-03-27

## Recommended Architecture

Three services communicating via Kafka (async) and HTTP (sync). Each service is independently deployable but runs in a single Docker Compose for v1.

```
                    GitHub Webhooks
                         |
                  [Connector Service]
                    |            |
              (raw storage)  (Kafka: stream_updated)
                                |
                    [Core Service - DDD/Hexagonal]
                    |       |         |        |
              Calculators  Anomaly  Investigators  Insight Store
                    |       |         |
              (Kafka: metric_updated) |
                    |                 |
              (Kafka: anomaly_detected)
                    |
                    +-- (Kafka: insight_created)
                                |
                  [Channel Service]
                    |
              Slack (proactive alerts + ad-hoc queries)
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| Connector Service | Ingests external data, normalizes to streams, debounces, stores raw data | Core (via Kafka: stream_updated), MongoDB (raw storage) |
| Core Service | Computes metrics, detects anomalies, runs investigators, stores insights | Connector (consumes Kafka), Channel (via Kafka: insight_created), MongoDB (metrics, insights) |
| Channel Service | Delivers insights to users, handles ad-hoc queries via Slack | Core (consumes Kafka + HTTP for ad-hoc queries), Slack API |
| MongoDB | Persistent storage | All services (each service owns its own collections -- no cross-service DB reads) |
| Kafka | Async event bus | All services (produce and consume domain events) |

### Data Flow

1. **Ingestion:** GitHub webhook -> Connector Service -> raw storage + normalize -> publish `stream_updated` to Kafka
2. **Computation:** Core consumes `stream_updated` -> metric calculators compute/update -> publish `metric_updated`
3. **Detection:** Core consumes `metric_updated` -> anomaly detector evaluates statistical thresholds -> publish `anomaly_detected`
4. **Investigation:** Core consumes `anomaly_detected` -> investigator agent queries stores, reasons with LLM -> store insight -> publish `insight_created`
5. **Delivery:** Channel Service consumes `insight_created` -> format with Slack Block Kit -> send to Slack channel
6. **Ad-hoc:** User message in Slack -> Channel Service -> HTTP POST to Core -> agent investigates -> response -> Slack reply

### Kafka Topic Design

| Topic | Producer | Consumer | Partition Key | Purpose |
|-------|----------|----------|---------------|---------|
| `stream_updated` | Connector Service | Core Service | `project_id` | New/updated stream data available |
| `metric_updated` | Core Service | Core Service (anomaly detector) | `project_id` | Metric recalculated |
| `anomaly_detected` | Core Service | Core Service (investigators) | `project_id` | Statistical anomaly found |
| `insight_created` | Core Service | Channel Service | `project_id` | New insight ready for delivery |

Four topics total. Partition by `project_id` to guarantee ordering within a project.

## Patterns to Follow

### Pattern 1: Hexagonal Architecture (Core Service)

**What:** Separate domain logic from infrastructure via ports (interfaces) and adapters (implementations).

**When:** Always in the Core service. This is the heart of the system where DDD matters most.

**Structure:**
```
core/
  domain/
    entities/          # Metric, Insight, Investigation, Stream
    value_objects/     # MetricType, TimeWindow, AnomalyThreshold
    events/            # DomainEvent subclasses
    services/          # Domain services (pure logic)
  application/
    ports/             # Interfaces (MetricRepository, InsightRepository, EventPublisher)
    use_cases/         # Application services orchestrating domain logic
  infrastructure/
    adapters/
      persistence/     # MongoMetricRepository, MongoInsightRepository
      messaging/       # KafkaEventPublisher, KafkaEventConsumer
      ai/              # ADKInvestigatorAdapter
    api/               # FastAPI routes (driving adapter)
```

```python
# domain/ports/metric_repository.py (PORT - interface)
from abc import ABC, abstractmethod
from domain.entities import Metric, MetricDataPoint

class MetricRepository(ABC):
    @abstractmethod
    async def save_data_point(self, data_point: MetricDataPoint) -> None: ...

    @abstractmethod
    async def get_data_points(
        self, metric_id: str, start: datetime, end: datetime
    ) -> list[MetricDataPoint]: ...


# infrastructure/adapters/persistence/mongo_metric_repository.py (ADAPTER)
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.ports.metric_repository import MetricRepository

class MongoMetricRepository(MetricRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db.metric_data_points

    async def save_data_point(self, data_point: MetricDataPoint) -> None:
        await self._collection.insert_one(data_point.model_dump())
```

### Pattern 2: Domain Events via Kafka

**What:** Domain events published to Kafka topics with minimal payloads.

**When:** Whenever a service needs to notify others of state changes.

```python
# shared/events.py
from pydantic import BaseModel
from datetime import datetime

class StreamUpdated(BaseModel):
    event_type: str = "stream_updated"
    stream_id: str
    project_id: str
    source: str          # "github"
    data_type: str       # "pull_request", "commit", "review"
    timestamp: datetime
    correlation_id: str

class MetricUpdated(BaseModel):
    event_type: str = "metric_updated"
    metric_id: str
    metric_type: str     # "pr_cycle_time", "pr_throughput", "review_turnaround"
    project_id: str
    window_start: datetime
    window_end: datetime
    correlation_id: str
```

**Key rules:**
- Events carry IDs and minimal context, not full entity payloads
- Consumer fetches full data via its own store or HTTP if needed
- JSON serialization with Pydantic models (consider Avro for schema evolution in v2+)

### Pattern 3: Debouncing at Two Levels

**What:** Buffer high-frequency events before triggering downstream computation.

**When:** Connectors (before emitting stream_updated) and Calculators (before emitting metric_updated).

**Why:** A PR merge can trigger 5-10 GitHub webhooks in rapid succession (status checks, reviews, merge commit). Without debouncing, you recalculate metrics 10 times for one logical event.

```python
class Debouncer:
    def __init__(self, window_seconds: float = 5.0):
        self._window = window_seconds
        self._pending: dict[str, asyncio.Task] = {}

    async def debounce(self, key: str, callback):
        if key in self._pending:
            self._pending[key].cancel()
        self._pending[key] = asyncio.create_task(
            self._delayed_emit(key, callback)
        )

    async def _delayed_emit(self, key: str, callback):
        await asyncio.sleep(self._window)
        del self._pending[key]
        await callback()
```

### Pattern 4: Investigator as ADK Agent with Tools

**What:** Each investigator is a Google ADK agent configured with specific tools that query data stores.

**When:** Both deterministic (template-based) and AI (LLM-powered) investigators.

```python
# Conceptual structure -- verify against current ADK API
from google.adk import Agent, Tool

@Tool
async def query_metrics(metric_type: str, days: int = 7) -> dict:
    """Query metric data points for the specified type and time range."""
    # Calls MetricRepository port
    return results

@Tool
async def query_streams(source: str, data_type: str, days: int = 7) -> dict:
    """Query raw stream data for context."""
    return results

@Tool
async def query_past_insights(topic: str, days: int = 30) -> dict:
    """Read past insights for recurring pattern detection."""
    return results

investigator = Agent(
    model="gemini-2.0-flash",
    tools=[query_metrics, query_streams, query_past_insights],
    system_prompt="You are an engineering metrics investigator...",
    max_iterations=5,  # CRITICAL: prevent runaway tool loops
)
```

**Important:** ADK API shown here is conceptual. The actual API must be verified against current documentation before implementation.

### Pattern 5: Correlation IDs for Full Traceability

**What:** Every event carries a `correlation_id` that traces back to the original trigger.

**When:** Always. From webhook ingestion through to insight delivery.

```python
import uuid
import structlog

# Generate at ingestion point
correlation_id = request.headers.get("X-GitHub-Delivery", str(uuid.uuid4()))

# Bind to structlog context for automatic inclusion in all logs
structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

# Pass through Kafka message headers
producer.produce(
    topic="stream_updated",
    value=event.model_dump_json(),
    headers={"correlation_id": correlation_id},
)
```

### Pattern 6: MongoDB Collection Ownership

**What:** Each service owns and exclusively writes to its collections. No cross-service direct DB access.

| Service | Owns Collections | Reads From |
|---------|-----------------|------------|
| Connector | `raw_webhooks`, `streams`, `stream_data_points` | Own collections only |
| Core | `metrics`, `metric_data_points`, `anomalies`, `insights`, `investigations` | Own collections only |
| Channel | `messages`, `threads` | Own collections + Core via HTTP |

## Anti-Patterns to Avoid

### Anti-Pattern 1: Shared Database Reads Between Services
**What:** Channel Service reading Core's MongoDB collections directly.
**Why bad:** Tight coupling. Schema changes in Core break Channel. Cannot scale independently.
**Instead:** Channel queries Core via HTTP API for ad-hoc data. Kafka events carry enough context for proactive flows.

### Anti-Pattern 2: Synchronous Chains for Main Pipeline
**What:** Connector -> HTTP -> Core -> HTTP -> Channel for the data pipeline.
**Why bad:** Any service down breaks everything. No replay. No backpressure.
**Instead:** Kafka for all pipeline communication. HTTP only for request-response (ad-hoc queries, health checks).

### Anti-Pattern 3: Fat Domain Events
**What:** Putting entire entity payloads in Kafka messages.
**Why bad:** Huge messages, tight schema coupling, version conflicts.
**Instead:** Events carry IDs + minimal metadata. Consumer fetches full data if needed.

### Anti-Pattern 4: Anemic Domain Model
**What:** Entities are just data holders; all logic in services.
**Why bad:** Defeats DDD purpose. Business rules scattered. Hard to test.
**Instead:** Domain entities contain behavior. `Metric.add_data_point()` validates and computes. Use cases orchestrate entities.

### Anti-Pattern 5: One Giant Kafka Consumer
**What:** Single consumer handling all event types in one process.
**Why bad:** Slow handler blocks all others. No independent scaling.
**Instead:** Separate consumer groups per event type within Core.

### Anti-Pattern 6: Raw Dict Storage in MongoDB
**What:** Writing `dict` directly to MongoDB without Pydantic validation.
**Why bad:** Schema drift, silent data corruption, query failures on missing fields.
**Instead:** All MongoDB writes go through Pydantic model serialization.

## Scalability Considerations

| Concern | Single User (v1) | 10 Projects | 100 Projects |
|---------|-------------------|-------------|--------------|
| Kafka | Single broker, no replication | 3-broker cluster, replication | Managed Kafka (Confluent Cloud) |
| MongoDB | Single node | Replica set | Sharded cluster by project_id |
| Core Service | Single instance | Multiple instances per consumer group | Horizontal scaling with Kafka partitions |
| Investigators | Sequential per project | Parallel per project | Rate-limited pool with queue backpressure |
| Slack | Direct API calls | Rate-limited queue | Batching, message queue with throttling |

**v1 target:** Single user, single project. Docker Compose on one machine. Architecture supports scaling but does not require it.

## Sources

- Domain-Driven Design (Eric Evans), Implementing DDD (Vaughn Vernon)
- Hexagonal Architecture (Alistair Cockburn)
- Kafka patterns: Confluent documentation and best practices
- Project architecture decisions from `.planning/PROJECT.md`
