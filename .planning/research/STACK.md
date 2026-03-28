# Technology Stack

**Project:** StackStitch
**Researched:** 2026-03-27
**Note:** Web search and fetch tools were unavailable during research. Versions are based on training data (cutoff ~May 2025) and should be verified with `pip index versions <package>` before locking. Confidence levels reflect this limitation.

## Recommended Stack

### Python Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12+ | Runtime | 3.12 is stable with significant performance improvements (specializing interpreter). 3.13 is available but newer; 3.12 is the safe production choice. Google ADK requires 3.10+. | MEDIUM |
| uv | latest | Package manager | 10-100x faster than pip, drop-in compatible, handles virtualenvs and lockfiles. Replaces pip + pip-tools + virtualenv. Created by Astral (same team as ruff). | MEDIUM |

### Web Framework & API

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| FastAPI | ~0.115+ | HTTP API framework | Async-native, Pydantic-native, OpenAPI auto-generation. The standard for Python async APIs. Needed for webhook endpoints (GitHub), sync inter-service calls, and health checks. | HIGH |
| Uvicorn | ~0.32+ | ASGI server | Standard production server for FastAPI. Use with `--workers` for multi-process in production. | HIGH |
| Pydantic | 2.x (~2.10+) | Data validation & settings | V2 is a complete rewrite in Rust, dramatically faster. Core to FastAPI and used for domain models, DTOs, and settings management via `pydantic-settings`. | HIGH |
| pydantic-settings | ~2.7+ | Configuration management | Loads config from env vars, .env files, secrets. Typed configuration with validation. | HIGH |

### Database

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| MongoDB | 7.x+ | Primary data store | Already decided. Handles variable schemas from different connectors well. Use separate collections per aggregate (streams, metrics, insights). | HIGH |
| Motor | ~3.6+ | Async MongoDB driver | Async wrapper around PyMongo. Required for non-blocking DB access in async services. Use Motor for Connector Service and Channel System (async). | MEDIUM |
| PyMongo | ~4.9+ | Sync MongoDB driver | Motor depends on it. May also use directly in Core service if Core runs synchronously (simpler DDD implementation). | MEDIUM |
| Beanie | ~1.27+ | Async ODM (optional) | Pydantic-native ODM built on Motor. Provides document models, query builders, and migrations. Useful but adds a layer -- evaluate if raw Motor suffices for hexagonal ports. | LOW |

### Message Broker

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Apache Kafka | 3.7+ (Docker image) | Message broker | Already decided. Ordered message processing for correct metric calculation. Use `confluentinc/cp-kafka` Docker image. Consider KRaft mode (no Zookeeper) for simpler deployment. | HIGH |
| confluent-kafka | ~2.6+ | Python Kafka client | Confluent's official Python client, wraps librdkafka (C). Fastest and most reliable Python Kafka library. Use for both producers and consumers. | MEDIUM |
| Schema Registry | (Confluent) | Schema management | Optional but recommended for v2+. Enforces Avro/JSON Schema on Kafka messages. Prevents schema drift between services. Use `confluent-kafka[avro]` or `confluent-kafka[json]`. | MEDIUM |

**Why NOT aiokafka:** confluent-kafka is built on librdkafka (C library) and is significantly more performant and battle-tested. aiokafka is pure Python and has had reliability issues under load. confluent-kafka works fine with asyncio via threading or `confluent_kafka.Consumer` in a background thread.

### Agent Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| google-adk | ~1.x | Agent framework | Already decided. Google's Agent Development Kit for building AI agents with tool-use patterns. Fits the investigator architecture where agents have tools to query stores. | LOW |
| google-genai | (ADK dep) | Gemini API client | ADK's underlying client for Gemini models. Supports function calling, structured output. | LOW |
| LiteLLM | ~1.55+ | LLM proxy (BYOK) | Since BYOK means supporting multiple LLM providers (not just Gemini), LiteLLM provides a unified interface to 100+ LLMs. Use alongside ADK for provider flexibility. | MEDIUM |

**ADK Note:** Google ADK was released in April 2025 and is relatively new. Documentation and API stability should be verified against current docs. The core pattern (agent + tools + memory) aligns well with investigators. LOW confidence on version because this is a fast-moving library.

