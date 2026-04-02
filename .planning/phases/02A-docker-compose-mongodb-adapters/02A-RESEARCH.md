# Phase 2A: Docker Compose & MongoDB Adapters - Research

**Researched:** 2026-04-02
**Domain:** Docker Compose orchestration, MongoDB async persistence, integration testing
**Confidence:** HIGH

## Summary

This phase bridges the pure domain layer from Phase 1 to real infrastructure. Two parallel workstreams: (1) a Docker Compose file that starts MongoDB, Kafka (KRaft mode), the Core service stub, and dev tools with one command, and (2) MongoDB repository adapters implementing all 6 port interfaces using async PyMongo (not Motor, which is deprecated).

The most significant research finding is that **Motor is deprecated as of May 2025** in favor of PyMongo's native async API (`AsyncMongoClient`), which reached GA in PyMongo 4.13. Since this is a greenfield project, the adapters should use PyMongo async directly — it provides better latency and throughput by using asyncio natively rather than delegating to a thread pool. The CLAUDE.md recommendation of Motor should be overridden with PyMongo async.

The adapter layer is the translation boundary between rich domain aggregates (Stream with embedded DataPoints) and flat MongoDB documents (individual StreamDataPoint documents with denormalized parent keys). This decompose-on-write / assemble-on-read pattern is well-established and avoids MongoDB's 16MB document limit.

**Primary recommendation:** Use PyMongo 4.16+ with `AsyncMongoClient` for all async MongoDB operations. Use `apache/kafka` official image in KRaft mode. Use testcontainers 4.14+ with `MongoDbContainer` for integration tests.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Kafka runs in KRaft mode (no ZooKeeper container). Single Kafka container with built-in metadata management.
- **D-02:** Dev observability tools included: Mongo Express (MongoDB web UI) and Kafka UI (Redpanda Console or similar) for debugging.
- **D-03:** Core service runs as a Docker container with a minimal FastAPI stub -- only a `/health` endpoint. Proves the service boots and connects to MongoDB. No Kafka consumers in this phase.
- **D-04:** Domain model does NOT map 1:1 to DB model. Parent entities (Stream, Metric, Thread) are virtual -- they have no documents. Only child/leaf entities are persisted as individual documents.
- **D-05:** Collection naming follows the aggregate name, containing child documents: `streams`, `metrics`, `threads`, `insights`, `investigations`, `invocations`.
- **D-06:** Composite-key entities (StreamDataPoint, MetricDataPoint) reference their logical parent via denormalized key fields. No parent_id reference object.
- **D-07:** UUID-identified entities (Insight, Investigation, Invocation) use UUID string as MongoDB `_id`. No ObjectId, no Binary UUID.
- **D-08:** StreamDataPoint and MetricDataPoint documents use their domain UUID as `_id` (string).
- **D-09:** Message documents in the `threads` collection reference their parent thread via `thread_id` field.
- **D-10:** InvestigationStep objects are embedded within the Investigation document (not a separate collection).
- **D-11:** Adapters ensure indexes on startup (ensure_index/create_index). No separate migration scripts.
- **D-12:** Repository `get_by_key()` (for Stream, Metric) and `get_by_id()` (for Thread) assembles the virtual parent entity by querying the child collection and constructing the domain object with the adapter.
- **D-13:** Raw async driver. No Beanie ODM. The adapter IS the mapping layer.
- **D-14:** MongoDB adapters live inside the core package: `core/src/core/infrastructure/adapters/mongodb/`
- **D-15:** Shared MongoDB connection module at `core/src/core/infrastructure/adapters/mongodb/connection.py`. Adapters receive `AsyncIOMotorDatabase` via constructor injection.
- **D-16:** One adapter file per repository port.
- **D-17:** Integration tests use testcontainers to spin up real MongoDB in Docker.
- **D-18:** Shared container per test session, clean database per test function.
- **D-19:** Full round-trip coverage for every repository port method.

