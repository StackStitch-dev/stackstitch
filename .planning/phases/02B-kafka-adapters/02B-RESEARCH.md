# Phase 02B: Kafka Adapters - Research

**Researched:** 2026-04-02
**Domain:** Kafka messaging adapters (producer + consumer) for domain event system
**Confidence:** HIGH

## Summary

This phase implements Kafka adapters that bridge the domain event system (Phase 1) to real async messaging. The producer adapter implements the `EventPublisher` port, serializing domain events to JSON and publishing to a single `domain.events` topic. The consumer infrastructure subscribes to that topic, reads event_type from headers, and dispatches to registered handler functions.

confluent-kafka 2.14.0 provides GA-stable native asyncio support via `AIOProducer` and `AIOConsumer` (graduated from experimental in 2.13.0), eliminating the need for manual thread-pool bridges. The consumer runs as a separate process with its own Docker Compose service entry. Integration tests use testcontainers with `RedpandaContainer` for real Kafka round-trip verification.

**Primary recommendation:** Use confluent-kafka 2.14.0 with native `AIOProducer`/`AIOConsumer` for async Kafka operations. The asyncio API is now stable and supports context managers.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Single `domain.events` topic for all domain events
- D-02: Default partition key is `project_id`; MessageCreated and InsightCreated use `thread_id`
- D-03: Partition key derivation is adapter concern, domain stays clean
- D-04: JSON serialization via Pydantic `model_dump(mode="json")`
- D-05: Event type name as Kafka header (`event_type: "StreamUpdated"`)
- D-06: Schema Registry deferred to v2+
- D-07: Simple registry dict mapping `dict[str, Callable]` for consumer routing
- D-08: Handler functions receive deserialized DomainEvent and invoke use cases
- D-09: At-least-once delivery, commit after successful handler execution
- D-10: 5 retries with exponential backoff (1s, 2s, 4s, 8s, 16s) before DLQ
- D-11: Dead-letter topic: `domain.events.dlq` with error metadata headers
- D-12: Single consumer group: `core-service`
- D-13: Configurable partition count (default 3), topic creation at startup
- D-14: Single consumer instance, serial partition processing
- D-15: Adapters in `core/src/core/infrastructure/adapters/kafka/`
- D-16: One file for producer, one for consumer, one for shared config/connection
- D-17: Consumer runs as separate worker process, not inside FastAPI lifespan
- D-18: Multiple entry points: API (FastAPI) and Consumer (Kafka)
- D-19: Docker Compose `core-consumer` service alongside `core` service, same image different CMD

### Claude's Discretion
- confluent-kafka vs aiokafka library choice (CLAUDE.md recommends confluent-kafka)
- Exact consumer poll loop implementation (asyncio bridge for confluent-kafka, or native async with aiokafka)
- Topic creation strategy (auto-create vs explicit admin client)
- Test fixture design for Kafka testcontainers
- Entry point module structure (e.g., `core.entrypoints.api`, `core.entrypoints.consumer`)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFR-03 | Kafka handles async messaging between Connector Service and Core | confluent-kafka 2.14.0 with AIOProducer/AIOConsumer provides stable async Kafka client; producer implements EventPublisher port; consumer dispatches to use case handlers; integration tests verify round-trip with testcontainers |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| confluent-kafka | 2.14.0 | Kafka producer/consumer | Wraps librdkafka (C), fastest Python Kafka client. Native asyncio GA since 2.13.0. Context manager support in 2.14.0. CLAUDE.md recommends it. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| testcontainers[kafka] | >=4.14,<5 | Integration test Kafka container | Integration tests needing real Kafka broker |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| confluent-kafka | aiokafka | aiokafka is pure Python (slower, less reliable under load). confluent-kafka now has native asyncio, eliminating aiokafka's only advantage. |

### Discretion Recommendation: confluent-kafka

Use **confluent-kafka 2.14.0** with native `AIOProducer`/`AIOConsumer`. Reasons:
1. CLAUDE.md explicitly recommends confluent-kafka
2. Native asyncio support is now GA (no longer experimental)
3. 2.14.0 adds async context manager protocol -- clean resource management
4. Wraps battle-tested librdkafka -- superior throughput and reliability
5. AdminClient available for explicit topic creation

