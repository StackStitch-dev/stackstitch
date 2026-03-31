# Phase 1: Core Domain & Ports - Research

**Researched:** 2026-03-31
**Domain:** Python DDD + Hexagonal Architecture -- pure domain modeling with Pydantic v2
**Confidence:** HIGH

## Summary

Phase 1 is a pure domain modeling phase with zero infrastructure dependencies. The entire deliverable is Python code: domain entities (Pydantic v2 BaseModel), port interfaces (ABC with async methods), use case classes, domain events, domain exceptions, and in-memory fakes for testing. The CONTEXT.md provides extremely detailed decisions (D-01 through D-70) covering every modeling choice, leaving minimal ambiguity.

The core technical challenge is structuring Pydantic v2 models correctly for a hexagonal architecture -- entities need `validate_assignment=True` for mutability with validation, value objects need `frozen=True`, and ports need `abc.ABC` with `async def` abstract methods. All 7 use cases follow the same pattern: constructor injection of ports, single `execute()` method, emit domain events via `EventPublisher`.

**Primary recommendation:** Use Pydantic v2 BaseModel for all entities/value objects with appropriate `model_config`, Python `abc.ABC` for port definitions (not Protocol -- explicit contracts are better for a DDD codebase where implementors MUST inherit), and pytest with pytest-asyncio for testing all async use cases against in-memory fakes.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Hybrid domain models -- entities own validation and single-entity business logic; use cases handle cross-entity orchestration
- **D-02:** Pydantic BaseModel as base class for all entities -- built-in validation, serialization, aligns with FastAPI stack
- **D-03:** UUID identity generated at entity creation (`uuid4()`), not DB-assigned -- entities have identity before persistence
- **D-04:** Entities collect domain events internally; use cases flush events after persistence via EventPublisher
- **D-05:** Typed domain events -- specific event classes (StreamUpdated, MetricUpdated, etc.) in the domain layer; Kafka topic mapping is an adapter concern
- **D-06:** `created_at` as UTC datetime on all entities; `updated_at` managed at DB level only (not in domain)
- **D-07:** Channel-agnostic Thread/Message -- no Slack-specific fields in Core
- **D-08:** Investigation is a full entity with ordered list of typed InvestigationStep objects with token tracking
- **D-09:** Consulted data sources are implicit in InvestigationStep trace
- **D-10:** Single trigger per Investigation (anomaly | adhoc) with trigger_ref UUID and optional query string
- **D-11:** 1:1 relationship: one Investigation produces one Insight (or none on failure)
- **D-12:** Insight is semi-structured with typed core fields + flexible `metadata: dict[str, Any]`
- **D-13:** Credential entity and credential store port belong entirely to Connector Service, NOT Core
- **D-14:** Project is NOT a domain entity -- just a `project_id: UUID` field on other entities
- **D-15:** All entities reference project_id as a loose UUID field
- **D-16:** Stream embeds StreamDataPoints (list of embedded value objects)
- **D-17:** Stream has no id and no created_at -- identified by composite key `(source, stream_type, project_id)`
- **D-18:** StreamDataPoint.data is `dict[str, Any]` -- flexible payload
- **D-19:** Metric embeds MetricDataPoints (consistent with Stream pattern)
- **D-20:** Metric has no id -- identified by composite key `(metric_type, project_id)`
- **D-21:** MetricDataPoint is minimal: just `value: float` + `timestamp: datetime`
- **D-22:** Aggregation strategy deferred to Phase 3
- **D-23:** MetricsCalculator is a secondary port (called by use cases)
- **D-24:** MetricMonitor is a secondary port, uses EventPublisher directly to emit AnomalyDetected events
- **D-25:** Anomaly is a domain event only (AnomalyDetected), NOT a persisted entity
- **D-26:** Thread embeds Messages (consistent pattern), identified by UUID
- **D-27:** No direct link between Thread and Investigation
- **D-28:** Invocation is a new domain entity -- records every pending orchestration request
- **D-29:** Invocations created by use cases that emit triggering events
- **D-30:** Orchestrate use case implements a drain loop
- **D-31:** Agent receives full Thread + pending invocations each iteration
- **D-32:** Only final response delivered via MessageDeliverer
- **D-33:** Concurrency handled by Kafka consumer group sequential guarantees
- **D-34:** Agent has a single tool: RunInvestigation (deferred to Phase 4)
- **D-35:** One repository port per aggregate, async throughout
- **D-36:** Secondary ports: Repository ports per aggregate + EventPublisher + Investigator + MetricsCalculator + MetricMonitor + Agent + MessageDeliverer
- **D-37:** EventPublisher only (no EventSubscriber port)
- **D-38:** Use cases ARE the primary ports
- **D-39:** In-memory fakes for ALL ports shipped in Phase 1
- **D-40:** Orchestrator port renamed: it is the Orchestrate use case, Agent is the secondary port
- **D-41:** Scheduler port removed
- **D-42:** Plain UUIDs for all entity identifiers
- **D-43:** String enums `(str, Enum)` for all domain enums
- **D-44:** Value objects beyond enums at Claude's discretion
- **D-45:** Custom exception hierarchy with `DomainError` base class
- **D-46:** Each exception carries typed context fields
- **D-47:** Exception class names serve as error codes
- **D-48:** Inter-service communication is HTTP only. Kafka events are internal to Core.
- **D-49:** Each service defines its own request/response models independently
- **D-50:** Debouncing is purely an infrastructure/adapter concern
- **D-51:** One class per use case with `execute()` method
- **D-52:** Use cases accept primitive inputs directly (no input DTOs), return domain entities
- **D-53:** Constructor injection for dependencies
- **D-54-D-59:** Six domain events (StreamDataPointCreated, StreamUpdated, MetricUpdated, AnomalyDetected, InsightCreated, MessageCreated)
- **D-60-D-66:** Seven use cases (IngestStreamData, ProcessStreamDataPoint, ProcessStreamUpdate, MonitorMetric, RunInvestigation, HandleMessage, Orchestrate)
- **D-67:** Investigator receives Investigation entity + context dict, returns InvestigatorResult
- **D-68:** Agent.process(thread: Thread, invocations: list[Invocation]) -> str