### Claude's Discretion
- Specific index definitions per collection (compound indexes on key fields, etc.)
- Docker Compose port mappings and volume configuration
- Health endpoint implementation details
- Test fixture design and helper utilities
- Dockerfile multi-stage build structure for Core service

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFR-01 | All services run via a single Docker Compose command for local deployment | Docker Compose config with MongoDB 7, Kafka KRaft, Core stub, Mongo Express, Kafka UI |
| INFR-02 | MongoDB is used as the primary data store for streams, metrics, and insights | PyMongo async adapters implementing all 6 repository ports with round-trip integration tests |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Language:** Python 3.12+
- **Architecture:** DDD + Hexagonal Architecture for the Core
- **Database:** MongoDB with variable schema handling
- **Message Broker:** Kafka with ordered message processing
- **Package Manager:** uv
- **Build backend:** hatchling (established in Phase 1)
- **Linter/Formatter:** Ruff
- **Type checker:** mypy (strict mode)
- **Test framework:** pytest with pytest-asyncio (asyncio_mode = "auto")
- **HTTP framework:** FastAPI with Uvicorn
- **GSD Workflow:** All changes through GSD commands

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pymongo | 4.16.0 | Async MongoDB driver (AsyncMongoClient) | Motor is deprecated (May 2025). PyMongo 4.13+ has GA async API. Native asyncio, better latency than Motor's thread pool delegation. Drop-in replacement with same query patterns. |
| FastAPI | 0.115+ | HTTP framework for /health stub | Already in stack. Only used for health endpoint in this phase. |
| uvicorn | 0.32+ | ASGI server | Standard production server for FastAPI. |
| pydantic-settings | 2.7+ | Configuration management | Loads MongoDB URI, service config from env vars. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| testcontainers[mongodb] | 4.14+ | Integration test MongoDB container | Spins up real MongoDB for adapter integration tests |
| httpx | 0.28+ | HTTP test client | Testing /health endpoint via FastAPI TestClient |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyMongo async | Motor 3.7.1 | Motor is deprecated (EOL May 2026, critical-only after May 2027). PyMongo async is the official replacement with better performance. |
| PyMongo async | Beanie ODM | Adds abstraction layer. D-13 explicitly chose raw driver -- adapter IS the mapping layer. |
| apache/kafka image | confluentinc/cp-kafka | Confluent image is larger, more enterprise-focused. apache/kafka is the official Apache image, lighter, supports KRaft natively. |

**Installation (add to core/pyproject.toml):**
```bash
# Production dependencies
uv add "pymongo>=4.16,<5" "fastapi>=0.115,<1" "uvicorn>=0.32,<1" "pydantic-settings>=2.7,<3"

# Dev dependencies
uv add --dev "testcontainers[mongodb]>=4.14,<5" "httpx>=0.28,<1"
```

**IMPORTANT -- Motor vs PyMongo async:** D-13 says "Raw Motor (async) driver" and D-15 says adapters receive `AsyncIOMotorDatabase`. Since Motor is now deprecated, the equivalent in PyMongo async is `AsyncDatabase` from `pymongo.asynchronous.database`. The constructor injection type should be `pymongo.asynchronous.database.AsyncDatabase` instead of `motor.motor_asyncio.AsyncIOMotorDatabase`. The API is nearly identical -- same `insert_one`, `find_one`, `find`, `replace_one`, `create_index` methods.

## Architecture Patterns

### Recommended Project Structure
```
core/
├── src/core/
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   └── mongodb/
│   │   │       ├── __init__.py
│   │   │       ├── connection.py          # AsyncMongoClient factory, db accessor
│   │   │       ├── stream_repository.py   # StreamRepository adapter
│   │   │       ├── metric_repository.py   # MetricRepository adapter
│   │   │       ├── insight_repository.py  # InsightRepository adapter
│   │   │       ├── investigation_repository.py
│   │   │       ├── thread_repository.py   # ThreadRepository adapter
│   │   │       └── invocation_repository.py
│   │   └── web/
│   │       ├── __init__.py
│   │       └── app.py                     # FastAPI app with /health endpoint
│   └── ...existing domain/application...
├── tests/
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── conftest.py                    # Session-scoped MongoDB container fixture
│   │   ├── test_stream_repository.py
│   │   ├── test_metric_repository.py
│   │   ├── test_insight_repository.py
│   │   ├── test_investigation_repository.py
│   │   ├── test_thread_repository.py
│   │   └── test_invocation_repository.py
│   └── ...existing unit tests...
├── Dockerfile
└── pyproject.toml
docker-compose.yml                         # Root-level compose file
```

### Pattern 1: Decompose-on-Write / Assemble-on-Read Adapter

