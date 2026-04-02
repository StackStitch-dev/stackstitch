---
phase: 02A-docker-compose-mongodb-adapters
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docker-compose.yml
  - core/Dockerfile
  - core/pyproject.toml
  - core/src/core/infrastructure/__init__.py
  - core/src/core/infrastructure/adapters/__init__.py
  - core/src/core/infrastructure/adapters/mongodb/__init__.py
  - core/src/core/infrastructure/adapters/mongodb/connection.py
  - core/src/core/infrastructure/web/__init__.py
  - core/src/core/infrastructure/web/app.py
  - core/tests/integration/__init__.py
  - core/tests/integration/conftest.py
  - core/tests/integration/test_health.py
autonomous: true
requirements: [INFR-01, INFR-02]

must_haves:
  truths:
    - "Running `docker compose up -d` starts MongoDB, Kafka, Core, Mongo Express, and Kafka UI without errors"
    - "Core /health endpoint returns 200 with mongodb connected status"
    - "MongoDB adapters can receive AsyncDatabase via constructor injection from the connection module"
    - "Integration tests can spin up a real MongoDB via testcontainers"
  artifacts:
    - path: "docker-compose.yml"
      provides: "Docker Compose orchestration for all services"
      contains: "services:"
    - path: "core/Dockerfile"
      provides: "Multi-stage Docker build for Core service"
      contains: "FROM ghcr.io/astral-sh/uv"
    - path: "core/src/core/infrastructure/adapters/mongodb/connection.py"
      provides: "AsyncMongoClient factory and database accessor"
      exports: ["create_mongo_client", "get_database"]
    - path: "core/src/core/infrastructure/web/app.py"
      provides: "FastAPI app with /health endpoint"
      exports: ["create_app"]
    - path: "core/tests/integration/conftest.py"
      provides: "Session-scoped MongoDB container fixture and function-scoped clean db fixture"
      contains: "MongoDbContainer"
  key_links:
    - from: "docker-compose.yml"
      to: "core/Dockerfile"
      via: "build context"
      pattern: "build:.*context:.*\\./core"
    - from: "core/src/core/infrastructure/web/app.py"
      to: "core/src/core/infrastructure/adapters/mongodb/connection.py"
      via: "AsyncMongoClient import"
      pattern: "AsyncMongoClient"
    - from: "core/tests/integration/conftest.py"
      to: "pymongo.asynchronous.database.AsyncDatabase"
      via: "fixture yields AsyncDatabase"
      pattern: "AsyncDatabase"
---

<objective>
Docker Compose environment, Core Dockerfile, FastAPI health stub, MongoDB connection module, and integration test infrastructure.

Purpose: Establish the infrastructure foundation so that (a) all services start with one `docker compose up` command, (b) the Core service boots and verifies MongoDB connectivity, and (c) integration tests have a real MongoDB container to test against.

Output: docker-compose.yml, Dockerfile, FastAPI health app, MongoDB connection module, integration test conftest with testcontainers fixtures.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02A-docker-compose-mongodb-adapters/02A-CONTEXT.md
@.planning/phases/02A-docker-compose-mongodb-adapters/02A-RESEARCH.md

@core/pyproject.toml
@core/src/core/application/ports/repositories.py

<interfaces>
<!-- Port interfaces that adapters will implement (from Phase 1) -->

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

