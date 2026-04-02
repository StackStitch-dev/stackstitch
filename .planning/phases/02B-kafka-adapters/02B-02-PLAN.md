---
phase: 02B-kafka-adapters
plan: 02
type: execute
wave: 2
depends_on: ["02B-01"]
files_modified:
  - core/tests/integration/conftest.py
  - core/tests/integration/test_kafka_producer.py
  - core/tests/integration/test_kafka_consumer.py
  - core/tests/integration/test_kafka_roundtrip.py
  - core/tests/unit/test_kafka_partition_key.py
autonomous: true
requirements: [INFR-03]

must_haves:
  truths:
    - "Producer publishes events with correct JSON payload and event_type header"
    - "Producer uses correct partition keys (project_id default, thread_id for Message/Insight)"
    - "Consumer receives events and routes to correct handler by event_type header"
    - "Consumer retries failed handlers and sends to DLQ after exhaustion"
    - "Full round-trip: publish event -> consume event -> handler invoked with deserialized DomainEvent"
  artifacts:
    - path: "core/tests/integration/conftest.py"
      provides: "Kafka testcontainer fixture (RedpandaContainer)"
      contains: "RedpandaContainer"
    - path: "core/tests/integration/test_kafka_producer.py"
      provides: "Integration tests for KafkaEventPublisher"
      min_lines: 40
    - path: "core/tests/integration/test_kafka_consumer.py"
      provides: "Integration tests for KafkaEventConsumer routing and DLQ"
      min_lines: 60
    - path: "core/tests/integration/test_kafka_roundtrip.py"
      provides: "End-to-end publish-consume round-trip test"
      min_lines: 30
    - path: "core/tests/unit/test_kafka_partition_key.py"
      provides: "Unit tests for partition key derivation logic"
      min_lines: 25
  key_links:
    - from: "core/tests/integration/conftest.py"
      to: "core/src/core/infrastructure/adapters/kafka/connection.py"
      via: "bootstrap_servers fixture used by producer/consumer creation"
      pattern: "get_bootstrap_server"
    - from: "core/tests/integration/test_kafka_producer.py"
      to: "core/src/core/infrastructure/adapters/kafka/event_producer.py"
      via: "KafkaEventPublisher under test"
      pattern: "KafkaEventPublisher"
    - from: "core/tests/integration/test_kafka_consumer.py"
      to: "core/src/core/infrastructure/adapters/kafka/event_consumer.py"
      via: "KafkaEventConsumer under test"
      pattern: "KafkaEventConsumer"
---

<objective>
Create integration tests verifying Kafka adapter behavior: producer publishes with correct serialization/headers/partition keys, consumer routes events to handlers and handles failures with DLQ, and full round-trip publish-consume works against a real Kafka broker.

Purpose: Satisfy INFR-03 success criterion #3 — integration tests verify publish/consume round-trips against real Kafka.
Output: Complete test suite covering all Kafka adapter behaviors, runnable via pytest with testcontainers.
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
@.planning/phases/02B-kafka-adapters/02B-01-SUMMARY.md

<interfaces>
<!-- Kafka adapter code created in Plan 01 -->
From core/src/core/infrastructure/adapters/kafka/connection.py:
```python
class KafkaSettings(BaseSettings):
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "domain.events"
    kafka_dlq_topic: str = "domain.events.dlq"
    kafka_consumer_group: str = "core-service"
    kafka_topic_partitions: int = 3
    kafka_auto_offset_reset: str = "earliest"

def create_producer(settings: KafkaSettings) -> AIOProducer: ...
def create_consumer(settings: KafkaSettings) -> AIOConsumer: ...
def ensure_topics(settings: KafkaSettings) -> None: ...
```

From core/src/core/infrastructure/adapters/kafka/event_producer.py:
```python
class KafkaEventPublisher(EventPublisher):
    TOPIC = "domain.events"
    def __init__(self, producer: AIOProducer) -> None: ...
    async def publish(self, event: DomainEvent) -> None: ...
    async def publish_many(self, events: list[DomainEvent]) -> None: ...
    def _partition_key(self, event: DomainEvent) -> str | None: ...
```

From core/src/core/infrastructure/adapters/kafka/event_consumer.py:
```python
EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]
EVENT_REGISTRY: dict[str, type[DomainEvent]] = {}

class KafkaEventConsumer:
    TOPIC = "domain.events"
    DLQ_TOPIC = "domain.events.dlq"
    MAX_RETRIES = 5
    BACKOFF_BASE = 1
    def __init__(self, consumer: AIOConsumer, dlq_producer: AIOProducer, handlers: dict[str, EventHandler]) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

From core/src/core/domain/events/domain_events.py:
```python
class StreamUpdated(DomainEvent):
    source: str
    stream_type: str
    project_id: UUID