**Installation:**
```bash
cd core && uv add "confluent-kafka>=2.14,<3"
cd core && uv add --dev "testcontainers[kafka]>=4.14,<5"
```

Note: `testcontainers[mongodb]` is already a dev dependency. Adding `[kafka]` extra installs the Kafka module alongside it. Can combine: `testcontainers[mongodb,kafka]>=4.14,<5`.

## Architecture Patterns

### Recommended File Structure
```
core/src/core/infrastructure/adapters/kafka/
    __init__.py
    connection.py           # KafkaSettings, create_producer, create_consumer, AdminClient helpers
    event_producer.py       # KafkaEventPublisher implements EventPublisher port
    event_consumer.py       # KafkaEventConsumer with poll loop, routing, retry, DLQ

core/src/core/entrypoints/
    __init__.py
    api.py                  # Move/re-export create_app() from infrastructure.web.app
    consumer.py             # Consumer entry point: asyncio.run(main())
```

### Pattern 1: Kafka Producer Adapter (implements EventPublisher)

**What:** Adapter that serializes domain events to JSON and publishes to `domain.events` topic with appropriate partition key and event_type header.

**When to use:** Any use case that publishes domain events (all 6 existing use cases).

```python
# core/src/core/infrastructure/adapters/kafka/event_producer.py
from __future__ import annotations

from confluent_kafka.aio import AIOProducer
from core.application.ports.event_publisher import EventPublisher
from core.domain.events.domain_events import (
    DomainEvent, InsightCreated, MessageCreated,
)


class KafkaEventPublisher(EventPublisher):
    """Publishes domain events to Kafka topic as JSON."""

    TOPIC = "domain.events"

    def __init__(self, producer: AIOProducer) -> None:
        self._producer = producer

    async def publish(self, event: DomainEvent) -> None:
        key = self._partition_key(event)
        headers = [("event_type", type(event).__name__.encode())]
        value = event.model_dump_json().encode()
        await self._producer.produce(
            topic=self.TOPIC,
            key=key.encode() if key else None,
            value=value,
            headers=headers,
        )

    async def publish_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)
        await self._producer.flush()

    def _partition_key(self, event: DomainEvent) -> str | None:
        """D-02/D-03: Derive partition key from event type."""
        if isinstance(event, (MessageCreated, InsightCreated)):
            thread_id = getattr(event, "thread_id", None)
            return str(thread_id) if thread_id else None
        project_id = getattr(event, "project_id", None)
        return str(project_id) if project_id else None
```

### Pattern 2: Consumer Event Router

**What:** Registry-based routing from event_type header to handler functions.

```python
# core/src/core/infrastructure/adapters/kafka/event_consumer.py
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from confluent_kafka import KafkaError
from confluent_kafka.aio import AIOConsumer, AIOProducer

from core.domain.events.domain_events import DomainEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]

# Event type registry populated by application wiring
EVENT_REGISTRY: dict[str, type[DomainEvent]] = {}


class KafkaEventConsumer:
    """Consumes domain events from Kafka and routes to handlers."""

    TOPIC = "domain.events"
    DLQ_TOPIC = "domain.events.dlq"
    MAX_RETRIES = 5
    BACKOFF_BASE = 1  # seconds

    def __init__(
        self,
        consumer: AIOConsumer,
        dlq_producer: AIOProducer,
        handlers: dict[str, EventHandler],
    ) -> None:
        self._consumer = consumer
        self._dlq_producer = dlq_producer
        self._handlers = handlers
        self._running = False

    async def start(self) -> None:
        self._consumer.subscribe([self.TOPIC])
        self._running = True
        while self._running:
            msg = await self._consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error("Consumer error: %s", msg.error())
                continue
            await self._process_message(msg)

    async def stop(self) -> None:
        self._running = False
        self._consumer.close()

    async def _process_message(self, msg) -> None:
        event_type = self._extract_event_type(msg)
        if not event_type or event_type not in self._handlers:
            logger.warning("No handler for event_type=%s", event_type)
            return

        for attempt in range(self.MAX_RETRIES):
            try:
                event_class = EVENT_REGISTRY.get(event_type)
                if not event_class:
                    break
                event = event_class.model_validate_json(msg.value())
                await self._handlers[event_type](event)
                self._consumer.store_offsets(msg)
                return
            except Exception:
                delay = self.BACKOFF_BASE * (2 ** attempt)
                logger.exception(
                    "Handler failed for %s (attempt %d/%d), retry in %ds",
                    event_type, attempt + 1, self.MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)

        # All retries exhausted -- send to DLQ
        await self._send_to_dlq(msg, event_type)

    async def _send_to_dlq(self, msg, event_type: str | None) -> None:
        headers = list(msg.headers() or [])
        headers.extend([
            ("original_topic", self.TOPIC.encode()),
            ("error_event_type", (event_type or "unknown").encode()),
            ("retry_count", str(self.MAX_RETRIES).encode()),
        ])
        await self._dlq_producer.produce(
            topic=self.DLQ_TOPIC,
            key=msg.key(),
            value=msg.value(),
            headers=headers,
        )
        self._consumer.store_offsets(msg)

    @staticmethod
    def _extract_event_type(msg) -> str | None:
        headers = msg.headers()
        if not headers:
            return None
        for key, value in headers:
            if key == "event_type":
                return value.decode() if isinstance(value, bytes) else value
        return None
```

