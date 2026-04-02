---
phase: 02A-docker-compose-mongodb-adapters
plan: 03
type: execute
wave: 2
depends_on: ["02A-01"]
files_modified:
  - core/src/core/infrastructure/adapters/mongodb/investigation_repository.py
  - core/src/core/infrastructure/adapters/mongodb/thread_repository.py
  - core/src/core/infrastructure/adapters/mongodb/invocation_repository.py
  - core/tests/integration/test_investigation_repository.py
  - core/tests/integration/test_thread_repository.py
  - core/tests/integration/test_invocation_repository.py
autonomous: true
requirements: [INFR-02]

must_haves:
  truths:
    - "Investigation documents include embedded InvestigationStep objects (D-10)"
    - "Investigation round-trips through save/get_by_id preserving status, steps, findings, and tokens_used"
    - "Thread.save() persists Message child documents in the 'threads' collection with thread_id reference (D-09)"
    - "Thread.get_by_id() assembles the Thread aggregate from its Message documents"
    - "Thread.get_by_project_id() returns all threads for a project"
    - "Invocation documents persist with UUID string _id and round-trip all fields"
    - "InvocationRepository.get_pending_by_thread_id() returns only PENDING invocations for a given thread"
  artifacts:
    - path: "core/src/core/infrastructure/adapters/mongodb/investigation_repository.py"
      provides: "MongoInvestigationRepository implementing InvestigationRepository port"
      contains: "class MongoInvestigationRepository"
    - path: "core/src/core/infrastructure/adapters/mongodb/thread_repository.py"
      provides: "MongoThreadRepository implementing ThreadRepository port"
      contains: "class MongoThreadRepository"
    - path: "core/src/core/infrastructure/adapters/mongodb/invocation_repository.py"
      provides: "MongoInvocationRepository implementing InvocationRepository port"
      contains: "class MongoInvocationRepository"
    - path: "core/tests/integration/test_investigation_repository.py"
      provides: "Round-trip integration tests for InvestigationRepository"
      contains: "test_save_and_get_by_id"
    - path: "core/tests/integration/test_thread_repository.py"
      provides: "Round-trip integration tests for ThreadRepository"
      contains: "test_save_and_get_by_id"
    - path: "core/tests/integration/test_invocation_repository.py"
      provides: "Round-trip integration tests for InvocationRepository"
      contains: "test_get_pending_by_thread_id"
  key_links:
    - from: "core/src/core/infrastructure/adapters/mongodb/investigation_repository.py"
      to: "core/src/core/application/ports/repositories.py"
      via: "implements InvestigationRepository ABC"
      pattern: "class MongoInvestigationRepository\\(InvestigationRepository\\)"
    - from: "core/src/core/infrastructure/adapters/mongodb/thread_repository.py"
      to: "core/src/core/application/ports/repositories.py"
      via: "implements ThreadRepository ABC"
      pattern: "class MongoThreadRepository\\(ThreadRepository\\)"
    - from: "core/src/core/infrastructure/adapters/mongodb/invocation_repository.py"
      to: "core/src/core/application/ports/repositories.py"
      via: "implements InvocationRepository ABC"
      pattern: "class MongoInvocationRepository\\(InvocationRepository\\)"
---

<objective>
MongoDB adapters for Investigation, Thread, and Invocation repositories with full round-trip integration tests.

Purpose: Complete all 6 repository port implementations. Investigation has embedded steps (D-10), Thread uses the decompose/assemble pattern for messages (D-09), and Invocation supports the pending-by-thread query needed for the orchestration drain loop.

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
@core/src/core/domain/entities/investigation.py
@core/src/core/domain/entities/thread.py
@core/src/core/domain/entities/invocation.py
@core/src/core/domain/enums.py
@core/src/core/infrastructure/adapters/mongodb/connection.py
@core/tests/integration/conftest.py

<interfaces>
<!-- Domain entities the adapters must serialize/deserialize -->

