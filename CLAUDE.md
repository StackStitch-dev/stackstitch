<!-- GSD:project-start source:PROJECT.md -->
## Project

**StackStitch**

An open-source AI operational intelligence engine that unifies data from engineering tools (GitHub, Jira, Sentry, Calendar, Slack), computes delivery metrics, detects anomalies, and generates context-aware narrative insights. Engineers interact with it through Slack — receiving proactive alerts when friction is detected, and asking ad-hoc questions that the system investigates across all connected data sources.

**Core Value:** Reduce engineering leaders' cognitive load by automatically correlating cross-platform data and surfacing actionable, narrative insights — so they spend time removing blockers, not searching for them.

### Constraints

- **Language:** Python — chosen for AI ecosystem compatibility (ADK, LLM libraries)
- **Architecture:** Domain Driven Design + Hexagonal Architecture for the Core
- **Database:** MongoDB — handles variable schema of operational data from diverse sources
- **Message Broker:** Kafka — guarantees ordered message processing between services
- **Agent Framework:** Google ADK — for implementing investigators and user-facing agent
- **Channel v1:** Slack only — other channels deferred
- **Connector v1:** GitHub only — others deferred
- **OSS scope:** Single user, single project, no login — everything inferred by default
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
### Agent Framework
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| google-adk | ~1.x | Agent framework | Already decided. Google's Agent Development Kit for building AI agents with tool-use patterns. Fits the investigator architecture where agents have tools to query stores. | LOW |
| google-genai | (ADK dep) | Gemini API client | ADK's underlying client for Gemini models. Supports function calling, structured output. | LOW |
| LiteLLM | ~1.55+ | LLM proxy (BYOK) | Since BYOK means supporting multiple LLM providers (not just Gemini), LiteLLM provides a unified interface to 100+ LLMs. Use alongside ADK for provider flexibility. | MEDIUM |
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
# Install uv (if not already installed)
# Initialize project
# Core dependencies
# Dev dependencies
# Optional (add when needed)
# uv add beanie                           # ODM layer if raw Motor becomes cumbersome
# uv add --dev opentelemetry-api opentelemetry-sdk  # Observability (later phases)
## Key Configuration Patterns
### Kafka Consumer with Async Bridge
### Pydantic Settings for Service Config
## Version Verification Needed
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