class MessageCreated(DomainEvent):
    thread_id: UUID
    message_content: str

class InsightCreated(DomainEvent):
    insight_id: UUID
    investigation_id: UUID
    project_id: UUID
    thread_id: UUID | None = None
```

From core/tests/integration/conftest.py (existing pattern):
```python
@pytest.fixture(scope="session")
def mongo_container() -> MongoDbContainer:
    container = MongoDbContainer("mongo:7")
    container.start()
    yield container
    container.stop()

@pytest.fixture
async def mongo_db(mongo_container: MongoDbContainer) -> AsyncGenerator[AsyncDatabase]:
    ...
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Kafka testcontainer fixture and create unit tests for partition key derivation</name>
  <files>
    core/tests/integration/conftest.py
    core/tests/unit/test_kafka_partition_key.py
  </files>
  <read_first>
    core/tests/integration/conftest.py
    core/src/core/infrastructure/adapters/kafka/event_producer.py
    core/src/core/domain/events/domain_events.py
  </read_first>
  <action>
1. Update `core/tests/integration/conftest.py` to add Kafka fixtures alongside existing MongoDB fixtures:
   - Add import: `from testcontainers.kafka import RedpandaContainer`
   - Add session-scoped fixture `kafka_container`:
     ```python
     @pytest.fixture(scope="session")
     def kafka_container() -> RedpandaContainer:
         container = RedpandaContainer()
         container.start()
         yield container  # type: ignore[misc]
         container.stop()
     ```
   - Add function-scoped fixture `kafka_bootstrap_servers`:
     ```python
     @pytest.fixture
     def kafka_bootstrap_servers(kafka_container: RedpandaContainer) -> str:
         return kafka_container.get_bootstrap_server()
     ```
   - Add function-scoped fixture `kafka_settings` that creates a `KafkaSettings` with the testcontainer bootstrap servers and a unique consumer group per test (to avoid offset conflicts):
     ```python
     @pytest.fixture
     def kafka_settings(kafka_bootstrap_servers: str) -> KafkaSettings:
         import uuid
         from core.infrastructure.adapters.kafka.connection import KafkaSettings
         return KafkaSettings(
             kafka_bootstrap_servers=kafka_bootstrap_servers,
             kafka_consumer_group=f"test-{uuid.uuid4().hex[:8]}",
         )
     ```
   - Add fixture `kafka_ensure_topics` that calls `ensure_topics(kafka_settings)`:
     ```python
     @pytest.fixture
     def kafka_ensure_topics(kafka_settings: KafkaSettings) -> None:
         from core.infrastructure.adapters.kafka.connection import ensure_topics
         ensure_topics(kafka_settings)
     ```
   - Keep all existing MongoDB fixtures unchanged.