### Claude's Discretion
- Which domain concepts warrant dedicated value objects beyond enums and plain types
- Specific method signatures on repository ports (beyond save/get_by_id)
- Internal structure of InvestigatorResult and InvestigationStep fields

### Deferred Ideas (OUT OF SCOPE)
- Scheduled/deterministic investigators -- deferred to v2 (removes Scheduler port from Phase 1)
- Query use cases (read-only endpoints) -- deferred to v2
- Time window aggregation strategy for metrics -- deferred to Phase 3
- Agent tool wiring (ADK-specific) -- deferred to Phase 4
- Credential entity and store -- belongs to Connector Service domain, not Core
- CRED-01, CRED-02, CRED-04 remapping needed (Connector Service, not Core)

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFR-05 | Project scaffold follows DDD + Hexagonal Architecture for the Core service | Directory structure pattern, Pydantic entity modeling, ABC port definitions, use case patterns -- all covered in Architecture Patterns and Code Examples sections |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | Runtime | Stable with performance improvements. 3.13 available on this machine but 3.12 is the minimum target per CLAUDE.md. |
| Pydantic | 2.12.5 | Domain entities & validation | Current stable. Provides BaseModel for all entities, field validators for business rules, model_config for entity behavior. |
| pydantic-settings | 2.13.1 | Configuration (later phases) | Not needed in Phase 1 but mentioned for completeness. |

