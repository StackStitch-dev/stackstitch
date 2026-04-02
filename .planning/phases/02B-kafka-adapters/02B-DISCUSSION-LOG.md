# Phase 2b: Kafka Adapters - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 02B-kafka-adapters
**Areas discussed:** Topic mapping strategy, Serialization format, Consumer routing design, Error handling & delivery, Consumer group & concurrency, Adapter code location, Consumer lifecycle

---

## Topic Mapping Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| One topic per event type | e.g., stream.updated, metric.updated -- 7 topics, clean separation | |
| One topic per aggregate | e.g., streams, metrics -- fewer topics, filter by type within topic | |
| Single domain.events topic | All events on one topic, partitioned by project_id | Partial |

**User's choice:** Single domain.events topic but with thread_id as partition key for MessageCreated and InsightCreated events (conversation ordering).
**Notes:** Default partition key is project_id. Thread/message events are the exception using thread_id.

---

## Partition Key Derivation

| Option | Description | Selected |
|--------|-------------|----------|
| Adapter derives it | Producer inspects event type and picks key. Domain stays clean. | Yes |
| Event carries partition_hint | Optional field on DomainEvent base. More explicit but touches domain. | |

**User's choice:** Adapter derives it -- keeps domain layer pure.

---

## Serialization Format

| Option | Description | Selected |
|--------|-------------|----------|
| JSON with event_type header | Pydantic model_dump, event type in Kafka header | Yes |
| JSON with Schema Registry | JSON Schema validated by Confluent Schema Registry | |
| Avro with Schema Registry | Binary Avro, most compact, best evolution | |

**User's choice:** JSON with event_type header. Schema Registry deferred to v2+.

---

## Consumer Routing Design

| Option | Description | Selected |
|--------|-------------|----------|
| Registry dict mapping | dict[str, Callable] maps event_type to handler. Explicit. | Yes |
| Decorator-based registration | @handles decorators auto-register. Cleaner but more framework-like. | |

**User's choice:** Registry dict mapping -- explicit and easy to test.

---

## Error Handling & Delivery

| Option | Description | Selected |
|--------|-------------|----------|
| At-least-once + DLQ | Commit after success, DLQ after N retries | Yes |
| At-least-once + fail-fast | Commit after success, log and skip on failure | |
| At-least-once + retry with backoff | Retry N times then skip or DLQ | |

**User's choice:** At-least-once + DLQ with 5 retries and exponential backoff (1s, 2s, 4s, 8s, 16s).

---

## Consumer Group & Concurrency

| Option | Description | Selected |
|--------|-------------|----------|
| Single consumer, single partition | Simplest, ordered processing | |
| Single consumer, multiple partitions | Allows future scaling, configurable count | Yes |

**User's choice:** Single consumer, multiple partitions with configurable partition count (default 3 via pydantic-settings).

---

## Adapter Code Location

| Option | Description | Selected |
|--------|-------------|----------|
| core/infrastructure/adapters/kafka/ | Alongside MongoDB, consistent pattern | Yes |
| Separate kafka-worker/ package | Consumer as separate service package | |

**User's choice:** core/infrastructure/adapters/kafka/ -- consistent with Phase 2a.

---

## Consumer Lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Background asyncio task in FastAPI lifespan | Same process, simplest deployment | |
| Separate worker process | Own entrypoint, own container, independent scaling | Yes |

**User's choice:** Separate worker process. Core module defines multiple entry points (API, consumer) that become deployable artifacts in their own Docker containers. Same image, different CMD.

---

## Claude's Discretion

- confluent-kafka vs aiokafka library choice
- Consumer poll loop implementation details
- Topic creation strategy
- Test fixture design
- Entry point module structure

## Deferred Ideas

None -- all discussion stayed within phase scope.