### Pattern 3: Connection/Config Module

**What:** Shared Kafka connection settings and client factory functions.

```python
# core/src/core/infrastructure/adapters/kafka/connection.py
from __future__ import annotations

from pydantic_settings import BaseSettings
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka.aio import AIOProducer, AIOConsumer


class KafkaSettings(BaseSettings):
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "domain.events"
    kafka_dlq_topic: str = "domain.events.dlq"
    kafka_consumer_group: str = "core-service"
    kafka_topic_partitions: int = 3
    kafka_auto_offset_reset: str = "earliest"

    model_config = {"env_prefix": ""}


def create_producer(settings: KafkaSettings) -> AIOProducer:
    return AIOProducer({
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "acks": "all",
    })


def create_consumer(settings: KafkaSettings) -> AIOConsumer:
    return AIOConsumer({
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "group.id": settings.kafka_consumer_group,
        "auto.offset.reset": settings.kafka_auto_offset_reset,
        "enable.auto.commit": False,  # D-09: manual commit after handler success
    })


def ensure_topics(settings: KafkaSettings) -> None:
    """Create topics if they don't exist. Called at startup."""
    admin = AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})
    topics = [
        NewTopic(settings.kafka_topic, num_partitions=settings.kafka_topic_partitions, replication_factor=1),
        NewTopic(settings.kafka_dlq_topic, num_partitions=1, replication_factor=1),
    ]
    fs = admin.create_topics(topics)
    for topic, f in fs.items():
        try:
            f.result()
        except Exception:
            pass  # Topic already exists -- safe to ignore
```

### Pattern 4: Consumer Entry Point

**What:** Separate process entry point for the Kafka consumer worker.

```python
# core/src/core/entrypoints/consumer.py
import asyncio
import signal

from core.infrastructure.adapters.kafka.connection import (
    KafkaSettings, create_consumer, create_producer, ensure_topics,
)
from core.infrastructure.adapters.kafka.event_consumer import KafkaEventConsumer


async def main() -> None:
    settings = KafkaSettings()
    ensure_topics(settings)

    consumer_client = create_consumer(settings)
    dlq_producer = create_producer(settings)

    # Wire handlers to use cases here
    handlers: dict = {}

    event_consumer = KafkaEventConsumer(
        consumer=consumer_client,
        dlq_producer=dlq_producer,
        handlers=handlers,
    )

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(event_consumer.stop()))

    await event_consumer.start()


if __name__ == "__main__":
    asyncio.run(main())
```

### Pattern 5: Docker Compose Consumer Service

**What:** Same image, different command for consumer worker.