### Supporting (Dev Dependencies)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 | Test framework | All domain tests |
| pytest-asyncio | 1.3.0 | Async test support | Testing async use cases and port interactions |
| pytest-cov | 6.0+ | Coverage reporting | CI gate and OSS credibility |
| ruff | 0.15.8 | Linter + formatter | All code quality checks |
| mypy | 1.20.0 | Static type checking | Strict mode for DDD type correctness |
| pre-commit | 4.0+ | Git hooks | Run ruff, mypy before commits |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| abc.ABC for ports | typing.Protocol | Protocol uses structural subtyping (duck typing). ABC enforces explicit inheritance which is better for a DDD codebase where port implementations MUST declare intent. ABC also allows `@abstractmethod` enforcement at instantiation time. |
| Pydantic BaseModel for entities | dataclasses | Pydantic provides built-in validation, serialization, and aligns with FastAPI stack (D-02 locks this choice). |
| Plain classes for value objects | attrs | Pydantic frozen models serve the same purpose with consistent API across all domain types. |

**Installation:**
```bash
uv init core/
cd core/
uv add pydantic
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy pre-commit
```

## Architecture Patterns

### Recommended Project Structure
```
core/
├── pyproject.toml
├── src/
│   └── core/
│       ├── __init__.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── entities/
│       │   │   ├── __init__.py
│       │   │   ├── stream.py          # Stream, StreamDataPoint
│       │   │   ├── metric.py          # Metric, MetricDataPoint
│       │   │   ├── insight.py         # Insight
│       │   │   ├── investigation.py   # Investigation, InvestigationStep, InvestigatorResult
│       │   │   ├── thread.py          # Thread, Message
│       │   │   └── invocation.py      # Invocation
│       │   ├── events/
│       │   │   ├── __init__.py
│       │   │   └── domain_events.py   # All 6 domain events
│       │   ├── enums.py               # All string enums
│       │   └── exceptions.py          # DomainError hierarchy
│       └── application/
│           ├── __init__.py
│           ├── ports/
│           │   ├── __init__.py
│           │   ├── repositories.py    # All repository ports
│           │   ├── event_publisher.py # EventPublisher port
│           │   ├── investigator.py    # Investigator port
│           │   ├── metrics_calculator.py  # MetricsCalculator port
│           │   ├── metric_monitor.py  # MetricMonitor port
│           │   ├── agent.py           # Agent port
│           │   └── message_deliverer.py   # MessageDeliverer port
│           └── use_cases/
│               ├── __init__.py
│               ├── ingest_stream_data.py
│               ├── process_stream_data_point.py
│               ├── process_stream_update.py
│               ├── monitor_metric.py
│               ├── run_investigation.py
│               ├── handle_message.py
│               └── orchestrate.py
└── tests/
    ├── __init__.py
    ├── conftest.py                    # Shared fixtures, in-memory fakes
    ├── fakes/
    │   ├── __init__.py
    │   ├── repositories.py           # In-memory repo fakes
    │   ├── event_publisher.py        # In-memory event publisher
    │   ├── investigator.py           # Fake investigator
    │   ├── metrics_calculator.py     # Fake metrics calculator
    │   ├── metric_monitor.py         # Fake metric monitor
    │   ├── agent.py                  # Fake agent
    │   └── message_deliverer.py      # Fake message deliverer
    ├── domain/
    │   ├── test_entities.py          # Entity instantiation, validation
    │   ├── test_events.py            # Domain event creation
    │   └── test_exceptions.py        # Exception hierarchy
    └── use_cases/
        ├── test_ingest_stream_data.py
        ├── test_process_stream_data_point.py
        ├── test_process_stream_update.py
        ├── test_monitor_metric.py
        ├── test_run_investigation.py
        ├── test_handle_message.py
        └── test_orchestrate.py
```

### Pattern 1: Pydantic Entity with Domain Events
**What:** Entities as Pydantic BaseModel with internal event collection using PrivateAttr
**When to use:** All domain entities that emit events (Investigation, Thread, Invocation)