<task type="auto">
  <name>Task 1: Docker Compose, Dockerfile, dependencies, and FastAPI health stub</name>
  <files>
    docker-compose.yml,
    core/Dockerfile,
    core/pyproject.toml,
    core/src/core/infrastructure/__init__.py,
    core/src/core/infrastructure/web/__init__.py,
    core/src/core/infrastructure/web/app.py
  </files>
  <read_first>
    core/pyproject.toml,
    .planning/phases/02A-docker-compose-mongodb-adapters/02A-RESEARCH.md
  </read_first>
  <action>
    **1. Add production and dev dependencies to `core/pyproject.toml`:**
    Add to `dependencies` list:
    - `"pymongo>=4.16,<5"`
    - `"fastapi>=0.115,<1"`
    - `"uvicorn>=0.32,<1"`
    - `"pydantic-settings>=2.7,<3"`

    Add to `[dependency-groups] dev` list:
    - `"testcontainers[mongodb]>=4.14,<5"`
    - `"httpx>=0.28,<1"`

    Run `cd core && uv sync` to install.

    **2. Create `docker-compose.yml` at project root** per D-01, D-02, D-03.
    Use the exact configuration from RESEARCH.md section "Docker Compose (Complete)":
    - `mongodb` service: `mongo:7`, port 27017, named volume `mongodb_data`, healthcheck with `mongosh --eval "db.adminCommand('ping')"`, interval 10s, timeout 5s, retries 5
    - `kafka` service: `apache/kafka:latest`, port 9092, KRaft mode (D-01) with env vars: KAFKA_NODE_ID=1, KAFKA_PROCESS_ROLES=broker,controller, KAFKA_LISTENERS=PLAINTEXT://kafka:29092,CONTROLLER://kafka:29093,PLAINTEXT_HOST://0.0.0.0:9092, KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092, KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT,CONTROLLER:PLAINTEXT, KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:29093, KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER, KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT, KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1, KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1, KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1, KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS=0, KAFKA_LOG_DIRS=/tmp/kraft-combined-logs, CLUSTER_ID=MkU3OEVBNTcwNTJENDM2Qk. Healthcheck: `/opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092 > /dev/null 2>&1`, interval 15s, timeout 10s, retries 5
    - `mongo-express` service: `mongo-express:latest`, port 8081, ME_CONFIG_MONGODB_URL=mongodb://mongodb:27017/, ME_CONFIG_BASICAUTH=false, depends_on mongodb (service_healthy) -- per D-02
    - `kafka-ui` service: `docker.redpanda.com/redpandadata/console:latest`, port 8080, KAFKA_BROKERS=kafka:29092, depends_on kafka (service_healthy) -- per D-02
    - `core` service: build context `./core`, port 8000, MONGODB_URI=mongodb://mongodb:27017/, MONGODB_DATABASE=stackstitch, depends_on mongodb (service_healthy), healthcheck using python urllib to `http://localhost:8000/health`
    - named volume: `mongodb_data`

    **3. Create `core/Dockerfile`** multi-stage build with uv:
    - Builder stage: `FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder`, WORKDIR /app, ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy, copy pyproject.toml and uv.lock*, run `uv sync --frozen --no-dev --no-install-project`, copy src/, run `uv sync --frozen --no-dev`
    - Runtime stage: `FROM python:3.12-slim-bookworm AS runtime`, WORKDIR /app, COPY --from=builder /app/.venv /app/.venv, ENV PATH="/app/.venv/bin:$PATH", EXPOSE 8000, CMD `["uvicorn", "core.infrastructure.web.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]`

    **4. Create package init files:**
    - `core/src/core/infrastructure/__init__.py` -- empty
    - `core/src/core/infrastructure/web/__init__.py` -- empty

    **5. Create `core/src/core/infrastructure/web/app.py`** per D-03:
    - Import `FastAPI` from fastapi, `AsyncMongoClient` from pymongo, `BaseSettings` from pydantic_settings
    - `CoreSettings(BaseSettings)` class with fields: `mongodb_uri: str = "mongodb://localhost:27017/"`, `mongodb_database: str = "stackstitch"`, and `model_config = {"env_prefix": ""}`
    - `create_app() -> FastAPI` factory function:
      - Creates `CoreSettings()` instance
      - Creates `FastAPI(title="StackStitch Core", version="0.1.0")`
      - Uses `@app.on_event("startup")` to create `AsyncMongoClient(settings.mongodb_uri)` stored in `app.state.mongo_client`
      - Uses `@app.on_event("shutdown")` to call `app.state.mongo_client.close()`
      - `GET /health` endpoint that calls `await app.state.mongo_client.admin.command("ping")` and returns `{"status": "ok", "mongodb": "connected"}` on success, or `{"status": "degraded", "mongodb": "disconnected"}` on exception
  </action>
  <verify>
    <automated>cd /Users/jorgeandresdiaz/Documents/development/stackstitch/core && uv run python -c "from core.infrastructure.web.app import create_app; print('import ok')"</automated>
  </verify>
  <acceptance_criteria>
    - docker-compose.yml exists at project root and contains `services:` with mongodb, kafka, mongo-express, kafka-ui, core
    - docker-compose.yml contains `condition: service_healthy` for mongodb and kafka dependencies
    - docker-compose.yml contains `KAFKA_PROCESS_ROLES: broker,controller` (KRaft mode, D-01)
    - core/Dockerfile contains `FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder`
    - core/Dockerfile contains `CMD ["uvicorn", "core.infrastructure.web.app:create_app"`
    - core/pyproject.toml contains `"pymongo>=4.16,<5"`
    - core/pyproject.toml contains `"testcontainers[mongodb]>=4.14,<5"` in dev dependencies
    - core/src/core/infrastructure/web/app.py contains `def create_app() -> FastAPI:`
    - core/src/core/infrastructure/web/app.py contains `AsyncMongoClient`
    - core/src/core/infrastructure/web/app.py contains `@app.get("/health")`
    - `uv run python -c "from core.infrastructure.web.app import create_app"` exits 0
  </acceptance_criteria>
  <done>Docker Compose file orchestrates MongoDB + Kafka (KRaft) + Core + dev tools. Dockerfile builds Core service. FastAPI health endpoint pings MongoDB. All new dependencies installed.</done>
