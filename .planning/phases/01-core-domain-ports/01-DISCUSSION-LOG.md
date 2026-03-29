# Phase 1: Core Domain & Ports - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 01-core-domain-ports
**Areas discussed:** Domain modeling style, Port granularity, Value objects & types, Error handling strategy, Module boundaries, Use case design, Investigation reasoning trace, Stream/StreamDataPoint relationship, Debouncing as domain concept, Metric/MetricDataPoint design, Anomaly detection domain model, Project entity scope, Message/Thread design, Domain event catalog, Use case catalog, IngestStreamData latency design, Orchestrator internal design, Investigator port design, Orchestrate invocation logic

---

## Domain Modeling Style

### Entity Behavior
| Option | Description | Selected |
|--------|-------------|----------|
| Rich domain models | Entities own all validation, state transitions, business rules | |
| Anemic + use case logic | Entities are plain data holders, all logic in use cases | |
| Hybrid | Entities own validation + single-entity logic, use cases orchestrate | ✓ |

**User's choice:** Hybrid
**Notes:** Classic DDD with practical separation — entities aren't dumb but don't try to do everything

### Base Class
| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic BaseModel | Built-in validation, serialization, FastAPI alignment | ✓ |
| Plain Python classes | Full control, no framework coupling in domain | |

**User's choice:** Pydantic BaseModel

### Entity Identity
| Option | Description | Selected |
|--------|-------------|----------|
| UUID generated at creation | uuid4() at construction, no DB dependency | ✓ |
| DB-assigned IDs | MongoDB ObjectId on insert | |

**User's choice:** UUID generated at creation

### Domain Events
| Option | Description | Selected |
|--------|-------------|----------|
| Entities collect domain events | Events accumulated internally, flushed by use cases | ✓ |
| Use cases emit events directly | Keep entities simpler | |

**User's choice:** Entities collect domain events

### Event Types
| Option | Description | Selected |
|--------|-------------|----------|
| Typed domain events | Specific event classes per event | ✓ |
| Generic event envelope | Single Event class with type string + payload dict | |

**User's choice:** Typed domain events

### Timestamps
**User's choice:** created_at as UTC datetime on all entities; updated_at managed at DB level only
**Notes:** User explicitly stated this preference

### Channel Abstraction
| Option | Description | Selected |
|--------|-------------|----------|
| Channel-agnostic domain | Thread/Message in Core with no Slack-specific fields | ✓ |
| Channel-aware domain | Include channel_type field | |

**User's choice:** Channel-agnostic domain

### Investigation Entity
| Option | Description | Selected |
|--------|-------------|----------|
| Full entity | Own lifecycle with status, token tracking, reasoning trace | ✓ |
| Value object on Insight | Metadata embedded in Insight | |

**User's choice:** Full entity
**Notes:** Must include intermediate thinking steps (tool calls, reasoning) that the model followed

### Credential Entity
**User's choice:** Credential is NOT a Core entity — belongs entirely to Connector Service
**Notes:** Credential store port also excluded from Core. Core and Connector Service are fully isolated modules.

### Insight Structure
| Option | Description | Selected |
|--------|-------------|----------|
| Structured with typed fields | All fields explicit | |
| Semi-structured with metadata dict | Core fields typed, extras in metadata dict | ✓ |

**User's choice:** Semi-structured with metadata dict

### Project Entity
**User's choice:** Project is NOT a domain entity — virtual tenancy concept via project_id UUID
**Notes:** No Project class, no Project repository

---

## Port Granularity

### Repository Organization
| Option | Description | Selected |
|--------|-------------|----------|
| One port per aggregate | All CRUD + query for its aggregate | ✓ |
| Granular per-operation (CQRS) | Separate read/write ports | |

**User's choice:** One port per aggregate

### Async vs Sync
| Option | Description | Selected |
|--------|-------------|----------|
| Async throughout | All port methods async def | ✓ |
| Sync ports, async adapters | Domain sync, adapters wrap | |

**User's choice:** Async throughout

### Non-Repository Ports
| Option | Description | Selected |
|--------|-------------|----------|
| EventPublisher | Abstract interface for publishing domain events | ✓ |
| Investigator | Abstract interface for running investigations | ✓ |
| Scheduler | Abstract interface for recurring tasks | Initially selected, later removed |
| MetricsCalculator | Secondary port for computing metrics from streams | ✓ |
| MetricMonitor | Secondary port for anomaly detection | ✓ |
| Agent | Secondary port for ADK agent brain | ✓ |
| MessageDeliverer | Secondary port for delivering responses via HTTP webhook | ✓ |

**Notes:** EventSubscriber is a primary adapter concern, not a secondary port. Scheduler removed (scheduled investigators deferred to v2). Investigator must be named "Investigator" per architecture diagram (not "InvestigationRunner").

### EventPublisher Split
**User's choice:** EventPublisher only (no EventSubscriber) — subscription is a primary adapter concern