```python
# Source: Pydantic v2 docs + DDD pattern
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from core.domain.events.domain_events import DomainEvent


class Entity(BaseModel):
    """Base for entities that have UUID identity and collect domain events."""
    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def collect_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def flush_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events
```

### Pattern 2: Composite-Key Entity (Stream/Metric)
**What:** Entities identified by composite key instead of UUID
**When to use:** Stream `(source, stream_type, project_id)` and Metric `(metric_type, project_id)`

```python
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.domain.entities.stream import StreamDataPoint
from core.domain.enums import StreamType


class Stream(BaseModel):
    """Identified by composite key (source, stream_type, project_id). No UUID, no created_at."""
    model_config = ConfigDict(validate_assignment=True)

    source: str
    stream_type: StreamType
    project_id: UUID
    data_points: list[StreamDataPoint] = Field(default_factory=list)

    def add_data_point(self, data_point: StreamDataPoint) -> None:
        self.data_points.append(data_point)
```

### Pattern 3: Value Object (Frozen Pydantic Model)
**What:** Immutable value objects using frozen=True
**When to use:** StreamDataPoint, MetricDataPoint, InvestigationStep, domain events

```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class StreamDataPoint(BaseModel):
    """Immutable value object embedded in Stream."""
    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    data: dict[str, Any]
```

### Pattern 4: ABC Port with Async Methods
**What:** Abstract base classes defining async port contracts
**When to use:** All secondary ports (repositories, EventPublisher, Investigator, etc.)

```python
import abc
from uuid import UUID

from core.domain.entities.investigation import Investigation


class InvestigationRepository(abc.ABC):
    """Port for Investigation persistence."""

    @abc.abstractmethod
    async def save(self, investigation: Investigation) -> None: ...

    @abc.abstractmethod
    async def get_by_id(self, investigation_id: UUID) -> Investigation | None: ...
```

### Pattern 5: Use Case with Constructor Injection
**What:** Single-responsibility use case with execute() method
**When to use:** All 7 use cases

```python
from core.application.ports.event_publisher import EventPublisher
from core.domain.events.domain_events import StreamDataPointCreated


class IngestStreamData:
    """Receives raw data, validates via Pydantic, emits StreamDataPointCreated.
    No DB write -- just validation and event emission for latency."""

    def __init__(self, event_publisher: EventPublisher) -> None:
        self._event_publisher = event_publisher

    async def execute(
        self,
        source: str,
        stream_type: str,
        project_id: UUID,
        timestamp: datetime,
        data: dict[str, Any],
    ) -> StreamDataPoint:
        # Pydantic validation happens at construction
        data_point = StreamDataPoint(timestamp=timestamp, data=data)
        event = StreamDataPointCreated(
            source=source,
            stream_type=stream_type,
            project_id=project_id,
            data_point=data_point,
        )
        await self._event_publisher.publish(event)
        return data_point
```

### Pattern 6: Domain Event as Frozen Pydantic Model
**What:** Typed, immutable domain events carrying contextual data
**When to use:** All 6 domain events

```python
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class DomainEvent(BaseModel):
    """Base domain event -- immutable, timestamped, uniquely identified."""
    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StreamDataPointCreated(DomainEvent):
    source: str
    stream_type: str
    project_id: UUID
    data_point: "StreamDataPoint"
```

### Pattern 7: String Enum
**What:** Python string enums that serialize naturally to JSON/MongoDB
**When to use:** All domain enums (D-43)

```python
from enum import Enum


class InvestigationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class InvestigationTrigger(str, Enum):
    ANOMALY = "anomaly"
    ADHOC = "adhoc"


class InvocationSource(str, Enum):
    USER_MESSAGE = "user_message"
    INSIGHT = "insight"


class InvocationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
```

### Pattern 8: Domain Exception Hierarchy
**What:** Custom exceptions with typed context fields (D-45, D-46, D-47)
**When to use:** All domain-level errors

