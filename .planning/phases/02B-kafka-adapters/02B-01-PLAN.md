---
phase: 02B-kafka-adapters
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/pyproject.toml
  - core/src/core/infrastructure/adapters/kafka/__init__.py
  - core/src/core/infrastructure/adapters/kafka/connection.py
  - core/src/core/infrastructure/adapters/kafka/event_producer.py
  - core/src/core/infrastructure/adapters/kafka/event_consumer.py
  - core/src/core/entrypoints/__init__.py
  - core/src/core/entrypoints/consumer.py
  - docker-compose.yml
autonomous: true
requirements: [INFR-03]

must_haves:
  truths:
    - "KafkaEventPublisher implements EventPublisher ABC with publish() and publish_many()"
    - "KafkaEventConsumer routes events to handlers by event_type header"
    - "Consumer retries failed handlers 5 times with exponential backoff then sends to DLQ"
    - "Consumer runs as a separate Docker Compose service (core-consumer)"
    - "Topics are created at startup via AdminClient"
  artifacts:
    - path: "core/src/core/infrastructure/adapters/kafka/connection.py"
      provides: "KafkaSettings, create_producer, create_consumer, ensure_topics"
      exports: ["KafkaSettings", "create_producer", "create_consumer", "ensure_topics"]
    - path: "core/src/core/infrastructure/adapters/kafka/event_producer.py"
      provides: "KafkaEventPublisher implementing EventPublisher port"
      exports: ["KafkaEventPublisher"]
    - path: "core/src/core/infrastructure/adapters/kafka/event_consumer.py"
      provides: "KafkaEventConsumer with poll loop, routing, retry, DLQ"
      exports: ["KafkaEventConsumer", "EventHandler", "EVENT_REGISTRY"]
    - path: "core/src/core/entrypoints/consumer.py"
      provides: "Standalone consumer process entry point"
    - path: "docker-compose.yml"
      provides: "core-consumer service alongside core API service"
      contains: "core-consumer"
  key_links:
    - from: "core/src/core/infrastructure/adapters/kafka/event_producer.py"
      to: "core/src/core/application/ports/event_publisher.py"
      via: "class inheritance"
      pattern: "class KafkaEventPublisher\\(EventPublisher\\)"
    - from: "core/src/core/infrastructure/adapters/kafka/event_producer.py"
      to: "core/src/core/domain/events/domain_events.py"
      via: "partition key derivation"
      pattern: "isinstance.*MessageCreated.*InsightCreated"
    - from: "core/src/core/entrypoints/consumer.py"
      to: "core/src/core/infrastructure/adapters/kafka/event_consumer.py"
      via: "instantiation and startup"
      pattern: "KafkaEventConsumer"
    - from: "docker-compose.yml"
      to: "core/src/core/entrypoints/consumer.py"
      via: "container command"
      pattern: "python.*-m.*core.entrypoints.consumer"
---

<objective>
Implement Kafka adapter infrastructure: connection/config module, producer adapter (EventPublisher port), consumer with routing/retry/DLQ, consumer entry point, and Docker Compose consumer service.

Purpose: Bridge the domain event system to real async messaging through Kafka, enabling services to communicate via events.
Output: Complete Kafka adapter code and Docker Compose consumer service, ready for integration testing in Plan 02.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02B-kafka-adapters/02B-CONTEXT.md
@.planning/phases/02B-kafka-adapters/02B-RESEARCH.md

<interfaces>
<!-- EventPublisher port the Kafka producer MUST implement -->
From core/src/core/application/ports/event_publisher.py:
```python
class EventPublisher(abc.ABC):
    @abc.abstractmethod
    async def publish(self, event: DomainEvent) -> None: ...

    @abc.abstractmethod
    async def publish_many(self, events: list[DomainEvent]) -> None: ...
```

From core/src/core/domain/events/domain_events.py:
```python
class DomainEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StreamDataPointCreated(DomainEvent): ...  # has project_id: UUID
class StreamUpdated(DomainEvent): ...           # has project_id: UUID
class MetricUpdated(DomainEvent): ...           # has project_id: UUID
class AnomalyDetected(DomainEvent): ...         # has project_id: UUID
class InsightCreated(DomainEvent): ...          # has project_id: UUID, thread_id: UUID | None
class MessageCreated(DomainEvent): ...          # has thread_id: UUID
```