### In-Memory Fakes
| Option | Description | Selected |
|--------|-------------|----------|
| In-memory fakes in Phase 1 | Ship alongside ports for testing | ✓ |
| Defer to Phase 2 | Only interfaces in Phase 1 | |

**User's choice:** In-memory fakes in Phase 1

### Primary Port Interfaces
| Option | Description | Selected |
|--------|-------------|----------|
| Define in Phase 1 | Abstract interfaces for entry points | ✓ |
| Skip — use cases ARE primary interface | Adapters call use cases directly | |

**User's choice:** Define in Phase 1
**Notes:** Later clarified: use cases ARE the primary ports (equivalent concept)

### Internal Event Ports
| Option | Description | Selected |
|--------|-------------|----------|
| Keep as abstract ports | Even for Core-internal events | ✓ |
| Core-specific event bus | Simpler in-process pattern | |

**User's choice:** Keep as abstract ports

---

## Value Objects & Types

### ID Types
| Option | Description | Selected |
|--------|-------------|----------|
| NewType wrappers | Lightweight type aliases | |
| Value object classes | Full Pydantic value objects | |
| Plain UUID / str | No wrappers | ✓ |

**User's choice:** Plain UUID / str

### Value Objects
| Option | Description | Selected |
|--------|-------------|----------|
| TimeWindow | Encapsulate window logic | |
| Severity | Enum for severity levels | |
| MetricType | Enum for metric types | |
| Minimal — you decide | Claude's discretion | ✓ |

**User's choice:** Claude's discretion

### Enum Style
| Option | Description | Selected |
|--------|-------------|----------|
| String enums (str, Enum) | JSON/MongoDB compatible | ✓ |
| Plain Enum | Standard without str mixin | |

**User's choice:** String enums

---

## Error Handling

### Error Communication
| Option | Description | Selected |
|--------|-------------|----------|
| Custom exception hierarchy | Domain exceptions with DomainError base | ✓ |
| Result type pattern | Result[T, Error] returns | |

**User's choice:** Custom exception hierarchy

### Error Context
| Option | Description | Selected |
|--------|-------------|----------|
| Typed fields per exception | Structured context attributes | ✓ |
| Simple message strings | Human-readable only | |

**User's choice:** Typed fields per exception

### Error Codes
| Option | Description | Selected |
|--------|-------------|----------|
| Exception class names only | Type IS the code | ✓ |
| Enum error codes | Separate ErrorCode enum | |

**User's choice:** Exception class names only

---

## Module Boundaries

### Inter-Service Communication
**User's choice:** HTTP only between services. Kafka events are internal to Core.
**Notes:** This was a major architectural clarification — Kafka is NOT a cross-service bus.

### Shared Contracts
| Option | Description | Selected |
|--------|-------------|----------|
| Core defines HTTP API contracts | Other services import DTOs | |
| Independent per service | Each defines own models | ✓ |
| Shared contracts package | Separate shared/ package | |

**User's choice:** Independent per service

---

## Use Case Design

### Organization
| Option | Description | Selected |
|--------|-------------|----------|
| One class per use case | Single execute() method | ✓ |
| Grouped by domain area | Service classes | |

**User's choice:** One class per use case
**Notes:** Use case is equivalent to primary port

### Input/Output
| Option | Description | Selected |
|--------|-------------|----------|
| Input DTOs, return entities | Typed input objects | |
| Domain entities in and out | Direct entity usage | |
| Full DTO boundary | Both input and output DTOs | |

**User's choice:** Primitive inputs, return domain entities
**Notes:** Instead of input DTOs, use primitive inputs directly

### Dependency Injection
| Option | Description | Selected |
|--------|-------------|----------|
| Constructor injection | Ports via __init__ | ✓ |
| DI container | dependency-injector library | |

**User's choice:** Constructor injection

---

## Investigation Reasoning Trace

### Step Structure
| Option | Description | Selected |
|--------|-------------|----------|
| Ordered list of typed step objects | StepType enum (tool_call, reasoning, observation) | ✓ |
| Raw log (list of dicts) | Flexible dict storage | |

**User's choice:** Typed InvestigationStep objects

### Data Source Tracking
| Option | Description | Selected |
|--------|-------------|----------|
| Via referenced entity IDs | Separate tracking lists | |
| Implicit in steps | Trace steps contain the info | ✓ |

**User's choice:** Implicit in steps

### Trigger Model
| Option | Description | Selected |
|--------|-------------|----------|
| Single trigger | One trigger per Investigation | ✓ |
| Multi-trigger | Multiple related triggers | |

**User's choice:** Single trigger

### Investigation-Insight Cardinality
| Option | Description | Selected |
|--------|-------------|----------|
| 1:1 | One Investigation, one Insight | ✓ |
| 1:N | One Investigation, multiple Insights | |

**User's choice:** 1:1

---

## Stream/StreamDataPoint Relationship

### Embedding
| Option | Description | Selected |
|--------|-------------|----------|
| Stream embeds data points | List of embedded objects | ✓ |
| Separate entities linked by stream_id | Independent entities | |