```python
from typing import Any
from uuid import UUID


class DomainError(Exception):
    """Base for all domain errors. Class name serves as error code."""

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context = context


class EntityNotFoundError(DomainError):
    def __init__(self, entity_type: str, entity_id: UUID) -> None:
        super().__init__(
            f"{entity_type} with id {entity_id} not found",
            entity_type=entity_type,
            entity_id=entity_id,
        )


class InvalidEntityStateError(DomainError):
    def __init__(self, entity_type: str, entity_id: UUID, reason: str) -> None:
        super().__init__(
            f"{entity_type} {entity_id} is in invalid state: {reason}",
            entity_type=entity_type,
            entity_id=entity_id,
            reason=reason,
        )
```

### Pattern 9: In-Memory Fake for Testing
**What:** Concrete in-memory implementations of port ABCs
**When to use:** All ports get a fake in Phase 1 (D-39)

```python
from uuid import UUID

from core.application.ports.repositories import InvestigationRepository
from core.domain.entities.investigation import Investigation


class InMemoryInvestigationRepository(InvestigationRepository):
    def __init__(self) -> None:
        self._store: dict[UUID, Investigation] = {}

    async def save(self, investigation: Investigation) -> None:
        self._store[investigation.id] = investigation

    async def get_by_id(self, investigation_id: UUID) -> Investigation | None:
        return self._store.get(investigation_id)
```

### Anti-Patterns to Avoid
- **Leaking infrastructure into domain:** No imports from Motor, Kafka, Slack, or any adapter library in `core/domain/` or `core/application/`. The only external dependency is Pydantic.
- **Using Protocol instead of ABC for ports:** Protocol is for structural typing (duck typing). In a DDD codebase, port implementors must explicitly declare they implement the contract. Use `abc.ABC` + `@abstractmethod`.
- **Adding `updated_at` to domain entities:** Per D-06, `updated_at` is managed at DB level only. Do not add it to Pydantic models.
- **Creating DTOs/input objects for use cases:** Per D-52, use cases accept primitives directly. No `IngestStreamDataInput` classes.
- **Putting event subscription in Core:** Per D-37, only `EventPublisher` exists as a port. Event subscription (Kafka consumers) is a primary adapter concern wired in infrastructure.
- **Making IngestStreamData depend on a repository:** Per D-60, IngestStreamData has zero DB interaction. It only needs EventPublisher.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Data validation | Custom validation logic | Pydantic field_validator + model_validator | Pydantic handles type coercion, nested validation, custom rules with decorators |
| JSON serialization | Custom `to_dict()` methods | Pydantic `.model_dump()` / `.model_dump_json()` | Built-in, handles nested models, custom serializers, exclude fields |
| UUID generation | Custom ID generators | `uuid4()` via `Field(default_factory=uuid4)` | Standard, guaranteed uniqueness |
| Enum serialization | String constants / custom serialization | `(str, Enum)` pattern | Natural JSON serialization, type safety, exhaustive matching |
| Async test fixtures | Manual setup/teardown | pytest-asyncio fixtures with `@pytest.fixture` | Handles event loop lifecycle, async context managers |

**Key insight:** Phase 1 has almost zero "don't hand-roll" risk because there are no infrastructure concerns. The main risk is over-engineering domain models with unnecessary abstractions.

## Common Pitfalls

### Pitfall 1: Mutable Default Lists in Pydantic
**What goes wrong:** Using `list` as default instead of `Field(default_factory=list)` causes shared state between instances.
**Why it happens:** Pydantic v2 handles this better than v1 but `Field(default_factory=list)` is still the explicit, safe pattern.
**How to avoid:** Always use `Field(default_factory=list)` for mutable container defaults.
**Warning signs:** Tests passing in isolation but failing when run together.