From core/src/core/infrastructure/adapters/mongodb/connection.py (pattern to replicate):
```python
async def create_mongo_client(uri: str) -> AsyncMongoClient:
    client: AsyncMongoClient = AsyncMongoClient(uri)
    return client

def get_database(client: AsyncMongoClient, db_name: str) -> AsyncDatabase:
    return client.get_database(db_name, codec_options=CodecOptions(tz_aware=True))
```

From core/src/core/infrastructure/web/app.py (settings pattern):
```python
class CoreSettings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017/"
    mongodb_database: str = "stackstitch"
    model_config = {"env_prefix": ""}
```

From docker-compose.yml (Kafka container):
```yaml
kafka:
    image: apache/kafka:latest
    container_name: stackstitch-kafka
    ports:
      - "9092:9092"
    environment:
      KAFKA_LISTENERS: PLAINTEXT://kafka:29092,CONTROLLER://kafka:29093,PLAINTEXT_HOST://0.0.0.0:9092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
    healthcheck: ...
```

From core/pyproject.toml (current dependencies):
```toml
dependencies = [
    "pydantic>=2.12,<3",
    "pymongo>=4.16,<5",
    "fastapi>=0.115,<1",
    "uvicorn>=0.32,<1",
    "pydantic-settings>=2.7,<3",
]
[dependency-groups]
dev = [
    "pytest>=9.0,<10",
    "pytest-asyncio>=0.24,<2",
    "pytest-cov>=6.0,<7",
    "ruff>=0.15,<1",
    "mypy>=1.20,<2",
    "testcontainers[mongodb]>=4.14,<5",
    "httpx>=0.28,<1",
]
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Install confluent-kafka dependency and create Kafka adapter modules (connection, producer, consumer)</name>
  <files>
    core/pyproject.toml
    core/src/core/infrastructure/adapters/kafka/__init__.py
    core/src/core/infrastructure/adapters/kafka/connection.py
    core/src/core/infrastructure/adapters/kafka/event_producer.py
    core/src/core/infrastructure/adapters/kafka/event_consumer.py
  </files>
  <read_first>
    core/pyproject.toml
    core/src/core/application/ports/event_publisher.py
    core/src/core/domain/events/domain_events.py
    core/src/core/infrastructure/adapters/mongodb/connection.py
    core/src/core/infrastructure/web/app.py
    core/src/core/infrastructure/adapters/mongodb/__init__.py
  </read_first>
  <action>
1. Install dependencies:
   ```bash
   cd core && uv add "confluent-kafka>=2.14,<3"
   cd core && uv add --dev "testcontainers[mongodb,kafka]>=4.14,<5"
   ```
   Note: The testcontainers line replaces the existing `testcontainers[mongodb]` entry with `testcontainers[mongodb,kafka]` — same package, additional extra.

2. Create `core/src/core/infrastructure/adapters/kafka/__init__.py` — empty file (consistent with mongodb adapter package).

3. Create `core/src/core/infrastructure/adapters/kafka/connection.py` with:
   - `KafkaSettings(BaseSettings)` class with fields:
     - `kafka_bootstrap_servers: str = "localhost:9092"`
     - `kafka_topic: str = "domain.events"` (per D-01)
     - `kafka_dlq_topic: str = "domain.events.dlq"` (per D-11)
     - `kafka_consumer_group: str = "core-service"` (per D-12)
     - `kafka_topic_partitions: int = 3` (per D-13)
     - `kafka_auto_offset_reset: str = "earliest"`
     - `model_config = {"env_prefix": ""}` (matches CoreSettings pattern)
   - `def create_producer(settings: KafkaSettings) -> AIOProducer` — returns `AIOProducer({"bootstrap.servers": settings.kafka_bootstrap_servers, "acks": "all"})`
   - `def create_consumer(settings: KafkaSettings) -> AIOConsumer` — returns `AIOConsumer({"bootstrap.servers": settings.kafka_bootstrap_servers, "group.id": settings.kafka_consumer_group, "auto.offset.reset": settings.kafka_auto_offset_reset, "enable.auto.commit": False})` (per D-09: manual commit)
   - `def ensure_topics(settings: KafkaSettings) -> None` — uses `AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})` to create `NewTopic(settings.kafka_topic, num_partitions=settings.kafka_topic_partitions, replication_factor=1)` and `NewTopic(settings.kafka_dlq_topic, num_partitions=1, replication_factor=1)`. Calls `admin.create_topics(topics)`, iterates futures, ignores `TopicAlreadyExistsError` (idempotent).
   - Import from `confluent_kafka.aio` for AIOProducer/AIOConsumer, `confluent_kafka.admin` for AdminClient/NewTopic.

4. Create `core/src/core/infrastructure/adapters/kafka/event_producer.py` with:
   - `class KafkaEventPublisher(EventPublisher):` — implements the ABC from `core.application.ports.event_publisher`
   - Class constant `TOPIC = "domain.events"` (per D-01)
   - `__init__(self, producer: AIOProducer) -> None` — stores `self._producer = producer`
   - `async def publish(self, event: DomainEvent) -> None` — calls `self._producer.produce(topic=self.TOPIC, key=key.encode() if key else None, value=event.model_dump_json().encode(), headers=[("event_type", type(event).__name__.encode())])` (per D-04, D-05)
   - `async def publish_many(self, events: list[DomainEvent]) -> None` — loops `publish()` for each event, then calls `self._producer.flush()` at the end (per research Pitfall 5)
   - `def _partition_key(self, event: DomainEvent) -> str | None` — per D-02/D-03:
     - If `isinstance(event, (MessageCreated, InsightCreated))`: return `str(event.thread_id)` if `event.thread_id` is not None, else None
     - Otherwise: return `str(event.project_id)` if `hasattr(event, "project_id")` and `event.project_id` is not None, else None
   - Import `DomainEvent, InsightCreated, MessageCreated` from `core.domain.events.domain_events`

5. Create `core/src/core/infrastructure/adapters/kafka/event_consumer.py` with:
   - Type alias `EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]`
   - Module-level `EVENT_REGISTRY: dict[str, type[DomainEvent]] = {}` — maps event type name strings to event classes. Populated at startup wiring time. All 7 event classes registered: `{"StreamDataPointCreated": StreamDataPointCreated, "StreamUpdated": StreamUpdated, "MetricUpdated": MetricUpdated, "AnomalyDetected": AnomalyDetected, "InsightCreated": InsightCreated, "MessageCreated": MessageCreated}`. (Note: base DomainEvent is NOT registered — it's abstract.)
   - `class KafkaEventConsumer:` with:
     - Class constants: `TOPIC = "domain.events"`, `DLQ_TOPIC = "domain.events.dlq"`, `MAX_RETRIES = 5`, `BACKOFF_BASE = 1` (seconds)
     - `__init__(self, consumer: AIOConsumer, dlq_producer: AIOProducer, handlers: dict[str, EventHandler]) -> None` — stores consumer, dlq_producer, handlers, sets `self._running = False`
     - `async def start(self) -> None` — subscribes consumer to `[self.TOPIC]`, sets `self._running = True`, enters poll loop: `msg = await self._consumer.poll(timeout=1.0)`, skip None, skip `_PARTITION_EOF`, log other errors, else call `self._process_message(msg)` (per D-09: commit only after success)
     - `async def stop(self) -> None` — sets `self._running = False`, calls `self._consumer.close()`
     - `async def _process_message(self, msg) -> None` — extracts event_type via `_extract_event_type(msg)` (per D-05), checks handler exists in `self._handlers` dict (per D-07), loops retry with `range(self.MAX_RETRIES)`:
       - Looks up `EVENT_REGISTRY[event_type]` to get the event class
       - Deserializes: `event_class.model_validate_json(msg.value())`
       - Calls `await self._handlers[event_type](event)` (per D-08)
       - On success: `self._consumer.store_offsets(msg)` and return
       - On exception: compute `delay = self.BACKOFF_BASE * (2 ** attempt)` (yields 1, 2, 4, 8, 16 seconds per D-10), log with `logger.exception(...)`, `await asyncio.sleep(delay)`
     - After retry exhaustion: call `await self._send_to_dlq(msg, event_type)` (per D-10, D-11)
     - `async def _send_to_dlq(self, msg, event_type: str | None) -> None` — copies original headers, appends `("original_topic", self.TOPIC.encode())`, `("error_event_type", (event_type or "unknown").encode())`, `("retry_count", str(self.MAX_RETRIES).encode())` (per D-11). Produces to `self.DLQ_TOPIC`. Stores offset on original message after DLQ send.
     - `@staticmethod def _extract_event_type(msg) -> str | None` — reads headers list, finds `"event_type"` key, returns `value.decode()` if bytes else value. Returns None if no headers or key not found.
   - Use `import logging; logger = logging.getLogger(__name__)`
  </action>
  <verify>
    <automated>cd /Users/jorgeandresdiaz/Documents/development/stackstitch/core && uv run python -c "from core.infrastructure.adapters.kafka.connection import KafkaSettings, create_producer, create_consumer, ensure_topics; from core.infrastructure.adapters.kafka.event_producer import KafkaEventPublisher; from core.infrastructure.adapters.kafka.event_consumer import KafkaEventConsumer, EVENT_REGISTRY, EventHandler; print('All imports OK')"</automated>
  </verify>
  <acceptance_criteria>
    - core/pyproject.toml contains `"confluent-kafka>=2.14,<3"` in dependencies
    - core/pyproject.toml contains `testcontainers[mongodb,kafka]` in dev dependencies
    - core/src/core/infrastructure/adapters/kafka/__init__.py exists
    - connection.py contains `class KafkaSettings(BaseSettings):`
    - connection.py contains `kafka_bootstrap_servers: str`
    - connection.py contains `kafka_consumer_group: str = "core-service"`
    - connection.py contains `enable.auto.commit.*False`
    - connection.py contains `def ensure_topics(`
    - connection.py contains `AdminClient`
    - event_producer.py contains `class KafkaEventPublisher(EventPublisher):`
    - event_producer.py contains `async def publish(self, event: DomainEvent)`
    - event_producer.py contains `async def publish_many(self, events: list[DomainEvent])`
    - event_producer.py contains `def _partition_key(self, event: DomainEvent)`
    - event_producer.py contains `isinstance(event, (MessageCreated, InsightCreated))`
    - event_producer.py contains `model_dump_json().encode()`
    - event_producer.py contains `("event_type", type(event).__name__.encode())`
    - event_consumer.py contains `class KafkaEventConsumer:`
    - event_consumer.py contains `MAX_RETRIES = 5`
    - event_consumer.py contains `BACKOFF_BASE = 1`
    - event_consumer.py contains `DLQ_TOPIC = "domain.events.dlq"`
    - event_consumer.py contains `EVENT_REGISTRY: dict[str, type[DomainEvent]]`
    - event_consumer.py contains `store_offsets(msg)`
    - event_consumer.py contains `_send_to_dlq`
    - event_consumer.py contains `_extract_event_type`
  </acceptance_criteria>
  <done>
    confluent-kafka installed, KafkaSettings created with all config fields, KafkaEventPublisher implements EventPublisher with partition key derivation per D-02/D-03, KafkaEventConsumer has poll loop with routing/retry/DLQ per D-07 through D-11, all modules importable without errors
  </done>
</task>

<task type="auto">
  <name>Task 2: Create consumer entry point and add core-consumer service to Docker Compose</name>
  <files>
    core/src/core/entrypoints/__init__.py
    core/src/core/entrypoints/consumer.py
    docker-compose.yml
  </files>
  <read_first>
    docker-compose.yml
    core/Dockerfile
    core/src/core/infrastructure/web/app.py
    core/src/core/infrastructure/adapters/kafka/connection.py
    core/src/core/infrastructure/adapters/kafka/event_consumer.py
  </read_first>
  <action>
1. Create `core/src/core/entrypoints/__init__.py` — empty file.

2. Create `core/src/core/entrypoints/consumer.py` with:
   - `import asyncio`, `import signal`, `import logging`
   - Import `KafkaSettings, create_consumer, create_producer, ensure_topics` from `core.infrastructure.adapters.kafka.connection`
   - Import `KafkaEventConsumer` from `core.infrastructure.adapters.kafka.event_consumer`
   - `logger = logging.getLogger(__name__)`
   - `async def main() -> None:` function that:
     - Creates `settings = KafkaSettings()`
     - Calls `ensure_topics(settings)` to create topics at startup (per D-13)
     - Creates `consumer_client = create_consumer(settings)`
     - Creates `dlq_producer = create_producer(settings)`
     - Defines empty `handlers: dict[str, ...]` dict — placeholder comment: `# Wire use case handlers here in later phases`
     - Instantiates `event_consumer = KafkaEventConsumer(consumer=consumer_client, dlq_producer=dlq_producer, handlers=handlers)`
     - Registers signal handlers: `loop = asyncio.get_running_loop()`, for SIGTERM and SIGINT add handler `lambda: asyncio.create_task(event_consumer.stop())`
     - Logs `"Starting Kafka event consumer..."` at INFO level
     - Calls `await event_consumer.start()`
   - `if __name__ == "__main__":` block that calls `asyncio.run(main())`
   - Per D-17: this is a standalone process, NOT inside FastAPI lifespan
   - Per D-18: this is the consumer entry point alongside the API entry point

3. Update `docker-compose.yml` to add `core-consumer` service (per D-19):
   - Add after the existing `core` service block:
   ```yaml
     core-consumer:
       build:
         context: ./core
         dockerfile: Dockerfile
       container_name: stackstitch-core-consumer
       environment:
         MONGODB_URI: mongodb://mongodb:27017/
         MONGODB_DATABASE: stackstitch
         KAFKA_BOOTSTRAP_SERVERS: kafka:29092
       depends_on:
         kafka:
           condition: service_healthy
         mongodb:
           condition: service_healthy
       command: ["python", "-m", "core.entrypoints.consumer"]
   ```
   Note: Uses `kafka:29092` (internal PLAINTEXT listener), NOT `localhost:9092` (host-mapped). Same image as `core` but with different CMD override (per D-19). No port mapping needed — consumer is not an HTTP server.
   Also add `KAFKA_BOOTSTRAP_SERVERS: kafka:29092` to the existing `core` service environment block (so the API can also publish events in later phases).
  </action>
  <verify>
    <automated>cd /Users/jorgeandresdiaz/Documents/development/stackstitch/core && uv run python -c "from core.entrypoints.consumer import main; print('Consumer entry point importable')" && grep -c "core-consumer" /Users/jorgeandresdiaz/Documents/development/stackstitch/docker-compose.yml</automated>
  </verify>
  <acceptance_criteria>
    - core/src/core/entrypoints/__init__.py exists
    - consumer.py contains `async def main() -> None:`
    - consumer.py contains `KafkaSettings()`
    - consumer.py contains `ensure_topics(settings)`
    - consumer.py contains `create_consumer(settings)`
    - consumer.py contains `create_producer(settings)`
    - consumer.py contains `KafkaEventConsumer(`
    - consumer.py contains `signal.SIGTERM`
    - consumer.py contains `asyncio.run(main())`
    - consumer.py contains `if __name__ == "__main__":`
    - docker-compose.yml contains `core-consumer:`
    - docker-compose.yml contains `stackstitch-core-consumer`
    - docker-compose.yml contains `python.*-m.*core.entrypoints.consumer`
    - docker-compose.yml contains `KAFKA_BOOTSTRAP_SERVERS: kafka:29092` (at least twice — core and core-consumer)
    - docker-compose.yml core-consumer depends_on kafka with `condition: service_healthy`
  </acceptance_criteria>
  <done>
    Consumer entry point exists at core.entrypoints.consumer with signal handling and graceful shutdown, Docker Compose has core-consumer service using same image with different command, Kafka bootstrap servers configured for both core services
  </done>
</task>

</tasks>

<verification>
1. All Kafka adapter modules import without error: `cd core && uv run python -c "from core.infrastructure.adapters.kafka.connection import KafkaSettings; from core.infrastructure.adapters.kafka.event_producer import KafkaEventPublisher; from core.infrastructure.adapters.kafka.event_consumer import KafkaEventConsumer"`
2. Consumer entry point importable: `cd core && uv run python -c "from core.entrypoints.consumer import main"`
3. Docker Compose validates: `docker compose config --quiet`
4. KafkaEventPublisher is a subclass of EventPublisher: `cd core && uv run python -c "from core.infrastructure.adapters.kafka.event_producer import KafkaEventPublisher; from core.application.ports.event_publisher import EventPublisher; assert issubclass(KafkaEventPublisher, EventPublisher)"`
</verification>

<success_criteria>
- KafkaEventPublisher implements EventPublisher ABC (publish, publish_many)
- Partition key derivation uses project_id by default, thread_id for MessageCreated/InsightCreated
- KafkaEventConsumer routes events via event_type header to handler dict
- Consumer retries 5 times with 1/2/4/8/16s backoff before DLQ
- Consumer entry point is a standalone asyncio process with signal handling
- Docker Compose has core-consumer service using same image, different command
- All imports succeed, docker compose config validates
</success_criteria>

<output>
After completion, create `.planning/phases/02B-kafka-adapters/02B-01-SUMMARY.md`
</output>