### Slack Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| slack-bolt | ~1.21+ | Slack app framework | Official Slack SDK for Python apps. Handles events, commands, interactivity, and Socket Mode. Use `slack-bolt[async]` for async support. | HIGH |
| slack-sdk | ~3.33+ | Slack API client | Lower-level client (dependency of bolt). Direct API calls for sending messages, blocks, etc. | HIGH |

### GitHub Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PyGithub | ~2.5+ | GitHub REST API | Well-maintained, covers the full GitHub REST API. Use for polling/backfill operations. | MEDIUM |
| httpx | ~0.28+ | HTTP client | Async HTTP client for webhook ingestion and direct API calls. Preferred over requests for async contexts. | HIGH |

**Recommendation:** Use httpx directly for webhook ingestion (lightweight, you control the parsing) and PyGithub for polling/backfill operations. Webhooks are simple POST handlers that don't need a full SDK.

### Testing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pytest | ~8.3+ | Test framework | Standard Python testing. Use with `pytest-asyncio` for async tests. | HIGH |
| pytest-asyncio | ~0.24+ | Async test support | Required for testing async FastAPI endpoints, Motor queries, Kafka consumers. | HIGH |
| pytest-cov | ~6.0+ | Coverage reporting | Coverage is essential for OSS credibility and CI gates. | HIGH |
| Faker | ~33+ | Test data generation | Generate realistic test data for streams, metrics, insights. | HIGH |
| testcontainers | ~4.8+ | Integration test containers | Spin up real MongoDB, Kafka in Docker for integration tests. Better than mocking for integration tests. | MEDIUM |
| respx | ~0.22+ | HTTP mocking | Mock httpx requests. Use for testing GitHub webhook handlers and API calls without hitting real endpoints. | MEDIUM |
| httpx (TestClient) | (included) | API testing | FastAPI's TestClient built on httpx. Test API endpoints without running a server. | HIGH |

### Code Quality & Developer Experience

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Ruff | ~0.8+ | Linter + formatter | Replaces flake8, black, isort, pyflakes, and more. Written in Rust, extremely fast. Single tool for linting and formatting. | HIGH |
| mypy | ~1.13+ | Static type checking | Essential for a DDD codebase where domain types must be correct. Use strict mode. | HIGH |
| pre-commit | ~4.0+ | Git hooks | Run ruff, mypy, and tests before commits. Keeps codebase clean. | HIGH |

### Observability & Logging

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| structlog | ~24.4+ | Structured logging | JSON-structured logs with context binding. Essential for correlating events across services. Use with stdlib logging and `structlog.contextvars` for async-safe context. | HIGH |
| OpenTelemetry Python | ~1.28+ | Tracing & metrics | Vendor-neutral observability. Traces requests across services via Kafka headers. Export to Jaeger/OTLP in local dev. Add in later phases, not MVP. | MEDIUM |

### Task Scheduling

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| APScheduler | ~3.10+ | Scheduled tasks | For scheduled/deterministic investigators (daily reports, periodic metric recalculation). Lightweight, in-process scheduler. | HIGH |

**Why NOT Celery:** Celery adds Redis/RabbitMQ dependency and significant complexity. You already have Kafka for async messaging. APScheduler handles cron-like scheduling in-process. For distributed task execution, publish to Kafka topics instead.

### Containerization

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Docker | latest | Container runtime | Already decided. Use multi-stage builds for small images. | HIGH |
| Docker Compose | v2 | Local orchestration | Already decided. Define all services (core, connector, channel, mongo, kafka) in one file. | HIGH |

### Security & Secrets

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| cryptography | ~43+ | Encryption | Encrypt stored API tokens (GitHub, Slack, LLM keys) at rest. Use Fernet symmetric encryption with a master key from env. | HIGH |

### Dependency Injection

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| dependency-injector | ~4.42+ | DI container | Wires hexagonal architecture ports to adapters. Explicit dependency graph, supports async. Alternative: manual DI with FastAPI's `Depends()`. | MEDIUM |