### Pitfall 2: Forgetting async in Port Method Definitions
**What goes wrong:** Defining port methods as sync when they should be async (D-35 requires async throughout).
**Why it happens:** Easy to forget `async def` on ABC methods since there is no infrastructure in Phase 1.
**How to avoid:** All port abstract methods must be `async def`. In-memory fakes must also use `async def` even though they don't need it.
**Warning signs:** mypy errors when concrete adapters try to implement sync methods for async ports.

### Pitfall 3: Circular Imports in Domain Layer
**What goes wrong:** Entities importing events that import entities creates circular dependencies.
**Why it happens:** Domain events reference entity types (e.g., `StreamDataPointCreated` contains `StreamDataPoint`).
**How to avoid:** Use `from __future__ import annotations` (PEP 563) at top of every module. Use string forward references in type hints where needed. Keep events in their own module that imports from entities (one-way dependency).
**Warning signs:** `ImportError` at module load time.

### Pitfall 4: Over-Testing Pydantic Validation
**What goes wrong:** Writing tests that just verify Pydantic validates types correctly (testing the library, not the domain).
**Why it happens:** Desire for high coverage.
**How to avoid:** Test domain behavior and business rules, not basic type validation. Test field_validators and model_validators that encode business logic. Test entity methods like `collect_event()`, `flush_events()`, `add_data_point()`.
**Warning signs:** Tests that only call constructors with valid data and assert attributes match.

### Pitfall 5: PrivateAttr and model_dump() Interaction
**What goes wrong:** Expecting `_events` to appear in `model_dump()` output or be serialized.
**Why it happens:** `PrivateAttr` fields are excluded from Pydantic serialization by design.
**How to avoid:** This is actually the desired behavior -- events should not be serialized to DB. But be aware: `model_copy()` also does NOT copy private attributes. If you copy an entity, events are lost.
**Warning signs:** Events disappearing after entity copy operations.

### Pitfall 6: pytest-asyncio Mode Configuration
**What goes wrong:** Async tests not being collected or running synchronously.
**Why it happens:** pytest-asyncio requires explicit mode configuration since v0.21+.
**How to avoid:** Set `asyncio_mode = "auto"` in `pyproject.toml` under `[tool.pytest.ini_options]` so all async test functions are automatically detected.
**Warning signs:** Tests that should be async running without `await`, or warnings about "coroutine was never awaited".

### Pitfall 7: Composite Key Entities and Equality
**What goes wrong:** Stream and Metric don't have UUID ids, so default Pydantic equality (by all fields) may cause issues.
**Why it happens:** D-17 and D-20 define composite keys instead of UUIDs.
**How to avoid:** Consider implementing `__eq__` and `__hash__` based on the composite key fields for Stream and Metric. Pydantic BaseModel does not provide identity-based equality by default.
**Warning signs:** Two Stream objects with same composite key but different data_points not being treated as "the same stream".

## Code Examples

### Entity Base with Event Collection
```python
# Source: Pydantic v2 docs (PrivateAttr) + DDD aggregate pattern
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class DomainEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Entity(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def collect_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def flush_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events
```

### Repository Port with Composite Key Lookup
```python
# Source: Hexagonal architecture + DDD repository pattern
from __future__ import annotations

import abc
from uuid import UUID

from core.domain.entities.stream import Stream
from core.domain.enums import StreamType


class StreamRepository(abc.ABC):
    @abc.abstractmethod
    async def save(self, stream: Stream) -> None: ...

    @abc.abstractmethod
    async def get_by_key(
        self, source: str, stream_type: StreamType, project_id: UUID
    ) -> Stream | None: ...
```

