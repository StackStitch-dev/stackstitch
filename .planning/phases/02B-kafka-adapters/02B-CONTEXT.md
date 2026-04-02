# Phase 2b: Kafka Adapters - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Kafka producer adapter implementing the EventPublisher port, plus consumer infrastructure that subscribes to topics and dispatches events to use case handlers. This phase connects the domain event system (defined in Phase 1) to real async messaging through Kafka (running since Phase 2a).

**NOT in scope:** Schema Registry (deferred to v2+), new domain events or use cases, REST API changes, MongoDB changes, connector service integration.

</domain>

<decisions>
## Implementation Decisions

### Topic Mapping Strategy
- **D-01:** Single `domain.events` topic for all domain events. No per-type or per-aggregate topics.
- **D-02:** Default partition key is `project_id` (string). Exception: `MessageCreated` and `InsightCreated` events use `thread_id` as partition key to preserve ordering within conversations.
- **D-03:** Partition key derivation is an adapter concern. The producer adapter inspects the event type and picks the appropriate key. Domain layer stays clean — no partition_hint field on DomainEvent.

### Serialization Format
- **D-04:** JSON serialization via Pydantic `model_dump(mode="json")`. Human-readable, compatible with Kafka UI for debugging.
- **D-05:** Event type name stored as a Kafka message header (`event_type: "StreamUpdated"`). Consumer uses this header for routing — no need to deserialize the payload to determine the type.
- **D-06:** Schema Registry deferred to v2+. No Avro, no schema validation at the broker level for now.

### Consumer Routing Design
- **D-07:** Simple registry dict mapping: `dict[str, Callable]` maps event_type strings to async handler functions. Consumer reads event_type header, looks up handler, calls it.
- **D-08:** Handler functions receive the deserialized DomainEvent and invoke the appropriate use case. Explicit, easy to test, no decorator magic.

### Error Handling & Delivery
- **D-09:** At-least-once delivery semantics. Consumer commits offset only after successful handler execution.
- **D-10:** 5 retries with exponential backoff (1s, 2s, 4s, 8s, 16s) before routing to dead-letter topic.
- **D-11:** Dead-letter topic: `domain.events.dlq`. Failed messages include original headers plus error metadata (exception type, retry count, timestamp).

### Consumer Group & Concurrency
- **D-12:** Single consumer group: `core-service`.
- **D-13:** `domain.events` topic has configurable partition count (via pydantic-settings), default 3. Topic creation handled at startup if auto.create.topics is disabled.
- **D-14:** Single consumer instance processes all assigned partitions serially. Horizontal scaling deferred — v1 is single-user, single-project.

### Adapter Code Location
- **D-15:** Kafka adapters live in `core/src/core/infrastructure/adapters/kafka/`. Consistent with MongoDB adapters in `core/src/core/infrastructure/adapters/mongodb/` (Phase 2a D-14).
- **D-16:** One file for the producer adapter (implements EventPublisher), one file for the consumer infrastructure, one for shared config/connection.

### Consumer Lifecycle & Entry Points
- **D-17:** Consumer runs as a separate worker process, NOT inside the FastAPI lifespan. Separate entry point within the core module.
- **D-18:** Core module defines multiple entry points that become deployable artifacts:
  - **API entrypoint** — FastAPI server (existing from Phase 2a)
  - **Consumer entrypoint** — Kafka event consumer (new in this phase)
  - Each entry point can be deployed in its own Docker container.
- **D-19:** Docker Compose updated to run consumer as a separate service (`core-consumer`) alongside existing `core` (API) service. Both use the same Docker image with different commands.

### Claude's Discretion
- confluent-kafka vs aiokafka library choice (CLAUDE.md recommends confluent-kafka)
- Exact consumer poll loop implementation (asyncio bridge for confluent-kafka, or native async with aiokafka)
- Topic creation strategy (auto-create vs explicit admin client)
- Test fixture design for Kafka testcontainers
- Entry point module structure (e.g., `core.entrypoints.api`, `core.entrypoints.consumer`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Domain Event System (Phase 1)
- `core/src/core/application/ports/event_publisher.py` -- EventPublisher ABC with publish() and publish_many()
- `core/src/core/domain/events/domain_events.py` -- All 7 domain event classes (DomainEvent base, StreamDataPointCreated, StreamUpdated, MetricUpdated, AnomalyDetected, InsightCreated, MessageCreated)
- `core/src/core/domain/events/__init__.py` -- Event exports

### Use Cases (Event Producers)
- `core/src/core/application/use_cases/ingest_stream_data.py` -- Publishes StreamDataPointCreated
- `core/src/core/application/use_cases/process_stream_data_point.py` -- Publishes StreamUpdated
- `core/src/core/application/use_cases/process_stream_update.py` -- Calls MetricsCalculator, publishes MetricUpdated
- `core/src/core/application/use_cases/monitor_metric.py` -- Publishes AnomalyDetected
- `core/src/core/application/use_cases/run_investigation.py` -- Publishes InsightCreated
- `core/src/core/application/use_cases/handle_message.py` -- Publishes MessageCreated

### Infrastructure (Phase 2a)
- `docker-compose.yml` -- Kafka container (KRaft mode), already running
- `core/src/core/infrastructure/web/app.py` -- FastAPI entrypoint pattern (lifespan context)
- `core/src/core/infrastructure/adapters/mongodb/connection.py` -- Connection module pattern to replicate for Kafka

### Project Context
- `.planning/PROJECT.md` -- Project vision, constraints
- `.planning/REQUIREMENTS.md` -- INFR-03 requirement
- `.planning/ROADMAP.md` -- Phase breakdown with success criteria
- `CLAUDE.md` Technology Stack -- confluent-kafka, Kafka config patterns

### Prior Phase Decisions
- `.planning/phases/01-core-domain-ports/01-CONTEXT.md` -- D-04 (entities collect events), D-05 (typed domain events), D-37 (EventPublisher is publish-only)
- `.planning/phases/02A-docker-compose-mongodb-adapters/02A-CONTEXT.md` -- D-01 (KRaft mode), D-14/D-15 (adapter code location pattern)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- EventPublisher ABC in `event_publisher.py` -- exact interface the Kafka producer must implement (publish, publish_many)
- FakeEventPublisher in Phase 1 tests -- reference implementation showing expected behavior
- Pydantic DomainEvent base with `model_dump(mode="json")` -- natural JSON serialization for Kafka
- MongoDB connection module pattern (`connection.py`) -- replicate for Kafka client/config

### Established Patterns
- All use cases call `event_publisher.publish_many(entity.collect_events())` after persistence
- Constructor injection for dependencies (adapters receive clients via __init__)
- `pydantic-settings` BaseSettings for configuration (CoreSettings pattern in app.py)
- Testcontainers for integration tests (session-scoped container, function-scoped cleanup)

### Integration Points
- Kafka container in docker-compose.yml (port 9092, KRaft mode) -- already available
- Kafka UI (Redpanda Console) in docker-compose.yml -- use for debugging events
- Core Dockerfile -- same image, different CMD for API vs consumer entry points
- pyproject.toml -- needs confluent-kafka (or aiokafka) dependency added

</code_context>

<specifics>
## Specific Ideas

- The consumer entrypoint model means the core Docker image stays the same but is instantiated twice in docker-compose.yml with different commands (one for uvicorn, one for the consumer loop). This is a common microservice pattern that avoids building separate images.
- Thread-based partition key for MessageCreated/InsightCreated ensures conversation-scoped events are always processed in order by the same consumer partition, which matters for investigation workflows triggered by user messages.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 02B-kafka-adapters*
*Context gathered: 2026-04-02*