**Manual DI alternative:** For a 3-person team, FastAPI's built-in `Depends()` may suffice without a full DI framework. Start with manual wiring; adopt dependency-injector if wiring becomes complex.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Web Framework | FastAPI | Django | Django's ORM is wasted with MongoDB; Django's sync-first model adds complexity for async Kafka consumers |
| Web Framework | FastAPI | Litestar | Newer, smaller community. FastAPI is the safer ecosystem choice. |
| Kafka Client | confluent-kafka | aiokafka | Pure Python, slower, less reliable under load. confluent-kafka wraps battle-tested librdkafka. |
| MongoDB Driver | Motor + PyMongo | MongoEngine | MongoEngine is Django-era, not async, and adds heavy ORM overhead. Motor is lighter and async-native. |
| MongoDB ODM | Beanie (optional) | ODMantic | Beanie has more adoption and is Pydantic v2 native. But both are optional -- raw Motor may suffice. |
| Package Manager | uv | Poetry | Poetry is slower, more complex dependency resolution. uv is the clear direction for new Python projects in 2025+. |
| Linter | Ruff | flake8 + black + isort | Three tools vs one. Ruff is faster and replaces all of them. |
| Scheduler | APScheduler | Celery | Celery adds broker dependency (Redis/RabbitMQ). Overkill when you already have Kafka for async work. |
| HTTP Client | httpx | requests | requests is sync-only. httpx supports both sync and async with the same API. |
| LLM Abstraction | ADK + LiteLLM | LangChain | LangChain adds massive dependency tree and abstraction overhead. ADK is focused on agent patterns. LiteLLM is lightweight for multi-provider BYOK. |
| Agent Framework | Google ADK | CrewAI / AutoGen | ADK already decided. CrewAI/AutoGen are multi-agent orchestration; ADK is lower-level giving more control. |

## Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Initialize project
uv init stackstitch
cd stackstitch

# Core dependencies
uv add fastapi uvicorn pydantic pydantic-settings
uv add motor pymongo
uv add confluent-kafka
uv add google-adk
uv add slack-bolt slack-sdk
uv add httpx
uv add pygithub
uv add structlog
uv add apscheduler
uv add cryptography
uv add litellm

# Dev dependencies
uv add --dev pytest pytest-asyncio pytest-cov
uv add --dev faker respx testcontainers
uv add --dev ruff mypy pre-commit

# Optional (add when needed)
# uv add beanie                           # ODM layer if raw Motor becomes cumbersome
# uv add --dev opentelemetry-api opentelemetry-sdk  # Observability (later phases)
```

## Key Configuration Patterns

### Kafka Consumer with Async Bridge

confluent-kafka is not natively async. Run consumer in a background thread:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from confluent_kafka import Consumer

async def run_kafka_consumer(topic: str, handler):
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)
    consumer = Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'core-service',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,  # CRITICAL: manual commits only
    })
    consumer.subscribe([topic])

    def _poll():
        while True:
            msg = consumer.poll(1.0)
            if msg is not None and not msg.error():
                return msg

    while True:
        msg = await loop.run_in_executor(executor, _poll)
        await handler(msg)
        consumer.commit(msg)  # Commit AFTER successful processing
```

### Pydantic Settings for Service Config

```python
from pydantic_settings import BaseSettings

class CoreSettings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "stackstitch"
    kafka_bootstrap_servers: str = "localhost:9092"
    log_level: str = "INFO"
    llm_api_key: str = ""  # BYOK: user provides their own

    model_config = {"env_prefix": "STACKSTITCH_", "env_file": ".env"}
```

## Version Verification Needed

These versions should be verified before locking dependencies:

| Package | Stated Version | Verify Command | Priority |
|---------|---------------|----------------|----------|
| google-adk | ~1.x | `pip index versions google-adk` | HIGH -- fast-moving, API may have changed |
| litellm | ~1.55+ | `pip index versions litellm` | HIGH -- fast-moving |
| confluent-kafka | ~2.6+ | `pip index versions confluent-kafka` | MEDIUM |
| motor | ~3.6+ | `pip index versions motor` | MEDIUM |
| fastapi | ~0.115+ | `pip index versions fastapi` | LOW -- stable API |
| pydantic | ~2.10+ | `pip index versions pydantic` | LOW -- stable API |
| slack-bolt | ~1.21+ | `pip index versions slack-bolt` | LOW -- stable API |

## Sources

- Training data knowledge (cutoff ~May 2025) for all library recommendations
- Project constraints from `.planning/PROJECT.md`
- Web verification was unavailable during this research session -- all versions marked with `~` prefix should be verified before dependency lock