### Use Case Test with In-Memory Fake
```python
# Source: pytest-asyncio docs + DDD testing pattern
import pytest
from uuid import uuid4

from core.application.use_cases.ingest_stream_data import IngestStreamData
from tests.fakes.event_publisher import InMemoryEventPublisher


@pytest.fixture
def event_publisher() -> InMemoryEventPublisher:
    return InMemoryEventPublisher()


@pytest.fixture
def use_case(event_publisher: InMemoryEventPublisher) -> IngestStreamData:
    return IngestStreamData(event_publisher=event_publisher)


async def test_ingest_emits_stream_data_point_created(
    use_case: IngestStreamData,
    event_publisher: InMemoryEventPublisher,
) -> None:
    project_id = uuid4()
    await use_case.execute(
        source="github",
        stream_type="pull_request",
        project_id=project_id,
        timestamp=datetime.now(timezone.utc),
        data={"pr_number": 42, "action": "opened"},
    )
    assert len(event_publisher.events) == 1
    assert event_publisher.events[0].__class__.__name__ == "StreamDataPointCreated"
```

### EventPublisher Port and Fake
```python
# Port definition
import abc
from core.domain.events.domain_events import DomainEvent


class EventPublisher(abc.ABC):
    @abc.abstractmethod
    async def publish(self, event: DomainEvent) -> None: ...

    @abc.abstractmethod
    async def publish_many(self, events: list[DomainEvent]) -> None: ...


# In-memory fake
class InMemoryEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)

    async def publish_many(self, events: list[DomainEvent]) -> None:
        self.events.extend(events)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `orm_mode` | Pydantic v2 `from_attributes` | 2023 (v2.0) | Cleaner ORM mapping, not needed in Phase 1 |
| `@validator` decorator | `@field_validator` / `@model_validator` | 2023 (v2.0) | New decorator names, classmethod-based |
| pytest-asyncio implicit mode | Explicit `asyncio_mode = "auto"` | 2023 (v0.21) | Must configure in pyproject.toml |
| `typing.Optional[X]` | `X \| None` (PEP 604) | Python 3.10 | Cleaner union syntax |
| `from __future__ import annotations` needed | Native in Python 3.12+ with PEP 649 | Python 3.12+ | Still useful for consistency, but not strictly required |

## Open Questions

1. **InvestigatorResult and InvestigationStep internal fields**
   - What we know: D-08 says InvestigationStep has tool calls, reasoning, observations, token tracking. D-67 says InvestigatorResult has steps, findings narrative, tokens_used.
   - What's unclear: Exact field names and types for step_type, tool_name, observation content.
   - Recommendation: This is explicitly at Claude's discretion (per CONTEXT.md). Define reasonable fields: `step_type: str`, `tool_name: str | None`, `input_data: dict[str, Any]`, `output_data: dict[str, Any]`, `reasoning: str`, `tokens_used: int`. Keep them as frozen Pydantic value objects.

2. **Repository port method signatures beyond save/get_by_id**
   - What we know: Each aggregate needs a repository. Stream and Metric use composite keys.
   - What's unclear: What query methods do use cases actually need?
   - Recommendation: Start minimal. Add methods as use cases demand them: `save`, `get_by_id`/`get_by_key`, and a few that use cases obviously need (e.g., `InvocationRepository.get_pending_by_thread_id` for the Orchestrate drain loop, `ThreadRepository.get_by_id` for HandleMessage).

3. **Stream/Metric embedded data point growth**
   - What we know: Stream embeds StreamDataPoints (D-16), Metric embeds MetricDataPoints (D-19).
   - What's unclear: Unbounded list growth could be an issue in production.
   - Recommendation: This is an infrastructure concern for Phase 2. In Phase 1, model it as written. Add a note that adapters may paginate or limit embedded data points.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.13.3 | Target 3.12+ in pyproject.toml |
| uv | Package management | Yes | 0.10.3 | pip (slower) |
| Docker | Not needed Phase 1 | No | -- | Not needed |
| MongoDB | Not needed Phase 1 | -- | -- | Not needed |
| Kafka | Not needed Phase 1 | -- | -- | Not needed |

**Missing dependencies with no fallback:** None -- Phase 1 is pure Python, no external services.

**Missing dependencies with fallback:** Docker is not installed but is not needed until Phase 2.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `core/pyproject.toml` (Wave 0 -- needs creation) |
| Quick run command | `cd core && uv run pytest tests/ -x -q` |
| Full suite command | `cd core && uv run pytest tests/ --cov=src/core --cov-report=term-missing` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFR-05.1 | Domain entities instantiate with validation | unit | `uv run pytest tests/domain/test_entities.py -x` | Wave 0 |
| INFR-05.2 | Port interfaces defined as abstract contracts | unit | `uv run pytest tests/domain/test_entities.py -x` (import test) + mypy | Wave 0 |
| INFR-05.3 | Use cases execute business logic on ports | unit | `uv run pytest tests/use_cases/ -x` | Wave 0 |
| INFR-05.4 | All domain logic testable with in-memory fakes | unit | `uv run pytest tests/ -x` (full suite uses only fakes) | Wave 0 |
| INFR-05.5 | Directory structure follows hexagonal layout | smoke | `ls` verification in test or manual check | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd core && uv run pytest tests/ -x -q`
- **Per wave merge:** `cd core && uv run pytest tests/ --cov=src/core --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `core/pyproject.toml` -- project setup with dependencies and pytest config
- [ ] `core/src/core/__init__.py` -- package init
- [ ] `core/tests/conftest.py` -- shared fixtures with in-memory fakes
- [ ] `core/tests/fakes/` -- all in-memory fake implementations
- [ ] pytest-asyncio config: `asyncio_mode = "auto"` in pyproject.toml
- [ ] ruff + mypy configuration in pyproject.toml

## Sources

### Primary (HIGH confidence)
- [Pydantic v2 Models documentation](https://docs.pydantic.dev/latest/concepts/models/) -- model_config, frozen, validate_assignment, PrivateAttr, field_validator patterns
- [Pydantic v2 Configuration](https://docs.pydantic.dev/latest/api/config/) -- ConfigDict options
- PyPI version checks (pip3 install --dry-run): pydantic 2.12.5, pytest 9.0.2, pytest-asyncio 1.3.0, ruff 0.15.8, mypy 1.20.0

### Secondary (MEDIUM confidence)
- [Python DDD + Hexagonal Architecture patterns](https://dev.to/hieutran25/building-maintainable-python-applications-with-hexagonal-architecture-and-domain-driven-design-chp) -- ABC port patterns, directory structure
- [Hexagonal Architecture in Python 2026](https://johal.in/hexagonal-architecture-design-python-ports-and-adapters-for-modularity-2026/) -- current async patterns
- [Protocol vs ABC comparison](https://jellis18.github.io/post/2022-01-11-abc-vs-protocol/) -- rationale for ABC choice
- [Cosmic Python - Domain Modeling](https://www.cosmicpython.com/book/chapter_01_domain_model.html) -- canonical DDD patterns in Python

### Tertiary (LOW confidence)
- None -- all findings verified with official docs or multiple sources

## Project Constraints (from CLAUDE.md)

- **Language:** Python -- chosen for AI ecosystem compatibility (ADK, LLM libraries)
- **Architecture:** Domain Driven Design + Hexagonal Architecture for the Core
- **Package Manager:** uv -- replaces pip + pip-tools + virtualenv
- **Data Validation:** Pydantic 2.x -- core to FastAPI and domain models
- **Linter:** Ruff -- replaces flake8, black, isort
- **Type Checking:** mypy in strict mode
- **Testing:** pytest + pytest-asyncio + pytest-cov
- **GSD Workflow:** All file changes must go through GSD commands

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified via pip dry-run, all libraries well-established
- Architecture: HIGH -- patterns verified against multiple sources and Pydantic official docs; CONTEXT.md decisions are extremely detailed leaving minimal ambiguity
- Pitfalls: HIGH -- well-known Python/Pydantic issues verified against official docs and common patterns

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable domain -- Pydantic v2 API is mature)