**What:** Domain entities like Stream contain embedded data_points lists. The adapter decomposes these into individual MongoDB documents on save, and queries + assembles them back into domain entities on read.

**When to use:** When domain aggregates have unbounded child collections (D-04).

**Example:**
```python
# Source: Project CONTEXT.md D-04, D-06, D-12
from uuid import UUID, uuid4
from pymongo.asynchronous.database import AsyncDatabase
from core.application.ports.repositories import StreamRepository
from core.domain.entities.stream import Stream, StreamDataPoint
from core.domain.enums import StreamType


class MongoStreamRepository(StreamRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        self._collection = db["streams"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index(
            [("source", 1), ("stream_type", 1), ("project_id", 1)]
        )

    async def save(self, stream: Stream) -> None:
        # Decompose: each data_point becomes a document
        for dp in stream.data_points:
            doc = {
                "_id": str(uuid4()),  # D-08: UUID string as _id
                "source": stream.source,
                "stream_type": stream.stream_type.value,
                "project_id": str(stream.project_id),
                "timestamp": dp.timestamp,
                "data": dp.data,
            }
            await self._collection.replace_one(
                {"_id": doc["_id"]}, doc, upsert=True
            )

    async def get_by_key(
        self, source: str, stream_type: StreamType, project_id: UUID
    ) -> Stream | None:
        # Assemble: query children, construct parent
        cursor = self._collection.find({
            "source": source,
            "stream_type": stream_type.value,
            "project_id": str(project_id),
        })
        docs = await cursor.to_list()
        if not docs:
            return None
        data_points = [
            StreamDataPoint(timestamp=d["timestamp"], data=d["data"])
            for d in docs
        ]
        return Stream(
            source=source,
            stream_type=stream_type,
            project_id=project_id,
            data_points=data_points,
        )
```

### Pattern 2: UUID-as-String _id for Simple Entities

**What:** Entities with UUID identity use `str(entity.id)` as MongoDB `_id`. No ObjectId, no Binary UUID (D-07).

**When to use:** Insight, Investigation, Invocation, and child documents of Stream/Metric.

**Example:**
```python
# Source: Project CONTEXT.md D-07
async def save(self, insight: Insight) -> None:
    doc = insight.model_dump()
    doc["_id"] = str(doc.pop("id"))
    # Convert UUIDs to strings for MongoDB
    doc["project_id"] = str(doc["project_id"])
    doc["investigation_id"] = str(doc["investigation_id"])
    if doc.get("thread_id"):
        doc["thread_id"] = str(doc["thread_id"])
    doc["insight_type"] = doc["insight_type"]  # str enum already serializes
    await self._collection.replace_one(
        {"_id": doc["_id"]}, doc, upsert=True
    )

async def get_by_id(self, insight_id: UUID) -> Insight | None:
    doc = await self._collection.find_one({"_id": str(insight_id)})
    if doc is None:
        return None
    doc["id"] = UUID(doc.pop("_id"))
    doc["project_id"] = UUID(doc["project_id"])
    doc["investigation_id"] = UUID(doc["investigation_id"])
    if doc.get("thread_id"):
        doc["thread_id"] = UUID(doc["thread_id"])
    return Insight.model_validate(doc)
```

### Pattern 3: Connection Module with Async Client

**What:** Centralized connection module providing AsyncMongoClient and database object.

**Example:**
```python
# core/src/core/infrastructure/adapters/mongodb/connection.py
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase


async def create_mongo_client(uri: str) -> AsyncMongoClient:
    """Create and return an AsyncMongoClient."""
    client: AsyncMongoClient = AsyncMongoClient(uri)
    return client


def get_database(client: AsyncMongoClient, db_name: str) -> AsyncDatabase:
    """Get a database reference from the client."""
    return client[db_name]
```

### Pattern 4: Save Semantics -- Append vs Replace

**What:** Stream.save() and Metric.save() must handle the fact that data_points grow over time. The adapter needs to decide whether to replace all child documents or only insert new ones.

