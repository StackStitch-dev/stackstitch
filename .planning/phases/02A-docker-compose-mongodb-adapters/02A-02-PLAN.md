---
phase: 02A-docker-compose-mongodb-adapters
plan: 02
type: execute
wave: 2
depends_on: ["02A-01"]
files_modified:
  - core/src/core/infrastructure/adapters/mongodb/stream_repository.py
  - core/src/core/infrastructure/adapters/mongodb/metric_repository.py
  - core/src/core/infrastructure/adapters/mongodb/insight_repository.py
  - core/tests/integration/test_stream_repository.py
  - core/tests/integration/test_metric_repository.py
  - core/tests/integration/test_insight_repository.py
autonomous: true
requirements: [INFR-02]

must_haves:
  truths:
    - "StreamDataPoints are persisted as individual documents in the 'streams' collection with denormalized parent keys"
    - "Stream.save() decomposes the aggregate; Stream.get_by_key() reassembles it from child documents"
    - "MetricDataPoints are persisted as individual documents in the 'metrics' collection with denormalized parent keys"
    - "Metric.save() decomposes the aggregate; Metric.get_by_key() reassembles it from child documents"
    - "Insights are persisted with UUID string as _id and round-trip correctly through save/get_by_id"
  artifacts:
    - path: "core/src/core/infrastructure/adapters/mongodb/stream_repository.py"
      provides: "MongoStreamRepository implementing StreamRepository port"
      contains: "class MongoStreamRepository"
    - path: "core/src/core/infrastructure/adapters/mongodb/metric_repository.py"
      provides: "MongoMetricRepository implementing MetricRepository port"
      contains: "class MongoMetricRepository"
    - path: "core/src/core/infrastructure/adapters/mongodb/insight_repository.py"
      provides: "MongoInsightRepository implementing InsightRepository port"
      contains: "class MongoInsightRepository"
    - path: "core/tests/integration/test_stream_repository.py"
      provides: "Round-trip integration tests for StreamRepository"
      contains: "test_save_and_get_by_key"
    - path: "core/tests/integration/test_metric_repository.py"
      provides: "Round-trip integration tests for MetricRepository"
      contains: "test_save_and_get_by_key"
    - path: "core/tests/integration/test_insight_repository.py"
      provides: "Round-trip integration tests for InsightRepository"
      contains: "test_save_and_get_by_id"
  key_links:
    - from: "core/src/core/infrastructure/adapters/mongodb/stream_repository.py"
      to: "core/src/core/application/ports/repositories.py"
      via: "implements StreamRepository ABC"
      pattern: "class MongoStreamRepository\\(StreamRepository\\)"
    - from: "core/src/core/infrastructure/adapters/mongodb/metric_repository.py"
      to: "core/src/core/application/ports/repositories.py"
      via: "implements MetricRepository ABC"
      pattern: "class MongoMetricRepository\\(MetricRepository\\)"
    - from: "core/src/core/infrastructure/adapters/mongodb/insight_repository.py"
      to: "core/src/core/application/ports/repositories.py"
      via: "implements InsightRepository ABC"
      pattern: "class MongoInsightRepository\\(InsightRepository\\)"
---

<objective>
MongoDB adapters for Stream, Metric, and Insight repositories with full round-trip integration tests.

Purpose: Implement the decompose-on-write / assemble-on-read pattern for composite-key aggregates (Stream, Metric) and UUID-based entity persistence (Insight) against real MongoDB.

Output: 3 adapter implementations + 3 integration test files, all passing against testcontainers MongoDB.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/02A-docker-compose-mongodb-adapters/02A-CONTEXT.md
@.planning/phases/02A-docker-compose-mongodb-adapters/02A-RESEARCH.md

@core/src/core/application/ports/repositories.py
@core/src/core/domain/entities/stream.py
@core/src/core/domain/entities/metric.py
@core/src/core/domain/entities/insight.py
@core/src/core/domain/enums.py
@core/src/core/infrastructure/adapters/mongodb/connection.py
@core/tests/integration/conftest.py

<interfaces>
<!-- Domain entities the adapters must serialize/deserialize -->