```yaml
# Addition to docker-compose.yml
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

### Discretion Recommendation: Topic Creation Strategy

Use **explicit AdminClient topic creation** at consumer startup (not auto.create.topics). Reasons:
1. Explicit partition count control (D-13 requires configurable partitions)
2. DLQ topic needs different partition count (1 vs 3)
3. AdminClient.create_topics is idempotent -- safe to call on every startup
4. auto.create.topics.enable uses broker defaults which may not match requirements

### Discretion Recommendation: Entry Point Module Structure

Use `core.entrypoints.consumer` and keep `core.infrastructure.web.app` as-is for the API entry point. Reasons:
1. Consumer entry point is infrastructure, but `entrypoints/` is a clear top-level organizational concept
2. Moving/re-exporting the API entry point can be done later without breaking changes
3. Dockerfile CMD for consumer: `python -m core.entrypoints.consumer`
4. Keeps the existing API entry point stable (no refactor needed this phase)

### Anti-Patterns to Avoid
- **Running consumer inside FastAPI lifespan:** Blocked by D-17. Consumer must be a separate process for independent scaling and crash isolation.
- **Deserializing payload to determine event type:** Use the `event_type` header (D-05). Avoids polymorphic deserialization complexity.
- **Auto-committing offsets:** Violates D-09 at-least-once semantics. Must commit only after successful handler execution.
- **Catching and swallowing all exceptions silently:** Failed messages must go to DLQ after retry exhaustion (D-10/D-11). Never silently drop messages.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Kafka client | Custom socket protocol | confluent-kafka (librdkafka) | Protocol complexity, rebalancing, compression, batching |
| JSON serialization | Custom serializer | Pydantic model_dump_json() | Already built into domain events, handles UUID/datetime |
| Test Kafka broker | Docker scripts | testcontainers[kafka] | Lifecycle management, port allocation, cleanup |
| Topic admin | Shell scripts | AdminClient.create_topics | Programmatic, idempotent, integrated with settings |

## Common Pitfalls

### Pitfall 1: confluent-kafka C Extension Build Failures
**What goes wrong:** `pip install confluent-kafka` fails on some platforms without librdkafka headers.
**Why it happens:** confluent-kafka wraps librdkafka via C extensions. Some platforms need pre-built wheels.
**How to avoid:** Use `uv add` which fetches pre-built wheels. confluent-kafka 2.14.0 provides wheels for Python 3.8-3.14 on major platforms (linux, macOS, Windows). If building from source needed, install librdkafka-dev first.
**Warning signs:** Compilation errors mentioning `rdkafka.h` during install.

### Pitfall 2: Blocking the Event Loop with Sync Kafka Calls
**What goes wrong:** Using sync `Producer`/`Consumer` classes in an async context blocks the event loop.
**Why it happens:** The sync API calls librdkafka which blocks the calling thread.
**How to avoid:** Use `AIOProducer`/`AIOConsumer` from `confluent_kafka.aio` (stable since 2.13.0). These offload blocking calls to a thread pool automatically.
**Warning signs:** High latency in concurrent async operations when Kafka is active.

### Pitfall 3: Consumer Offset Commit Before Handler Completion
**What goes wrong:** Messages are lost when consumer commits offset but handler fails.
**Why it happens:** `enable.auto.commit=True` (default) commits offsets on a timer regardless of processing status.
**How to avoid:** Set `enable.auto.commit=False`, use `consumer.store_offsets(msg)` only after successful handler execution.
**Warning signs:** Missing events in downstream processing, especially after consumer restarts.

### Pitfall 4: Test Container Port Conflicts
**What goes wrong:** Kafka testcontainer fails to start due to port 9092 already in use by docker-compose Kafka.
**Why it happens:** Testcontainers allocates random ports, but if docker-compose Kafka is running, the internal broker port can conflict.
**How to avoid:** RedpandaContainer uses random host ports by default. Ensure tests don't hardcode port 9092. Stop docker-compose services before running integration tests if conflicts arise.
**Warning signs:** "Address already in use" errors in test output.

### Pitfall 5: Forgetting to Flush Producer Before Shutdown
**What goes wrong:** Messages buffered in the producer are lost on shutdown.
**Why it happens:** confluent-kafka batches messages for throughput. Unflushed messages are dropped.
**How to avoid:** Always call `await producer.flush()` before closing. The 2.14.0 context manager protocol handles this automatically with `async with`.
**Warning signs:** Published events never appearing in the topic.

### Pitfall 6: Headers Value Type Mismatch
**What goes wrong:** Headers with string values cause serialization errors or mismatches.
**Why it happens:** Kafka headers values must be `bytes`, not `str`.
**How to avoid:** Always encode header values: `("event_type", "StreamUpdated".encode())`. Decode on read: `value.decode()`.
**Warning signs:** TypeError on produce, or garbled header values on consume.

## Code Examples

### Verified: AIOProducer with Context Manager (confluent-kafka 2.14.0+)
```python
# Source: confluent-kafka 2.14.0 release notes
from confluent_kafka.aio import AIOProducer