**Key consideration for Stream/Metric save:**
- The domain `save(stream)` is called with the full aggregate including all data_points
- The simplest correct approach: use `insert_many` for new data_points only, or `replace_one` with upsert per data_point
- Since StreamDataPoint has no UUID in the domain model (it's a value object with timestamp + data), the adapter must generate a `_id` per document
- **Important:** On repeated saves, avoid duplicating existing data_points. Consider tracking which data_points are already persisted, or use a deterministic _id based on (source, stream_type, project_id, timestamp) to enable idempotent upserts

**Recommendation:** Generate a deterministic `_id` for StreamDataPoint by hashing `(source, stream_type, project_id, timestamp)` to make saves idempotent. Alternatively, track a "last saved index" -- but the hash approach is simpler and aligns with upsert patterns.

### Anti-Patterns to Avoid
- **Storing aggregates as single documents:** Violates D-04. Stream with thousands of data_points would hit 16MB limit. Child documents must be individual records.
- **Using ObjectId for _id:** Violates D-07/D-08. Always use UUID string.
- **Leaking MongoDB types into domain:** The adapter must convert all BSON types (especially datetime, ObjectId) to Python types before constructing domain entities.
- **Blocking MongoDB calls in async context:** Use `AsyncMongoClient` consistently. Never use synchronous `MongoClient` in the FastAPI async path.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MongoDB container for tests | Custom Docker scripts | `testcontainers[mongodb]` MongoDbContainer | Handles container lifecycle, port allocation, cleanup automatically |
| Docker Compose health checks | Manual sleep/retry | Docker Compose `healthcheck` + `depends_on.condition: service_healthy` | Reliable startup ordering without race conditions |
| UUID serialization for MongoDB | Custom encoder/decoder | `str(uuid)` / `UUID(string)` with Pydantic model_dump/model_validate | Simple string round-trip, no BSON Binary UUID complexity |
| Configuration management | Manual env parsing | pydantic-settings BaseSettings | Typed validation, .env file support, nested config |

**Key insight:** The adapter layer IS the hand-rolled mapping -- and that's intentional (D-13). But the mapping should be thin: `model_dump()` for serialization, `model_validate()` for deserialization, with UUID/enum string conversions in between.

## Common Pitfalls

### Pitfall 1: Motor Import Instead of PyMongo Async
**What goes wrong:** Using `from motor.motor_asyncio import AsyncIOMotorClient` when Motor is deprecated.
**Why it happens:** CLAUDE.md and CONTEXT.md reference Motor (decided before deprecation).
**How to avoid:** Use `from pymongo import AsyncMongoClient` and `from pymongo.asynchronous.database import AsyncDatabase`. The API is nearly identical.
**Warning signs:** Import errors if Motor is not installed, or deprecation warnings if it is.

### Pitfall 2: Duplicate Data Points on Re-Save
**What goes wrong:** Calling `save(stream)` twice persists data_points twice because each call generates new UUIDs for _id.
**Why it happens:** StreamDataPoint is a value object with no identity. Naive save assigns random UUID each time.
**How to avoid:** Use deterministic _id generation (hash of composite key + timestamp) or use `update_one` with `$addToSet` / `$push` combined with existence checks.
**Warning signs:** Data point count in DB exceeds expected count after multiple saves.

### Pitfall 3: Datetime Timezone Loss in MongoDB
**What goes wrong:** MongoDB stores datetimes as UTC but strips timezone info. Reading back gives naive datetimes.
**Why it happens:** BSON datetime type doesn't store timezone offset.
**How to avoid:** Use `CodecOptions(tz_aware=True, tzinfo=datetime.timezone.utc)` on the database or collection. Or explicitly attach timezone on read.
**Warning signs:** `datetime.now(timezone.utc)` comparisons fail because retrieved datetimes are naive.

### Pitfall 4: Enum Serialization Mismatch
**What goes wrong:** Pydantic `model_dump()` may serialize enums differently than expected for MongoDB queries.
**Why it happens:** `model_dump(mode="python")` keeps enum objects; `model_dump(mode="json")` gives strings. MongoDB queries need string values.
**How to avoid:** Use `model_dump(mode="json")` or explicitly call `.value` on enums when building query filters and documents.
**Warning signs:** Queries return no results despite data existing.

### Pitfall 5: Docker Compose Startup Race Conditions
**What goes wrong:** Core service starts before MongoDB is ready, connection fails.
**Why it happens:** `depends_on` only waits for container start, not service readiness.
**How to avoid:** Use `depends_on` with `condition: service_healthy` and add `healthcheck` to MongoDB and Kafka services.
**Warning signs:** Intermittent connection errors on first `docker compose up`.

### Pitfall 6: Kafka Not Used But Must Be Healthy
**What goes wrong:** Kafka container in compose fails silently, not caught until Phase 2b.
**Why it happens:** No consumers/producers in Phase 2a, so Kafka failures are invisible.
**How to avoid:** Include Kafka health check in compose. Kafka UI (Redpanda Console) provides visual confirmation. Success criteria requires Kafka starts without errors.
**Warning signs:** Kafka UI shows no brokers, or Kafka container restarts repeatedly.

## Code Examples

### Docker Compose (Complete)
```yaml
# docker-compose.yml (project root)
services:
  mongodb:
    image: mongo:7
    container_name: stackstitch-mongodb
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  kafka:
    image: apache/kafka:latest
    container_name: stackstitch-kafka
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://kafka:29092,CONTROLLER://kafka:29093,PLAINTEXT_HOST://0.0.0.0:9092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT,CONTROLLER:PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:29093
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_LOG_DIRS: /tmp/kraft-combined-logs
      CLUSTER_ID: MkU3OEVBNTcwNTJENDM2Qk
    healthcheck:
      test: ["CMD-SHELL", "/opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092 > /dev/null 2>&1"]
      interval: 15s
      timeout: 10s
      retries: 5

  mongo-express:
    image: mongo-express:latest
    container_name: stackstitch-mongo-express
    ports:
      - "8081:8081"
    environment:
      ME_CONFIG_MONGODB_URL: mongodb://mongodb:27017/
      ME_CONFIG_BASICAUTH: "false"
    depends_on:
      mongodb:
        condition: service_healthy

  kafka-ui:
    image: docker.redpanda.com/redpandadata/console:latest
    container_name: stackstitch-kafka-ui
    ports:
      - "8080:8080"
    environment:
      KAFKA_BROKERS: kafka:29092
    depends_on:
      kafka:
        condition: service_healthy

  core:
    build:
      context: ./core
      dockerfile: Dockerfile
    container_name: stackstitch-core
    ports:
      - "8000:8000"
    environment:
      MONGODB_URI: mongodb://mongodb:27017/
      MONGODB_DATABASE: stackstitch
    depends_on:
      mongodb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  mongodb_data:
```

### Dockerfile (Multi-Stage with uv)
```dockerfile
# core/Dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first (cache layer)
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install project
COPY src/ src/
RUN uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "core.infrastructure.web.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

### FastAPI Health Endpoint
```python
# core/src/core/infrastructure/web/app.py
from fastapi import FastAPI
from pymongo import AsyncMongoClient
from pydantic_settings import BaseSettings


class CoreSettings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017/"
    mongodb_database: str = "stackstitch"

    model_config = {"env_prefix": ""}


def create_app() -> FastAPI:
    settings = CoreSettings()
    app = FastAPI(title="StackStitch Core", version="0.1.0")
    client: AsyncMongoClient | None = None

    @app.on_event("startup")
    async def startup() -> None:
        nonlocal client
        client = AsyncMongoClient(settings.mongodb_uri)

    @app.on_event("shutdown")
    async def shutdown() -> None:
        if client:
            client.close()

    @app.get("/health")
    async def health() -> dict[str, str]:
        if client is None:
            return {"status": "error", "detail": "no client"}
        try:
            await client.admin.command("ping")
            return {"status": "ok", "mongodb": "connected"}
        except Exception:
            return {"status": "degraded", "mongodb": "disconnected"}

    return app
```

### Integration Test Fixture (testcontainers)
```python
# core/tests/integration/conftest.py
from collections.abc import AsyncGenerator

import pytest
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from testcontainers.mongodb import MongoDbContainer


@pytest.fixture(scope="session")
def mongo_container() -> MongoDbContainer:
    """Session-scoped: one MongoDB container for all integration tests."""
    container = MongoDbContainer("mongo:7")
    container.start()
    yield container
    container.stop()


@pytest.fixture
async def mongo_db(mongo_container: MongoDbContainer) -> AsyncGenerator[AsyncDatabase]:
    """Function-scoped: clean database per test."""
    url = mongo_container.get_connection_url()
    client: AsyncMongoClient = AsyncMongoClient(url)
    db = client["test_stackstitch"]
    yield db
    # Clean up: drop all collections after each test
    for name in await db.list_collection_names():
        await db.drop_collection(name)
    client.close()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Motor (AsyncIOMotorClient) | PyMongo AsyncMongoClient | May 2025 (Motor deprecated, PyMongo 4.13 GA async) | Direct asyncio instead of thread pool. Same API surface. Motor EOL May 2026. |
| Kafka + ZooKeeper | Kafka KRaft mode | Kafka 3.3+ (KRaft GA), Confluent 8.0 (ZK removed) | One fewer container. Simpler config. Required for Kafka 4.x+. |
| confluentinc/cp-kafka | apache/kafka | Kafka 3.7+ (official Docker images) | Official Apache Foundation image. Lighter weight for dev. |
| pip/Poetry | uv | 2024-2025 | 10-100x faster. Already decided in Phase 1. |

**Deprecated/outdated:**
- **Motor 3.7.x:** Deprecated May 2025. Bug fixes only until May 2026. Critical-only until May 2027. Use PyMongo async instead.
- **Kafka with ZooKeeper:** ZooKeeper removed from Confluent Platform 8.0. KRaft is the only path forward for Kafka 4.x+.

## Open Questions

1. **StreamDataPoint _id generation strategy**
   - What we know: StreamDataPoint is a value object (no UUID in domain). D-08 says "use their domain UUID as _id" but StreamDataPoint has no domain UUID -- it has `timestamp` + `data`.
   - What's unclear: Should _id be a random UUID generated by the adapter, or a deterministic hash of (source, stream_type, project_id, timestamp)?
   - Recommendation: Use random UUID per data point. Saves are idempotent if the adapter only inserts NEW data points (not the entire list each time). The save method should compare what's already in the DB and only insert missing ones, or the adapter should track the "high water mark" (count of persisted data points).

2. **PyMongo async vs Motor in D-13/D-15**
   - What we know: CONTEXT.md says "Raw Motor (async) driver" and "AsyncIOMotorDatabase." Motor is now deprecated.
   - What's unclear: Whether the user wants to stick with Motor anyway.
   - Recommendation: Use PyMongo async. The API is a near-identical drop-in. The user's intent (raw async driver, no ODM) is fully satisfied by PyMongo async. The type changes from `AsyncIOMotorDatabase` to `AsyncDatabase`.

3. **MetricDataPoint _id generation**
   - Same question as StreamDataPoint. MetricDataPoint has `value` + `timestamp` but no UUID.
   - Recommendation: Same approach -- adapter-generated UUID string per data point document.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Docker Compose, testcontainers | NOT FOUND | -- | Must install Docker Desktop. Blocks all infrastructure work. |
| Python | Core service, tests | Yes | 3.13.3 | Compatible (>=3.12 required) |
| uv | Package management | Yes | 0.10.3 | -- |

**Missing dependencies with no fallback:**
- **Docker:** Required for Docker Compose (INFR-01), testcontainers integration tests (D-17), and building Core service image (D-03). Must be installed before execution begins. Install Docker Desktop for macOS.

**Missing dependencies with fallback:**
- None. Docker is a hard requirement for this phase.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 0.24+ |
| Config file | `core/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd core && uv run pytest tests/integration/ -x -q` |
| Full suite command | `cd core && uv run pytest tests/ --cov=core --cov-report=term-missing` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFR-01 | Docker Compose starts all services | smoke (manual) | `docker compose up -d && docker compose ps` | N/A -- compose file, not code test |
| INFR-02-a | StreamRepository round-trip | integration | `cd core && uv run pytest tests/integration/test_stream_repository.py -x` | Wave 0 |
| INFR-02-b | MetricRepository round-trip | integration | `cd core && uv run pytest tests/integration/test_metric_repository.py -x` | Wave 0 |
| INFR-02-c | InsightRepository round-trip | integration | `cd core && uv run pytest tests/integration/test_insight_repository.py -x` | Wave 0 |
| INFR-02-d | InvestigationRepository round-trip | integration | `cd core && uv run pytest tests/integration/test_investigation_repository.py -x` | Wave 0 |
| INFR-02-e | ThreadRepository round-trip | integration | `cd core && uv run pytest tests/integration/test_thread_repository.py -x` | Wave 0 |
| INFR-02-f | InvocationRepository round-trip | integration | `cd core && uv run pytest tests/integration/test_invocation_repository.py -x` | Wave 0 |
| INFR-02-g | Health endpoint connects to MongoDB | integration | `cd core && uv run pytest tests/integration/test_health.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd core && uv run pytest tests/integration/ -x -q`
- **Per wave merge:** `cd core && uv run pytest tests/ --cov=core --cov-report=term-missing`
- **Phase gate:** Full suite green + `docker compose up -d` smoke test

### Wave 0 Gaps
- [ ] `core/tests/integration/__init__.py` -- package init
- [ ] `core/tests/integration/conftest.py` -- shared MongoDB container fixture (session-scoped)
- [ ] `core/tests/integration/test_stream_repository.py` -- covers INFR-02-a
- [ ] `core/tests/integration/test_metric_repository.py` -- covers INFR-02-b
- [ ] `core/tests/integration/test_insight_repository.py` -- covers INFR-02-c
- [ ] `core/tests/integration/test_investigation_repository.py` -- covers INFR-02-d
- [ ] `core/tests/integration/test_thread_repository.py` -- covers INFR-02-e
- [ ] `core/tests/integration/test_invocation_repository.py` -- covers INFR-02-f
- [ ] `core/tests/integration/test_health.py` -- covers INFR-02-g
- [ ] Dependencies: `pymongo`, `fastapi`, `uvicorn`, `pydantic-settings`, `testcontainers[mongodb]`, `httpx`

## Recommended Index Definitions

Per Claude's discretion, these are the recommended indexes for each collection:

| Collection | Index | Type | Rationale |
|------------|-------|------|-----------|
| `streams` | `(source, stream_type, project_id)` | Compound | Primary query path for `get_by_key()` |
| `streams` | `(source, stream_type, project_id, timestamp)` | Compound, unique | Prevents duplicate data points if deterministic _id not used |
| `metrics` | `(metric_type, project_id)` | Compound | Primary query path for `get_by_key()` |
| `threads` | `(project_id,)` | Single | Required for `get_by_project_id()` |
| `invocations` | `(thread_id, status)` | Compound | Required for `get_pending_by_thread_id()` |
| `insights` | `(project_id,)` | Single | Future queries by project |
| `investigations` | `(project_id,)` | Single | Future queries by project |

## Sources

### Primary (HIGH confidence)
- [PyMongo 4.16.0 on PyPI](https://pypi.org/project/pymongo/) -- latest version, GA async support
- [Motor deprecation announcement](https://www.mongodb.com/community/forums/t/motor-3-7-1-released/321388) -- Motor 3.7.1 deprecated May 2025
- [PyMongo Async Migration Guide](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/) -- Motor to PyMongo async
- [Apache Kafka Docker Hub](https://hub.docker.com/r/apache/kafka) -- official images, latest 4.2.0
- [Confluent Kafka-on-Docker tutorial](https://developer.confluent.io/confluent-tutorials/kafka-on-docker/) -- KRaft mode compose config
- [testcontainers Python PyPI](https://pypi.org/project/testcontainers/) -- latest 4.14.2

### Secondary (MEDIUM confidence)
- [Redpanda Console Docker Hub](https://hub.docker.com/r/redpandadata/console) -- Kafka UI image
- [Mongo Express Docker Hub](https://hub.docker.com/_/mongo-express) -- MongoDB web UI image
- [FastAPI Docker multi-stage builds](https://dev.to/ismaarce/scalable-python-backend-building-a-containerized-fastapi-application-with-uv-docker-and-172j) -- uv + FastAPI Dockerfile patterns

### Tertiary (LOW confidence)
- PyMongo async tutorial code examples -- readthedocs returned 403, patterns reconstructed from API reference and search summaries

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- PyMongo async is the official replacement for Motor, well-documented. testcontainers and FastAPI are stable.
- Architecture: HIGH -- Decompose/assemble pattern is explicitly defined in CONTEXT.md decisions. File structure follows hexagonal conventions.
- Pitfalls: HIGH -- Motor deprecation is verified, datetime/enum issues are well-known MongoDB patterns.
- Docker Compose: MEDIUM -- KRaft mode config verified against Confluent tutorial, but exact health check commands may need adjustment.

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable domain, 30-day validity)