From core/src/core/domain/entities/stream.py:
```python
class StreamDataPoint(BaseModel):
    model_config = ConfigDict(frozen=True)
    timestamp: datetime
    data: dict[str, Any]

class Stream(BaseModel):
    source: str
    stream_type: StreamType
    project_id: UUID
    data_points: list[StreamDataPoint] = Field(default_factory=list)
```

From core/src/core/domain/entities/metric.py:
```python
class MetricDataPoint(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: float
    timestamp: datetime

class Metric(BaseModel):
    metric_type: MetricType
    project_id: UUID
    data_points: list[MetricDataPoint] = Field(default_factory=list)
```

From core/src/core/domain/entities/insight.py:
```python
class Insight(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    investigation_id: UUID
    thread_id: UUID | None = None
    title: str
    narrative: str
    insight_type: InsightType
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

From core/src/core/application/ports/repositories.py:
```python
class StreamRepository(abc.ABC):
    async def save(self, stream: Stream) -> None: ...
    async def get_by_key(self, source: str, stream_type: StreamType, project_id: UUID) -> Stream | None: ...

class MetricRepository(abc.ABC):
    async def save(self, metric: Metric) -> None: ...
    async def get_by_key(self, metric_type: MetricType, project_id: UUID) -> Metric | None: ...