async with AIOProducer({"bootstrap.servers": "localhost:9092"}) as producer:
    await producer.produce("my-topic", key=b"key", value=b"value")
    await producer.flush()
```

### Verified: AdminClient Topic Creation
```python
# Source: confluent-kafka docs / examples/adminapi.py
from confluent_kafka.admin import AdminClient, NewTopic

admin = AdminClient({"bootstrap.servers": "localhost:9092"})
new_topics = [NewTopic("domain.events", num_partitions=3, replication_factor=1)]
fs = admin.create_topics(new_topics)
for topic, f in fs.items():
    try:
        f.result()  # None on success
    except Exception as e:
        print(f"Failed to create {topic}: {e}")
```

### Verified: Testcontainers Kafka Fixture
```python
# Source: testcontainers-python docs
import pytest
from testcontainers.kafka import RedpandaContainer

@pytest.fixture(scope="session")
def kafka_container():
    with RedpandaContainer() as container:
        yield container

@pytest.fixture
def bootstrap_servers(kafka_container):
    return kafka_container.get_bootstrap_server()
```

### Pydantic Event Serialization for Kafka
```python
# Natural integration with existing domain events
from core.domain.events.domain_events import StreamUpdated

event = StreamUpdated(source="github", stream_type="pull_request", project_id=project_id)

# Serialize for Kafka value
value: bytes = event.model_dump_json().encode()