</task>

<task type="auto">
  <name>Task 2: MongoDB connection module and integration test fixtures</name>
  <files>
    core/src/core/infrastructure/adapters/__init__.py,
    core/src/core/infrastructure/adapters/mongodb/__init__.py,
    core/src/core/infrastructure/adapters/mongodb/connection.py,
    core/tests/integration/__init__.py,
    core/tests/integration/conftest.py,
    core/tests/integration/test_health.py
  </files>
  <read_first>
    core/src/core/infrastructure/web/app.py,
    core/src/core/application/ports/repositories.py,
    .planning/phases/02A-docker-compose-mongodb-adapters/02A-RESEARCH.md
  </read_first>
  <action>
    **1. Create package init files:**
    - `core/src/core/infrastructure/adapters/__init__.py` -- empty
    - `core/src/core/infrastructure/adapters/mongodb/__init__.py` -- empty
    - `core/tests/integration/__init__.py` -- empty

    **2. Create `core/src/core/infrastructure/adapters/mongodb/connection.py`** per D-15:
    ```python
    from pymongo import AsyncMongoClient
    from pymongo.asynchronous.database import AsyncDatabase


    async def create_mongo_client(uri: str) -> AsyncMongoClient:
        """Create and return an AsyncMongoClient. Caller owns lifecycle (close)."""
        client: AsyncMongoClient = AsyncMongoClient(uri)
        return client


    def get_database(client: AsyncMongoClient, db_name: str) -> AsyncDatabase:
        """Get a database reference from the client."""
        return client[db_name]
    ```

    Note per RESEARCH.md: D-15 says "AsyncIOMotorDatabase" but Motor is deprecated. Using `pymongo.asynchronous.database.AsyncDatabase` as the equivalent. Same API surface (insert_one, find_one, find, replace_one, create_index).

    **3. Create `core/tests/integration/conftest.py`** per D-17, D-18:
    - Import `pytest`, `AsyncMongoClient` from pymongo, `AsyncDatabase` from `pymongo.asynchronous.database`, `MongoDbContainer` from `testcontainers.mongodb`
    - `@pytest.fixture(scope="session")` `mongo_container()` fixture: creates `MongoDbContainer("mongo:7")`, calls `.start()`, yields it, calls `.stop()` in teardown
    - `@pytest.fixture` (function-scoped) `mongo_db(mongo_container)` async fixture: gets connection URL via `mongo_container.get_connection_url()`, creates `AsyncMongoClient(url)`, gets db `client["test_stackstitch"]`, yields db, then drops all collections via `for name in await db.list_collection_names(): await db.drop_collection(name)`, then `client.close()`

    **4. Create `core/tests/integration/test_health.py`:**
    - Import `pytest`, `httpx`, `AsyncClient` from httpx, `create_app` from `core.infrastructure.web.app`
    - Use `@pytest.fixture` for a `test_app` that creates the FastAPI app, overrides the MongoDB URI using the `mongo_container` fixture's connection URL
    - Test `test_health_returns_ok`: creates `httpx.AsyncClient` with `app=test_app` using `httpx.ASGITransport`, sends GET to `/health`, asserts status 200, response JSON has `status == "ok"` and `mongodb == "connected"`

    Implementation detail for test_health.py: The create_app function reads settings from env vars. To override for testing, either set `MONGODB_URI` env var in the fixture to point at testcontainers URL, or monkey-patch CoreSettings. Prefer env var approach using `monkeypatch.setenv("MONGODB_URI", mongo_container.get_connection_url())` and then call `create_app()`.
  </action>
  <verify>
    <automated>cd /Users/jorgeandresdiaz/Documents/development/stackstitch/core && uv run pytest tests/integration/test_health.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - core/src/core/infrastructure/adapters/mongodb/connection.py contains `async def create_mongo_client(uri: str) -> AsyncMongoClient:`
    - core/src/core/infrastructure/adapters/mongodb/connection.py contains `def get_database(client: AsyncMongoClient, db_name: str) -> AsyncDatabase:`
    - core/src/core/infrastructure/adapters/mongodb/connection.py imports from `pymongo` not `motor`
    - core/tests/integration/conftest.py contains `MongoDbContainer("mongo:7")`
    - core/tests/integration/conftest.py contains `scope="session"` on mongo_container fixture
    - core/tests/integration/conftest.py contains `await db.drop_collection(name)` for per-test cleanup
    - core/tests/integration/test_health.py contains `"/health"` request
    - core/tests/integration/test_health.py asserts `"status"` is `"ok"` in response
    - `uv run pytest tests/integration/test_health.py -x` exits 0
  </acceptance_criteria>
  <done>Connection module provides AsyncMongoClient factory. Integration test fixtures spin up real MongoDB via testcontainers. Health endpoint integration test passes against real MongoDB.</done>
</task>

</tasks>

<verification>
- `cd core && uv run python -c "from core.infrastructure.web.app import create_app; from core.infrastructure.adapters.mongodb.connection import create_mongo_client, get_database; print('all imports ok')"` exits 0
- `cd core && uv run pytest tests/integration/test_health.py -x -q` passes
- `docker-compose.yml` exists at project root with all 5 services defined
</verification>

<success_criteria>
1. Docker Compose defines MongoDB, Kafka (KRaft), Core, Mongo Express, Kafka UI with health checks
2. Core Dockerfile builds with uv multi-stage pattern
3. FastAPI /health endpoint pings MongoDB and returns connection status
4. MongoDB connection module exports create_mongo_client and get_database using PyMongo async (not Motor)
5. Integration test conftest provides session-scoped MongoDB container and function-scoped clean database
6. Health endpoint integration test passes against real MongoDB
</success_criteria>

<output>
After completion, create `.planning/phases/02A-docker-compose-mongodb-adapters/02A-01-SUMMARY.md`
</output>