class InsightRepository(abc.ABC):
    async def save(self, insight: Insight) -> None: ...
    async def get_by_id(self, insight_id: UUID) -> Insight | None: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Stream and Metric repository adapters with integration tests</name>
  <files>
    core/src/core/infrastructure/adapters/mongodb/stream_repository.py,
    core/src/core/infrastructure/adapters/mongodb/metric_repository.py,
    core/tests/integration/test_stream_repository.py,
    core/tests/integration/test_metric_repository.py
  </files>
  <read_first>
    core/src/core/application/ports/repositories.py,
    core/src/core/domain/entities/stream.py,
    core/src/core/domain/entities/metric.py,
    core/src/core/domain/enums.py,
    core/tests/integration/conftest.py,
    core/src/core/infrastructure/adapters/mongodb/connection.py
  </read_first>
  <behavior>
    Stream tests:
    - test_save_and_get_by_key: Save a Stream with 2 data_points, get_by_key returns Stream with same source/stream_type/project_id and 2 data_points with matching timestamps and data
    - test_get_by_key_not_found: get_by_key for non-existent key returns None
    - test_save_appends_new_data_points: Save Stream with 1 dp, add another dp, save again, get_by_key returns 2 data_points (no duplicates)
    - test_indexes_created: After ensure_indexes(), the streams collection has a compound index on (source, stream_type, project_id)

    Metric tests:
    - test_save_and_get_by_key: Save a Metric with 2 data_points, get_by_key returns Metric with same metric_type/project_id and 2 data_points with matching values and timestamps
    - test_get_by_key_not_found: get_by_key for non-existent key returns None
    - test_save_appends_new_data_points: Save Metric with 1 dp, add another dp, save again, get_by_key returns 2 data_points (no duplicates)
  </behavior>
  <action>
    **MongoStreamRepository (`core/src/core/infrastructure/adapters/mongodb/stream_repository.py`):**

    Per D-04, D-05, D-06, D-08, D-12. Uses decompose-on-write / assemble-on-read pattern.

    ```python
    class MongoStreamRepository(StreamRepository):
        def __init__(self, db: AsyncDatabase) -> None:
            self._collection = db["streams"]
    ```

    - `ensure_indexes()`: Create compound index on `[("source", 1), ("stream_type", 1), ("project_id", 1)]`
    - `save(stream)`: For each data_point in stream.data_points, create a document with:
      - `_id`: Use a deterministic string id to prevent duplicates on re-save. Generate via `str(uuid5(NAMESPACE_URL, f"{stream.source}:{stream.stream_type.value}:{stream.project_id}:{dp.timestamp.isoformat()}"))` using `uuid.uuid5` and `uuid.NAMESPACE_URL`. This makes saves idempotent per RESEARCH.md Pitfall 2 guidance.
      - `source`: `stream.source`
      - `stream_type`: `stream.stream_type.value` (string, not enum -- per RESEARCH Pitfall 4)
      - `project_id`: `str(stream.project_id)`
      - `timestamp`: `dp.timestamp`
      - `data`: `dp.data`
      - Use `replace_one({"_id": doc["_id"]}, doc, upsert=True)` for each data_point
    - `get_by_key(source, stream_type, project_id)`: Query with `{"source": source, "stream_type": stream_type.value, "project_id": str(project_id)}`. Collect all docs via `cursor.to_list()`. If empty, return None. Otherwise construct `StreamDataPoint(timestamp=doc["timestamp"], data=doc["data"])` for each doc, then `Stream(source=source, stream_type=stream_type, project_id=project_id, data_points=data_points)`.

    **MongoMetricRepository (`core/src/core/infrastructure/adapters/mongodb/metric_repository.py`):**

    Same decompose/assemble pattern for Metric. Per D-04, D-05, D-06, D-08.

    ```python
    class MongoMetricRepository(MetricRepository):
        def __init__(self, db: AsyncDatabase) -> None:
            self._collection = db["metrics"]
    ```

    - `ensure_indexes()`: Compound index on `[("metric_type", 1), ("project_id", 1)]`
    - `save(metric)`: For each data_point, create document:
      - `_id`: deterministic via `str(uuid5(NAMESPACE_URL, f"{metric.metric_type.value}:{metric.project_id}:{dp.timestamp.isoformat()}"))`
      - `metric_type`: `metric.metric_type.value`
      - `project_id`: `str(metric.project_id)`
      - `value`: `dp.value`
      - `timestamp`: `dp.timestamp`
      - Use `replace_one` with upsert per data_point
    - `get_by_key(metric_type, project_id)`: Query `{"metric_type": metric_type.value, "project_id": str(project_id)}`, collect docs, if empty return None, else construct MetricDataPoint list and Metric.

    **Integration tests** use the `mongo_db` fixture from conftest.py. Create adapter instance with `MongoStreamRepository(mongo_db)`. Call `ensure_indexes()` before tests. Use domain entity factories (create Stream/Metric with test data using known UUIDs and timestamps).

    Import `AsyncDatabase` from `pymongo.asynchronous.database` for type hints. All enums are `str, Enum` subclasses so `.value` returns the string value.
  </action>
  <verify>
    <automated>cd /Users/jorgeandresdiaz/Documents/development/stackstitch/core && uv run pytest tests/integration/test_stream_repository.py tests/integration/test_metric_repository.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - stream_repository.py contains `class MongoStreamRepository(StreamRepository):`
    - stream_repository.py contains `self._collection = db["streams"]` (D-05)
    - stream_repository.py contains `replace_one(` for upsert pattern
    - stream_repository.py contains `stream_type.value` (enum to string conversion)
    - stream_repository.py contains `uuid5` for deterministic _id generation
    - metric_repository.py contains `class MongoMetricRepository(MetricRepository):`
    - metric_repository.py contains `self._collection = db["metrics"]` (D-05)
    - test_stream_repository.py has at least 3 test functions
    - test_metric_repository.py has at least 3 test functions
    - `uv run pytest tests/integration/test_stream_repository.py tests/integration/test_metric_repository.py -x` exits 0
  </acceptance_criteria>
  <done>Stream and Metric adapters implement decompose-on-write / assemble-on-read with deterministic _id generation. All integration tests pass round-trip persistence against real MongoDB.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Insight repository adapter with integration tests</name>
  <files>
    core/src/core/infrastructure/adapters/mongodb/insight_repository.py,
    core/tests/integration/test_insight_repository.py
  </files>
  <read_first>
    core/src/core/application/ports/repositories.py,
    core/src/core/domain/entities/insight.py,
    core/src/core/domain/enums.py,
    core/tests/integration/conftest.py,
    core/src/core/infrastructure/adapters/mongodb/stream_repository.py
  </read_first>
  <behavior>
    - test_save_and_get_by_id: Save an Insight, get_by_id returns Insight with same id, project_id, investigation_id, title, narrative, insight_type, metadata, created_at
    - test_get_by_id_not_found: get_by_id for non-existent UUID returns None
    - test_save_with_optional_thread_id: Save Insight with thread_id set, get_by_id returns it with thread_id preserved
    - test_save_overwrites_on_duplicate_id: Save Insight, modify title, save again, get_by_id returns updated title
  </behavior>
  <action>
    **MongoInsightRepository (`core/src/core/infrastructure/adapters/mongodb/insight_repository.py`):**

    Per D-05, D-07. UUID-as-string _id pattern.

    ```python
    class MongoInsightRepository(InsightRepository):
        def __init__(self, db: AsyncDatabase) -> None:
            self._collection = db["insights"]
    ```

    - `ensure_indexes()`: Single index on `[("project_id", 1)]` for future queries by project
    - `save(insight)`: Use `insight.model_dump(mode="json")` to get dict with string enums. Then:
      - `doc["_id"] = doc.pop("id")` -- already a string from mode="json"
      - Remove any `_events` key if present (PrivateAttr should not serialize, but be defensive)
      - `replace_one({"_id": doc["_id"]}, doc, upsert=True)`
    - `get_by_id(insight_id)`: `find_one({"_id": str(insight_id)})`. If None, return None. Else:
      - `doc["id"] = doc.pop("_id")`
      - `Insight.model_validate(doc)`
      - Note: `model_validate` with mode="json" strings should work since all fields in the doc are JSON-serializable strings/dicts. Pydantic will coerce UUID strings back to UUID, datetime ISO strings back to datetime, etc.

    **Integration tests:** Use `mongo_db` fixture. Create Insight instances with known UUIDs (use `uuid4()` in test). Verify all fields round-trip correctly including metadata dict, optional thread_id (None and non-None cases), and datetime precision.

    Handle datetime carefully per RESEARCH Pitfall 3: MongoDB may strip timezone info. After retrieval, verify timestamps are approximately equal (within 1ms) rather than exact equality, OR use `model_dump(mode="json")` which serializes to ISO string, and compare ISO strings.
  </action>
  <verify>
    <automated>cd /Users/jorgeandresdiaz/Documents/development/stackstitch/core && uv run pytest tests/integration/test_insight_repository.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - insight_repository.py contains `class MongoInsightRepository(InsightRepository):`
    - insight_repository.py contains `self._collection = db["insights"]` (D-05)
    - insight_repository.py contains `doc["_id"] = doc.pop("id")` or equivalent _id mapping
    - insight_repository.py contains `model_dump` for serialization
    - insight_repository.py contains `model_validate` for deserialization
    - insight_repository.py does NOT import from `motor`
    - test_insight_repository.py has at least 3 test functions
    - `uv run pytest tests/integration/test_insight_repository.py -x` exits 0
  </acceptance_criteria>
  <done>Insight adapter persists and retrieves Insight entities with UUID string _id. All fields including optional thread_id and metadata dict round-trip correctly. Integration tests pass.</done>
</task>

</tasks>

<verification>
- `cd core && uv run pytest tests/integration/test_stream_repository.py tests/integration/test_metric_repository.py tests/integration/test_insight_repository.py -x -q` -- all pass
- Each adapter class inherits from its port ABC (grep confirms)
- No `motor` imports anywhere in the mongodb adapter directory
</verification>

<success_criteria>
1. MongoStreamRepository implements decompose-on-write / assemble-on-read for Stream aggregate with deterministic _id
2. MongoMetricRepository implements same pattern for Metric aggregate
3. MongoInsightRepository implements UUID-as-string _id pattern for Insight entity
4. All adapters use PyMongo async (AsyncDatabase), not Motor
5. All adapters have ensure_indexes() methods
6. Integration tests verify full round-trip for save + get_by_key/get_by_id per D-19
7. All integration tests pass against real MongoDB via testcontainers
</success_criteria>

<output>
After completion, create `.planning/phases/02A-docker-compose-mongodb-adapters/02A-02-SUMMARY.md`
</output>