From core/src/core/domain/entities/investigation.py:
```python
class InvestigationStep(BaseModel):
    model_config = ConfigDict(frozen=True)
    step_type: InvestigationStepType
    tool_name: str | None = None
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""
    tokens_used: int = 0

class Investigation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    trigger: InvestigationTrigger
    trigger_ref: UUID
    query: str | None = None
    status: InvestigationStatus = InvestigationStatus.PENDING
    steps: list[InvestigationStep] = Field(default_factory=list)
    findings: str | None = None
    tokens_used: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

From core/src/core/domain/entities/thread.py:
```python
class Message(BaseModel):
    model_config = ConfigDict(frozen=True)
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Thread(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

From core/src/core/domain/entities/invocation.py:
```python
class Invocation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    thread_id: UUID
    project_id: UUID
    source: InvocationSource
    role: str
    message: str
    status: InvocationStatus = InvocationStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

From core/src/core/application/ports/repositories.py:
```python
class InvestigationRepository(abc.ABC):
    async def save(self, investigation: Investigation) -> None: ...
    async def get_by_id(self, investigation_id: UUID) -> Investigation | None: ...

class ThreadRepository(abc.ABC):
    async def save(self, thread: Thread) -> None: ...
    async def get_by_id(self, thread_id: UUID) -> Thread | None: ...
    async def get_by_project_id(self, project_id: UUID) -> list[Thread]: ...

class InvocationRepository(abc.ABC):
    async def save(self, invocation: Invocation) -> None: ...
    async def save_many(self, invocations: list[Invocation]) -> None: ...
    async def get_by_id(self, invocation_id: UUID) -> Invocation | None: ...
    async def get_pending_by_thread_id(self, thread_id: UUID) -> list[Invocation]: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Investigation repository adapter with integration tests</name>
  <files>
    core/src/core/infrastructure/adapters/mongodb/investigation_repository.py,
    core/tests/integration/test_investigation_repository.py
  </files>
  <read_first>
    core/src/core/application/ports/repositories.py,
    core/src/core/domain/entities/investigation.py,
    core/src/core/domain/enums.py,
    core/tests/integration/conftest.py
  </read_first>
  <behavior>
    - test_save_and_get_by_id: Save an Investigation (PENDING status, no steps), get_by_id returns it with matching fields
    - test_get_by_id_not_found: get_by_id for non-existent UUID returns None
    - test_save_with_steps_embedded: Save Investigation with 2 InvestigationStep objects, get_by_id returns Investigation with steps list containing both steps with all fields preserved (step_type, tool_name, input_data, output_data, reasoning, tokens_used)
    - test_save_completed_investigation: Create Investigation, call start(), then complete() with InvestigatorResult, save, get_by_id returns COMPLETED status with findings and tokens_used
    - test_save_overwrites_on_duplicate_id: Save, modify status, save again, get_by_id returns updated status
  </behavior>
  <action>
    **MongoInvestigationRepository (`core/src/core/infrastructure/adapters/mongodb/investigation_repository.py`):**

    Per D-05, D-07, D-10. Investigation is a single document with embedded steps.

    ```python
    class MongoInvestigationRepository(InvestigationRepository):
        def __init__(self, db: AsyncDatabase) -> None:
            self._collection = db["investigations"]
    ```

    - `ensure_indexes()`: Single index on `[("project_id", 1)]`
    - `save(investigation)`: Use `investigation.model_dump(mode="json")`. Then:
      - `doc["_id"] = doc.pop("id")` -- UUID string as _id per D-07
      - Remove `_events` key if present
      - `replace_one({"_id": doc["_id"]}, doc, upsert=True)`
      - Steps are embedded directly in the document per D-10 -- model_dump serializes them as list of dicts
    - `get_by_id(investigation_id)`: `find_one({"_id": str(investigation_id)})`. If None return None. Else:
      - `doc["id"] = doc.pop("_id")`
      - `Investigation.model_validate(doc)` -- Pydantic handles nested InvestigationStep deserialization

    Note: InvestigationStep is embedded (D-10), not a separate collection. model_dump(mode="json") serializes steps as list of dicts with string enum values. model_validate reconstructs them back into InvestigationStep objects.
  </action>
  <verify>
    <automated>cd /Users/jorgeandresdiaz/Documents/development/stackstitch/core && uv run pytest tests/integration/test_investigation_repository.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - investigation_repository.py contains `class MongoInvestigationRepository(InvestigationRepository):`
    - investigation_repository.py contains `self._collection = db["investigations"]` (D-05)
    - investigation_repository.py contains `model_dump(mode="json")` for serialization
    - investigation_repository.py does NOT create a separate collection for steps (D-10)
    - test_investigation_repository.py has at least 4 test functions including one testing embedded steps
    - `uv run pytest tests/integration/test_investigation_repository.py -x` exits 0
  </acceptance_criteria>
  <done>Investigation adapter persists and retrieves Investigation entities with embedded InvestigationStep objects. All fields including optional query, status transitions, and nested steps round-trip correctly.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Thread and Invocation repository adapters with integration tests</name>
  <files>
    core/src/core/infrastructure/adapters/mongodb/thread_repository.py,
    core/src/core/infrastructure/adapters/mongodb/invocation_repository.py,
    core/tests/integration/test_thread_repository.py,
    core/tests/integration/test_invocation_repository.py
  </files>
  <read_first>
    core/src/core/application/ports/repositories.py,
    core/src/core/domain/entities/thread.py,
    core/src/core/domain/entities/invocation.py,
    core/src/core/domain/enums.py,
    core/tests/integration/conftest.py
  </read_first>
  <behavior>
    Thread tests:
    - test_save_and_get_by_id: Save a Thread with 2 messages, get_by_id returns Thread with same id, project_id, created_at, and 2 messages with matching role/content/timestamp
    - test_get_by_id_not_found: get_by_id for non-existent UUID returns None
    - test_get_by_project_id: Save 2 threads with same project_id and 1 with different, get_by_project_id returns only the 2 matching threads
    - test_get_by_project_id_empty: get_by_project_id for project with no threads returns empty list
    - test_save_appends_new_messages: Save Thread with 1 message, add another message, save again, get_by_id returns 2 messages (no duplicates)

    Invocation tests:
    - test_save_and_get_by_id: Save an Invocation, get_by_id returns it with all fields matching
    - test_get_by_id_not_found: get_by_id for non-existent UUID returns None
    - test_save_many: Save 3 invocations via save_many, get_by_id returns each one
    - test_get_pending_by_thread_id: Save 3 invocations for same thread (2 PENDING, 1 PROCESSING), get_pending_by_thread_id returns only the 2 PENDING ones
    - test_get_pending_by_thread_id_empty: get_pending_by_thread_id for thread with no pending invocations returns empty list
    - test_save_overwrites_on_duplicate_id: Save, change status to PROCESSING, save again, get_by_id returns PROCESSING
  </behavior>
  <action>
    **MongoThreadRepository (`core/src/core/infrastructure/adapters/mongodb/thread_repository.py`):**

    Per D-04, D-05, D-09, D-12. Thread is a virtual parent. Messages are individual documents in the `threads` collection with a `thread_id` field.

    ```python
    class MongoThreadRepository(ThreadRepository):
        def __init__(self, db: AsyncDatabase) -> None:
            self._collection = db["threads"]
    ```

    - `ensure_indexes()`: Compound index on `[("thread_id", 1)]` and single index on `[("project_id", 1)]`
    - `save(thread)`: Decompose-on-write pattern. For each message in thread.messages:
      - Generate deterministic `_id` via `str(uuid5(NAMESPACE_URL, f"{thread.id}:{msg.role.value}:{msg.content}:{msg.timestamp.isoformat()}"))` to prevent duplicates on re-save
      - Document fields: `_id`, `thread_id: str(thread.id)`, `project_id: str(thread.project_id)`, `created_at: thread.created_at.isoformat()` (thread-level metadata on each doc), `role: msg.role.value`, `content: msg.content`, `timestamp: msg.timestamp.isoformat()`
      - Use `replace_one({"_id": doc_id}, doc, upsert=True)` per message
    - `get_by_id(thread_id)`: Query `{"thread_id": str(thread_id)}`. Collect docs. If empty, return None. Reconstruct messages list from docs. Build Thread with id=thread_id, project_id from first doc, messages=messages, created_at from first doc.
    - `get_by_project_id(project_id)`: Query `{"project_id": str(project_id)}`. Group docs by `thread_id`. For each group, assemble a Thread object. Return list of Threads.

    **MongoInvocationRepository (`core/src/core/infrastructure/adapters/mongodb/invocation_repository.py`):**

    Per D-05, D-07. Simple UUID entity, no decomposition needed.

    ```python
    class MongoInvocationRepository(InvocationRepository):
        def __init__(self, db: AsyncDatabase) -> None:
            self._collection = db["invocations"]
    ```

    - `ensure_indexes()`: Compound index on `[("thread_id", 1), ("status", 1)]` for get_pending_by_thread_id query
    - `save(invocation)`: `invocation.model_dump(mode="json")`, `doc["_id"] = doc.pop("id")`, `replace_one({"_id": doc["_id"]}, doc, upsert=True)`
    - `save_many(invocations)`: Loop and call save for each. (Could use bulk_write for performance but correctness first.)
    - `get_by_id(invocation_id)`: `find_one({"_id": str(invocation_id)})`, reconstruct via `doc["id"] = doc.pop("_id")`, `Invocation.model_validate(doc)`
    - `get_pending_by_thread_id(thread_id)`: Query `{"thread_id": str(thread_id), "status": "pending"}`. Collect docs, reconstruct each as Invocation. Return list.

    Note on InvocationStatus filter: Since enums are `str, Enum` and we use `model_dump(mode="json")`, the status is stored as `"pending"`, `"processing"`, `"done"` strings. Query with the string value directly.
  </action>
  <verify>
    <automated>cd /Users/jorgeandresdiaz/Documents/development/stackstitch/core && uv run pytest tests/integration/test_thread_repository.py tests/integration/test_invocation_repository.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - thread_repository.py contains `class MongoThreadRepository(ThreadRepository):`
    - thread_repository.py contains `self._collection = db["threads"]` (D-05)
    - thread_repository.py contains `"thread_id": str(thread.id)` for message documents (D-09)
    - thread_repository.py contains `uuid5` for deterministic message _id
    - invocation_repository.py contains `class MongoInvocationRepository(InvocationRepository):`
    - invocation_repository.py contains `self._collection = db["invocations"]` (D-05)
    - invocation_repository.py contains `"status": "pending"` in get_pending_by_thread_id query
    - test_thread_repository.py has at least 4 test functions including get_by_project_id
    - test_invocation_repository.py has at least 5 test functions including get_pending_by_thread_id and save_many
    - `uv run pytest tests/integration/test_thread_repository.py tests/integration/test_invocation_repository.py -x` exits 0
  </acceptance_criteria>
  <done>Thread adapter decomposes messages into individual documents with thread_id reference and reassembles on read. Invocation adapter supports save/save_many/get_by_id/get_pending_by_thread_id. All integration tests pass.</done>
</task>

</tasks>

<verification>
- `cd core && uv run pytest tests/integration/ -x -q` -- all integration tests pass (health + 6 repositories)
- Each of the 6 adapter classes inherits from its port ABC
- No `motor` imports in any adapter file
- Thread messages stored as individual documents with thread_id field (D-09)
- Investigation steps embedded within investigation document (D-10)
- Invocation get_pending_by_thread_id filters on status="pending"
</verification>

<success_criteria>
1. MongoInvestigationRepository persists Investigation with embedded InvestigationStep objects (D-10)
2. MongoThreadRepository decomposes messages into individual documents with thread_id (D-09) and assembles on read (D-12)
3. MongoThreadRepository.get_by_project_id returns all threads for a project
4. MongoInvocationRepository persists invocations with UUID string _id (D-07)
5. MongoInvocationRepository.get_pending_by_thread_id returns only PENDING status invocations
6. MongoInvocationRepository.save_many persists multiple invocations
7. All adapters use PyMongo async (AsyncDatabase), not Motor
8. All adapters have ensure_indexes() methods with appropriate indexes
9. All integration tests pass against real MongoDB via testcontainers
</success_criteria>

<output>
After completion, create `.planning/phases/02A-docker-compose-mongodb-adapters/02A-03-SUMMARY.md`
</output>