# Deserialize on consumer side
restored = StreamUpdated.model_validate_json(value)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| confluent-kafka + asyncio.to_thread bridge | Native AIOProducer/AIOConsumer | 2.13.0 (Jan 2025) | No manual thread pool bridging needed |
| `from confluent_kafka.experimental.aio` | `from confluent_kafka.aio` | 2.13.0 GA | Stable import path |
| Manual resource cleanup | `async with` context manager | 2.14.0 (Apr 2025) | Automatic flush and close |
| KafkaContainer (confluentinc image) | RedpandaContainer | testcontainers 4.x | Faster startup, lighter, Kafka-compatible |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 0.24+ |
| Config file | `core/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd core && uv run pytest tests/integration/test_kafka_producer.py tests/integration/test_kafka_consumer.py -x` |
| Full suite command | `cd core && uv run pytest -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFR-03a | KafkaEventPublisher.publish serializes event and sends to topic | integration | `cd core && uv run pytest tests/integration/test_kafka_producer.py -x` | Wave 0 |
| INFR-03b | KafkaEventPublisher.publish_many sends batch with correct headers | integration | `cd core && uv run pytest tests/integration/test_kafka_producer.py -x` | Wave 0 |
| INFR-03c | Partition key derivation (project_id default, thread_id for Message/Insight) | unit | `cd core && uv run pytest tests/unit/test_kafka_partition_key.py -x` | Wave 0 |
| INFR-03d | Consumer routes events to correct handlers via event_type header | integration | `cd core && uv run pytest tests/integration/test_kafka_consumer.py -x` | Wave 0 |
| INFR-03e | Consumer retries with exponential backoff, sends to DLQ after exhaustion | integration | `cd core && uv run pytest tests/integration/test_kafka_consumer.py -x` | Wave 0 |
| INFR-03f | Publish/consume round-trip: producer sends, consumer receives and deserializes | integration | `cd core && uv run pytest tests/integration/test_kafka_roundtrip.py -x` | Wave 0 |
| INFR-03g | Topic creation via AdminClient at startup | integration | `cd core && uv run pytest tests/integration/test_kafka_topics.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd core && uv run pytest tests/integration/test_kafka_producer.py tests/integration/test_kafka_consumer.py -x`
- **Per wave merge:** `cd core && uv run pytest -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/integration/test_kafka_producer.py` -- covers INFR-03a, INFR-03b
- [ ] `tests/integration/test_kafka_consumer.py` -- covers INFR-03d, INFR-03e
- [ ] `tests/integration/test_kafka_roundtrip.py` -- covers INFR-03f
- [ ] `tests/integration/test_kafka_topics.py` -- covers INFR-03g
- [ ] `tests/unit/test_kafka_partition_key.py` -- covers INFR-03c (no container needed)
- [ ] `tests/integration/conftest.py` -- add Kafka session fixture (RedpandaContainer)
- [ ] Dependency install: `uv add "confluent-kafka>=2.14,<3"` and `uv add --dev "testcontainers[kafka]>=4.14,<5"`

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Testcontainers, docker-compose | Yes | 29.3.1 | -- |
| Docker Compose | Consumer service | Yes | v5.1.1 | -- |
| Python | Runtime | Yes | 3.12+ | -- |
| confluent-kafka | Kafka adapter code | No (not yet installed) | Target: 2.14.0 | Must install via uv add |
| testcontainers[kafka] | Integration tests | No (only [mongodb] installed) | Target: >=4.14 | Must add kafka extra |
| Kafka broker (docker-compose) | Local dev/manual testing | Yes (in docker-compose.yml) | apache/kafka:latest | -- |

**Missing dependencies with no fallback:**
- confluent-kafka must be added to pyproject.toml dependencies
- testcontainers[kafka] must be added to dev dependencies

**Missing dependencies with fallback:**
- None -- all dependencies are installable via uv

## Open Questions

1. **AIOProducer.produce() return value**
   - What we know: The sync Producer.produce() fires a callback. AIOProducer.produce() returns an awaitable.
   - What's unclear: Exact return type -- is it the delivered Message or None? Does it raise on delivery failure?
   - Recommendation: Test empirically during implementation. The integration tests will validate behavior.

2. **RedpandaContainer vs KafkaContainer for testcontainers**
   - What we know: testcontainers-python provides `RedpandaContainer` in the kafka module. It's Kafka-compatible and faster to start.
   - What's unclear: Whether RedpandaContainer supports all confluent-kafka features (headers, admin API).
   - Recommendation: Use RedpandaContainer (standard in testcontainers-python kafka module). If any feature gap found, fall back to `KafkaContainer("confluentinc/cp-kafka:7.5.0")`.

3. **mypy typing for confluent-kafka**
   - What we know: confluent-kafka has type stubs but they may be incomplete for the async API.
   - What's unclear: Whether `AIOProducer`/`AIOConsumer` have complete type annotations.
   - Recommendation: Use `type: ignore` comments if needed for confluent-kafka imports. Don't let incomplete stubs block progress.

## Sources

### Primary (HIGH confidence)
- [confluent-kafka PyPI](https://pypi.org/project/confluent-kafka/) -- version 2.14.0, released 2026-04-02
- [confluent-kafka GitHub releases](https://github.com/confluentinc/confluent-kafka-python/releases) -- 2.13.0 asyncio GA, 2.14.0 context managers
- [Confluent Python client docs](https://docs.confluent.io/kafka-clients/python/current/overview.html) -- AIOProducer/AIOConsumer API
- [confluent-kafka asyncio example](https://github.com/confluentinc/confluent-kafka-python/blob/master/examples/asyncio_example.py) -- reference patterns
- Existing codebase: `core/src/core/application/ports/event_publisher.py`, `core/src/core/domain/events/domain_events.py`

### Secondary (MEDIUM confidence)
- [testcontainers-python kafka module](https://testcontainers-python.readthedocs.io/en/latest/modules/kafka/README.html) -- RedpandaContainer API
- [Confluent blog: Python asyncio GA](https://www.confluent.io/blog/confluent-kafka-clients-2-13-0-release-python-async/) -- asyncio graduation announcement

### Tertiary (LOW confidence)
- AIOProducer.produce() exact return semantics -- inferred from docs, needs empirical validation
- mypy type stub completeness for confluent_kafka.aio -- needs testing during implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- confluent-kafka 2.14.0 verified on PyPI, asyncio GA confirmed in release notes
- Architecture: HIGH -- patterns follow established codebase conventions (MongoDB adapter structure, pydantic-settings, testcontainers fixtures)
- Pitfalls: HIGH -- well-documented Kafka client gotchas, verified against official docs

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable library, 30-day validity)