2. Create `core/tests/unit/test_kafka_partition_key.py` with unit tests (no Kafka broker needed):
   - Import `KafkaEventPublisher` and all domain event classes
   - Instantiate `KafkaEventPublisher` with a mock/None producer (partition key logic doesn't touch producer)
   - Actually: since `_partition_key` is a regular method (not async, doesn't touch producer), we can test it by constructing a publisher with a `None` producer and calling `publisher._partition_key(event)` directly. Or create a minimal mock. The simplest approach: create the publisher object using `object.__new__(KafkaEventPublisher)` to skip __init__, then call `_partition_key` directly.
   - Better approach: just instantiate with `producer=None` since `_partition_key` does not use `self._producer`. Add `# type: ignore` comment.
   - Test cases:
     - `test_partition_key_stream_updated_uses_project_id`: Create `StreamUpdated(source="github", stream_type="pr", project_id=uuid4())`, assert `publisher._partition_key(event) == str(event.project_id)`
     - `test_partition_key_metric_updated_uses_project_id`: Create `MetricUpdated(metric_type="cycle_time", project_id=uuid4())`, assert returns `str(event.project_id)`
     - `test_partition_key_anomaly_detected_uses_project_id`: Create `AnomalyDetected(metric_type="cycle_time", project_id=uuid4(), severity="high", description="spike", metric_value=10.0, threshold=5.0)`, assert returns `str(event.project_id)`
     - `test_partition_key_message_created_uses_thread_id`: Create `MessageCreated(thread_id=uuid4(), message_content="hello")`, assert `publisher._partition_key(event) == str(event.thread_id)` (per D-02)
     - `test_partition_key_insight_created_uses_thread_id`: Create `InsightCreated(insight_id=uuid4(), investigation_id=uuid4(), project_id=uuid4(), thread_id=uuid4())`, assert returns `str(event.thread_id)` (per D-02)
     - `test_partition_key_insight_created_no_thread_id_returns_none`: Create `InsightCreated(insight_id=uuid4(), investigation_id=uuid4(), project_id=uuid4(), thread_id=None)`, assert returns `None`
     - `test_partition_key_stream_data_point_created_uses_project_id`: Create `StreamDataPointCreated(source="github", stream_type="pr", project_id=uuid4(), timestamp=datetime.now(timezone.utc), data={"key": "val"})`, assert returns `str(event.project_id)`
  </action>
  <verify>
    <automated>cd /Users/jorgeandresdiaz/Documents/development/stackstitch/core && uv run pytest tests/unit/test_kafka_partition_key.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - conftest.py contains `from testcontainers.kafka import RedpandaContainer`
    - conftest.py contains `def kafka_container(`
    - conftest.py contains `def kafka_bootstrap_servers(`
    - conftest.py contains `def kafka_settings(`
    - conftest.py contains `def kafka_ensure_topics(`
    - conftest.py still contains `def mongo_container(` (existing fixture preserved)
    - test_kafka_partition_key.py contains `test_partition_key_stream_updated_uses_project_id`
    - test_kafka_partition_key.py contains `test_partition_key_message_created_uses_thread_id`
    - test_kafka_partition_key.py contains `test_partition_key_insight_created_uses_thread_id`
    - test_kafka_partition_key.py contains `test_partition_key_insight_created_no_thread_id_returns_none`
    - `uv run pytest tests/unit/test_kafka_partition_key.py -x` exits 0 with all tests passing
  </acceptance_criteria>
  <done>
    Kafka testcontainer fixtures added to conftest.py (session-scoped container, function-scoped settings), unit tests for all 7 partition key scenarios pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Create integration tests for producer, consumer, and round-trip</name>
  <files>
    core/tests/integration/test_kafka_producer.py
    core/tests/integration/test_kafka_consumer.py
    core/tests/integration/test_kafka_roundtrip.py
  </files>
  <read_first>
    core/tests/integration/conftest.py
    core/src/core/infrastructure/adapters/kafka/event_producer.py
    core/src/core/infrastructure/adapters/kafka/event_consumer.py
    core/src/core/infrastructure/adapters/kafka/connection.py
    core/src/core/domain/events/domain_events.py
  </read_first>
  <action>
1. Create `core/tests/integration/test_kafka_producer.py`:
   - Uses `kafka_settings` and `kafka_ensure_topics` fixtures from conftest
   - Creates AIOProducer via `create_producer(kafka_settings)` and AIOConsumer (for verification reads) in each test
   - `test_publish_single_event_serializes_to_json`:
     - Create `KafkaEventPublisher(producer)` and a `StreamUpdated` event
     - Call `await publisher.publish(event)`
     - Flush producer
     - Create a consumer subscribed to `domain.events`, poll for the message
     - Assert message value is valid JSON that contains `"source"`, `"stream_type"`, `"project_id"`
     - Assert headers contain `("event_type", b"StreamUpdated")`
   - `test_publish_single_event_sets_partition_key`:
     - Publish a `StreamUpdated` event with known `project_id`
     - Consume and assert `msg.key().decode() == str(project_id)`
   - `test_publish_many_sends_multiple_events`:
     - Create 3 different events (StreamUpdated, MetricUpdated, StreamDataPointCreated)
     - Call `await publisher.publish_many(events)`
     - Consume 3 messages, verify each has correct `event_type` header
   - `test_publish_event_type_header_matches_class_name`:
     - Publish `MessageCreated` event
     - Consume and verify header `event_type` equals `b"MessageCreated"`
   - Important: Each test should use a unique consumer group ID (from `kafka_settings` fixture) and subscribe with `auto.offset.reset=earliest` to read from beginning. After producing, use a short poll loop (max 10 seconds timeout) to consume messages.
   - Helper function `consume_messages(consumer, topic, count, timeout=10.0)` that polls until `count` messages received or `timeout` exceeded, returns list of messages.

2. Create `core/tests/integration/test_kafka_consumer.py`:
   - `test_consumer_routes_event_to_correct_handler`:
     - Create a mock handler (async function that appends received events to a list)
     - Register handler for `"StreamUpdated"` in handlers dict
     - Ensure `EVENT_REGISTRY` has `"StreamUpdated": StreamUpdated`
     - Produce a `StreamUpdated` event directly via AIOProducer (with event_type header)
     - Start `KafkaEventConsumer` in a background task
     - Wait (with timeout) until the handler list has 1 event
     - Stop consumer
     - Assert handler received the event and fields match
   - `test_consumer_ignores_unknown_event_type`:
     - Produce a message with header `event_type: "UnknownEvent"`
     - Start consumer with empty handlers dict
     - Produce a `StreamUpdated` with registered handler
     - Assert only the StreamUpdated handler was called (unknown was skipped)
   - `test_consumer_sends_to_dlq_after_retry_exhaustion`:
     - Create a handler that always raises `RuntimeError`
     - Register for `"StreamUpdated"`
     - Override `KafkaEventConsumer.MAX_RETRIES = 2` and `BACKOFF_BASE = 0.01` (for fast tests — don't wait 1+2+4+8+16 seconds)
     - Produce a StreamUpdated event
     - Start consumer in background
     - Wait for DLQ message (subscribe a separate consumer to `domain.events.dlq`)
     - Assert DLQ message has original payload and error metadata headers (`original_topic`, `error_event_type`, `retry_count`)
     - Stop consumer
   - Important: Use `asyncio.wait_for(coro, timeout=15)` to prevent tests hanging. Stop consumer in finally block. For the DLQ test, temporarily reduce retry count and backoff to keep test fast.

3. Create `core/tests/integration/test_kafka_roundtrip.py`:
   - `test_publish_consume_roundtrip`:
     - Create `KafkaEventPublisher` with AIOProducer
     - Create `KafkaEventConsumer` with AIOConsumer and a tracking handler
     - Publish a `StreamUpdated` event via the publisher
     - Start consumer in background task
     - Wait until handler receives the event
     - Stop consumer
     - Assert received event `source`, `stream_type`, `project_id` match the published event
     - Assert received event is an instance of `StreamUpdated` (not raw DomainEvent)
   - `test_roundtrip_preserves_uuid_fields`:
     - Publish an `InsightCreated` event with known UUIDs
     - Consume and assert `insight_id`, `investigation_id`, `project_id`, `thread_id` are all UUIDs matching the originals (verifies Pydantic JSON serialization round-trip handles UUIDs correctly)
   - Important: Ensure `EVENT_REGISTRY` is populated before consumer starts. Either populate it in the test setup or import the module that populates it.
  </action>
  <verify>
    <automated>cd /Users/jorgeandresdiaz/Documents/development/stackstitch/core && uv run pytest tests/integration/test_kafka_producer.py tests/integration/test_kafka_consumer.py tests/integration/test_kafka_roundtrip.py -x -v --timeout=120</automated>
  </verify>
  <acceptance_criteria>
    - test_kafka_producer.py contains `test_publish_single_event_serializes_to_json`
    - test_kafka_producer.py contains `test_publish_many_sends_multiple_events`
    - test_kafka_producer.py contains `test_publish_event_type_header_matches_class_name`
    - test_kafka_consumer.py contains `test_consumer_routes_event_to_correct_handler`
    - test_kafka_consumer.py contains `test_consumer_sends_to_dlq_after_retry_exhaustion`
    - test_kafka_roundtrip.py contains `test_publish_consume_roundtrip`
    - test_kafka_roundtrip.py contains `test_roundtrip_preserves_uuid_fields`
    - All test files import from `core.infrastructure.adapters.kafka`
    - `uv run pytest tests/integration/test_kafka_producer.py tests/integration/test_kafka_consumer.py tests/integration/test_kafka_roundtrip.py -x` exits 0
  </acceptance_criteria>
  <done>
    Integration tests verify: producer serializes events to JSON with correct headers and partition keys, consumer routes events to handlers by event_type header, failed handlers retry and go to DLQ, full round-trip preserves event data including UUID fields
  </done>
</task>

</tasks>

<verification>
1. Unit tests pass: `cd core && uv run pytest tests/unit/test_kafka_partition_key.py -x -v`
2. Integration tests pass: `cd core && uv run pytest tests/integration/test_kafka_producer.py tests/integration/test_kafka_consumer.py tests/integration/test_kafka_roundtrip.py -x -v`
3. Full suite still green: `cd core && uv run pytest -x`
</verification>

<success_criteria>
- RedpandaContainer fixture provides real Kafka broker for integration tests
- Producer tests verify JSON serialization, event_type headers, partition keys, and batch publishing
- Consumer tests verify event routing by header, DLQ after retry exhaustion
- Round-trip test verifies end-to-end publish -> consume -> deserialize with UUID field preservation
- All tests pass against real Kafka (no mocking of Kafka client)
- Full test suite (including existing MongoDB tests) still passes
</success_criteria>

<output>
After completion, create `.planning/phases/02B-kafka-adapters/02B-02-SUMMARY.md`
</output>