**User's choice:** Stream embeds data points
**Notes:** Stream has no id and no created_at

### Stream Identity
| Option | Description | Selected |
|--------|-------------|----------|
| Composite key (source, stream_type, project_id) | No UUID | ✓ |
| UUID id | Standard identity | |

**User's choice:** Composite key

### Data Flexibility
| Option | Description | Selected |
|--------|-------------|----------|
| Flexible dict | data: dict[str, Any] | ✓ |
| Typed per stream_type | Separate models per type | |

**User's choice:** Flexible dict

---

## Metric/MetricDataPoint Design

### Embedding
**User's choice:** Metric embeds data points (consistent with Stream)

### Metric Identity
**User's choice:** Composite key (metric_type, project_id) — consistent with Stream

### MetricDataPoint Fields
**User's choice:** Minimal — just value + timestamp, no TimeWindow

### MetricsCalculator/MetricMonitor Role
**User's choice:** Secondary ports called by use cases (not event-driven adapters)

### Aggregation Strategy
**User's choice:** Deferred to Phase 3 — depends on anomaly detection algorithm

---

## Anomaly Detection Domain Model

### Anomaly Representation
| Option | Description | Selected |
|--------|-------------|----------|
| Domain event only | AnomalyDetected event, not persisted | ✓ |
| Persisted entity | Full entity in its own collection | |

**User's choice:** Domain event only
**Notes:** MetricMonitor emits via EventPublisher directly, does not return to use case

### MetricMonitor Dependencies
**User's choice:** EventPublisher injected at adapter construction, port interface is clean: check(metric) -> None

---

## Message/Thread Design

### Thread Structure
**User's choice:** Thread embeds Messages, identified by UUID

### Thread-Investigation Link
**User's choice:** No direct link — implicit through message content

---

## Domain Event Catalog

**User's choice:** 6 events: StreamDataPointCreated, StreamUpdated, MetricUpdated, AnomalyDetected, InsightCreated, MessageCreated
**Notes:** StreamDataPointCreated was a new event identified during discussion — IngestStreamData emits this instead of StreamUpdated for latency concerns. Also added: MessageCreated triggers Orchestrate use case.

---

## Use Case Catalog

**User's choice:** 7 use cases: IngestStreamData, ProcessStreamDataPoint, ProcessStreamUpdate, MonitorMetric, RunInvestigation, HandleMessage, Orchestrate
**Notes:** Scheduled investigators and query use cases deferred to v2. Orchestrate is a use case, not a separate Orchestrator port.

---

## IngestStreamData Latency Design

### Validation
| Option | Description | Selected |
|--------|-------------|----------|
| Validate then emit | Pydantic validates in memory, then emit event | ✓ |
| Emit raw, validate downstream | Pass raw data straight to event | |

**User's choice:** Validate then emit — no repository dependency, just EventPublisher

---

## Orchestrator Internal Design

**User's choice:** Orchestrate is the use case; ADK Agent is a separate secondary port called by it
**Notes:** Agent.process() returns response text to Orchestrate. Orchestrate stores in Thread and delivers via MessageDeliverer. Agent has RunInvestigation as its only tool (wiring deferred to Phase 4).

### Investigation Flow
**User's choice:** Async — agent doesn't wait for investigation. Investigation produces Insight, InsightCreated triggers Orchestrate again with role=system.

### Agent Port Interface
**User's choice:** process(thread: Thread, invocations: list[Invocation]) -> str

---

## Investigator Port Design

### Responsibility Split
| Option | Description | Selected |
|--------|-------------|----------|
| Investigator creates Insight internally | Full cycle in adapter | |
| Use case orchestrates, Investigator just runs | Returns findings, use case creates Insight | ✓ |

**User's choice:** Use case orchestrates
**Notes:** Investigator returns InvestigatorResult (steps, findings, tokens_used)

---

## Orchestrate Invocation Logic

### Debouncing Strategy
**User's choice:** Invocation entity + drain loop pattern
**Notes:** New Invocation entity records every pending orchestration request. RunInvestigation and HandleMessage create invocations. Orchestrate reads all pending, passes to Agent, loops until drained.

### Concurrency
**User's choice:** Kafka consumer group sequential guarantees (partition by thread_id) — no application-level locks

### Response Delivery
**User's choice:** Only final response delivered (after drain loop completes). Intermediate responses stored in Thread for agent context only.

### Agent Input Per Iteration
**User's choice:** Full Thread (including prior responses from this loop) + only new pending invocations

---

## Claude's Discretion

- Which domain concepts warrant dedicated value objects beyond enums
- Specific method signatures on repository ports
- Internal structure details of InvestigatorResult and InvestigationStep

## Deferred Ideas

- Scheduled/deterministic investigators (INTL-01) — deferred to v2
- Query use cases — deferred to v2
- Aggregation strategy — deferred to Phase 3
- Agent tool wiring — deferred to Phase 4
- Credential entity/store — belongs to Connector Service
- CRED-01/02/04 requirement remapping needed (currently mapped to Core Phase 2)
