# Project Research Summary

**Project:** StackStitch
**Domain:** Engineering Operational Intelligence Platform
**Researched:** 2026-03-27
**Confidence:** MEDIUM

## Executive Summary

StackStitch is an engineering intelligence platform that ingests GitHub activity via webhooks, computes engineering metrics (cycle time, throughput, review turnaround), and delivers AI-generated narrative insights to engineers via Slack — without a web dashboard. Research confirms this is a well-understood domain with established patterns: a three-service async microservices architecture (Connector, Core, Channel), domain-driven design in the Core service, and Kafka as the event backbone. The key architectural insight is that the data pipeline must be async throughout — Kafka for all pipeline hops, HTTP only for request-response — and the Core service must use hexagonal architecture to isolate domain logic from MongoDB and the ADK agent framework. The competitive differentiation is clear: narrative AI insights rather than dashboards. Most competitors (LinearB, Jellyfish, Swarmia) are dashboard-centric. StackStitch's Slack-native, narrative-first approach is distinct and should be a deliberate product position, not treated as a deferral.

The recommended stack centers on FastAPI + Pydantic v2 + Motor for the service layer, confluent-kafka (wrapping librdkafka) for reliable Kafka consumption, Google ADK with LiteLLM for the investigator agent layer, and slack-bolt for Slack integration. The stack is internally consistent: all major libraries are async-native or have async bridges, and Pydantic v2 serves as the shared validation layer across the API, domain model, and MongoDB serialization. The only significant tooling uncertainty is Google ADK, released April 2025, whose API stability is unproven and whose agent/tool patterns documented in ARCHITECTURE.md are conceptual and require live-doc verification before implementation.

The three highest-risk areas are: (1) Kafka consumer offset management — disabling auto-commit and committing only after successful processing is non-negotiable for data integrity; (2) Google ADK instability — pin the version strictly and wrap it behind a hexagonal port from day one to allow swap-out if needed; and (3) LLM cost explosion from unbounded agent loops — set `max_iterations` on all investigators and log token usage per insight. The MVP is intentionally narrow: GitHub only, Slack only, single user, no dashboard. The architecture is designed to scale to 100 projects but v1 does not require that scale.

## Key Findings

### Recommended Stack

The stack is Python 3.12+ managed with `uv`, built around FastAPI as the API framework, Motor for async MongoDB access, and confluent-kafka for Kafka. Pydantic v2 serves triple duty as the data validation layer, settings manager (via pydantic-settings), and MongoDB serialization layer — never write raw dicts to MongoDB. Code quality is consolidated into a single tool (Ruff) replacing the traditional flake8 + black + isort trio, and mypy enforces type correctness across the DDD domain model. For the AI investigator layer, Google ADK is combined with LiteLLM to support BYOK across multiple LLM providers. APScheduler handles cron-style scheduled investigators without adding a Celery/Redis dependency.

**Core technologies:**
- **Python 3.12 + uv**: Runtime and package manager — 3.12 is stable with async/performance improvements; uv is 10-100x faster than pip and is the clear direction for new Python projects
- **FastAPI + Uvicorn**: HTTP API framework — async-native, OpenAPI auto-generation, essential for webhook endpoints and ad-hoc query HTTP interface
- **Pydantic v2 + pydantic-settings**: Validation, settings, DTOs — Rust-based rewrite, dramatically faster, foundational to all layers
- **Motor 3.x**: Async MongoDB driver — required for non-blocking DB access in async services; never use PyMongo directly in async code paths
- **confluent-kafka**: Kafka producer/consumer — wraps librdkafka (C), most reliable Python Kafka client; explicitly NOT aiokafka (pure Python, less reliable under load)
- **Google ADK + LiteLLM**: Agent framework + multi-provider LLM abstraction — ADK for agent/tool patterns, LiteLLM for BYOK support across providers
- **slack-bolt[async]**: Slack integration — official SDK, handles events, commands, interactivity, and Socket Mode
- **structlog**: Structured logging — JSON logs with async-safe context propagation via `contextvars`; use `structlog.contextvars`, not threadlocal
- **APScheduler**: Scheduled investigators — cron-style triggers without Celery/Redis overhead
- **cryptography (Fernet)**: Credential encryption at rest — encrypt all stored API tokens with master key from env
- **pytest + pytest-asyncio + testcontainers**: Testing — async test support, real MongoDB/Kafka containers for integration tests

**Version verification required before locking:** `google-adk` (~1.x) and `litellm` (~1.55+) are fast-moving; run `pip index versions <package>` before committing to any version. All versions in STACK.md are marked `~` and are estimates from training data cutoff ~May 2025.

### Expected Features

The feature dependency chain is strict: credential storage gates all external integrations, webhook ingestion provides the raw data, metric calculators produce the signal, anomaly detection identifies what is worth investigating, and AI investigators explain it. Missing any upstream element makes everything downstream useless.

**Must have (table stakes):**
- **GitHub webhook ingestion (PRs, commits, reviews)** — core data source; no data = no product
- **Normalized stream storage** — raw webhooks are useless without a standard format
- **PR cycle time, throughput, review turnaround metrics** — the three most-expected engineering metrics
- **Time-window aggregations (daily/weekly/monthly)** — users expect multiple views; base on hourly UTC windows
- **Slack notifications for anomalies** — proactive delivery; without it the tool is passive
- **Ad-hoc Slack queries** — users expect to ask questions and get answers; the "wow" moment
- **Secure credential storage (BYOK config)** — users must trust the tool with their API tokens
- **Docker Compose one-command setup** — OSS users will not install without this

**Should have (differentiators):**
- **AI narrative insights** — most tools show dashboards; StackStitch explains WHY metrics changed; this is the primary differentiator
- **Cross-source anomaly correlation** — links metric spikes to causal events across data sources
- **Scheduled narrative reports** — automated weekly summaries via APScheduler; no manual triggering needed
- **Audit trail with correlation IDs** — full traceability from raw webhook to insight; builds user trust
- **Recurring pattern detection** — agents read past insights to identify patterns over time (needs weeks of data first)

**Defer to v2+:**
- Additional connectors (Jira, Sentry, Calendar) — design the connector interface now; implement GitHub only
- Multi-user / org management — complexity explosion; reserve for paid version
- Web dashboard / charts — Slack Block Kit suffices for v1; dashboard competes with established tools
- Custom metric definitions — ship sensible defaults; make calculators extensible via code for contributors
- OpenTelemetry full observability — useful but not blocking for single-user v1 deployment
- DORA metrics labeling — contested; compute raw data and let users interpret

### Architecture Approach

Three independently deployable services communicate via four Kafka topics (`stream_updated`, `metric_updated`, `anomaly_detected`, `insight_created`), all partitioned by `project_id` for per-project ordering guarantees. The Core service implements hexagonal (ports and adapters) architecture with DDD entities, separating domain logic entirely from MongoDB, Kafka, and ADK infrastructure. Data flows one-way through Kafka for the main pipeline; HTTP is used only for ad-hoc query request-response. Each service owns its MongoDB collections exclusively — no cross-service DB reads.

**Major components:**
1. **Connector Service** — ingests GitHub webhooks, verifies HMAC signatures, deduplicates via delivery ID store, normalizes to standard stream format, publishes `stream_updated`
2. **Core Service (DDD/Hexagonal)** — consumes streams, computes metrics, detects anomalies, runs AI investigators, stores insights, publishes `insight_created`; structured as `domain/ → application/ports/ → infrastructure/adapters/`
3. **Channel Service** — consumes `insight_created`, formats Slack Block Kit messages, handles ad-hoc Slack queries via HTTP back to Core
4. **MongoDB** — persistent store; each service owns its collections exclusively; no cross-service DB reads
5. **Kafka** — async event bus; four topics; `project_id` partition key for ordering within a project

**Key patterns:**
- Hexagonal in Core: ports are interfaces (`MetricRepository`, `InsightRepository`, `EventPublisher`); adapters are infrastructure implementations
- Domain events carry IDs only, not full payloads — consumers fetch full data from their own store
- Debouncing at two levels: connector (5s window before emitting `stream_updated`) and calculator (10s window before emitting `metric_updated`)
- Investigators as ADK agents with tool-use, strictly bounded by `max_iterations=3-5`
- Correlation IDs from `X-GitHub-Delivery` header propagated through all Kafka message headers and structlog context

### Critical Pitfalls

1. **Kafka consumer offset management** — disable `enable.auto.commit`; commit offsets manually only after successful processing; implement idempotent consumers with event ID deduplication. Silent data loss without this.

2. **MongoDB schema drift** — all writes must go through Pydantic model serialization; never write raw dicts; add MongoDB JSON Schema validation on collections as defense-in-depth; define `(project_id, timestamp)` and `(metric_type, project_id, window_start)` indexes at setup time.

3. **Google ADK API instability** — pin version strictly from day one; wrap ADK entirely behind a hexagonal port interface; write adapter layer so thin that swapping to direct Gemini API calls or LangGraph is a one-file change.

4. **LLM cost explosion** — set `max_iterations=3-5` on all investigators; summarize/aggregate data before passing to LLM context (never send 500 raw PRs); log `tokens_used` per insight; implement per-investigation token budget.

5. **Webhook deduplication failure** — store `X-GitHub-Delivery` IDs in a dedup collection with MongoDB unique index; return HTTP 200 immediately and process async; use `(source, external_id, event_type)` unique index on stream collections.

## Implications for Roadmap

The feature dependency chain from FEATURES.md is the clearest signal for phase ordering: credentials gate everything, data ingestion enables metrics, metrics enable detection, detection enables AI investigation, and investigation output enables delivery. Architectural concerns (hexagonal setup, Kafka integration, debouncing) must be established early because they are foundational to every downstream phase.

### Phase 1: Foundation — Project Scaffold and Credential Store
**Rationale:** Nothing else can be built without the project scaffold, Docker Compose environment, and secure credential storage. Establishing the hexagonal architecture skeleton here prevents a painful refactor when investigators need to swap ADK versions or LLM providers.
**Delivers:** Running Docker Compose with all services (Kafka, MongoDB, Core/Connector/Channel stubs), pydantic-settings typed configuration per service, Fernet-encrypted credential store, hexagonal architecture directory structure in Core, CI with ruff + mypy + pytest.
**Addresses:** Secure credential storage, BYOK configuration, Docker Compose one-command setup (skeleton)
**Avoids:** Over-engineered DDD (Pitfall #8) — scaffold structure but implement only what's needed; DI complexity — start with FastAPI `Depends()` rather than dependency-injector

### Phase 2: GitHub Connector and Stream Normalization
**Rationale:** Data is the prerequisite for everything. Without ingested, normalized streams, no metrics can be computed and no agents have anything to investigate.
**Delivers:** GitHub webhook endpoint (FastAPI), HMAC signature verification, deduplication via delivery ID store with unique MongoDB index, normalization to standard stream format (`type`, `source`, `project_id`, `timestamp`, `data`), raw storage, `stream_updated` Kafka publication.
**Addresses:** GitHub webhook ingestion, normalized stream storage
**Avoids:** Webhook deduplication failure (Pitfall #5); blocking the async event loop (Pitfall #7) — confluent-kafka producer in background thread; GitHub rate limits (Pitfall #11) — track `X-RateLimit-Remaining` for any polling/backfill
**Research flag:** Verify current GitHub webhook event payload shapes for `pull_request`, `pull_request_review`, and `push` events before implementing the normalizer

### Phase 3: Metric Calculators
**Rationale:** Metrics are the first user-visible value signal and the input that drives all downstream detection and investigation. Time-window alignment strategy must be locked here — changing it later breaks all historical data.
**Delivers:** PR cycle time, PR throughput, and review turnaround calculators; UTC hourly base windows; daily/weekly aggregations; debouncing at calculator level (10s configurable window); `metric_updated` Kafka publication; `(metric_type, project_id, window_start)` MongoDB indexes.
**Addresses:** Cycle time, throughput, review turnaround metrics, time-window aggregations
**Avoids:** Metric time window alignment issues (Pitfall #12) — hourly base unit, UTC everywhere; timezone drift (Pitfall #14) — UTC storage, display-time conversion only; forgotten indexes (Pitfall #16) — define at setup; debounce too short/long (Pitfall #6) — start at 10s, make env-configurable

### Phase 4: Anomaly Detection
**Rationale:** Anomaly detection is the bridge between raw metrics and actionable intelligence. It must exist before the AI investigator layer, which is triggered by anomaly events.
**Delivers:** Statistical threshold evaluation per metric type (Z-score or percentile baseline), configurable sensitivity per project, `anomaly_detected` Kafka publication, anomaly batching logic to prevent downstream Slack spam.
**Addresses:** The detection step that triggers AI investigation; configurable thresholds for false positive control
**Avoids:** Slack spam from false positive storms (Pitfall #9) — batch related anomalies before they reach the delivery layer

### Phase 5: AI Investigators
**Rationale:** This is the core differentiator. It requires functional metrics, anomaly detection, and the hexagonal ADK port to be in place before implementation. The highest-risk phase due to ADK instability — approach with the hexagonal port in place before writing any agent code.
**Delivers:** ADK investigator agents with tool-use (`query_metrics`, `query_streams`, `query_past_insights` tools), deterministic (template-based) scheduled investigators via APScheduler, AI (LLM-powered) investigators triggered by `anomaly_detected`, insight storage, `insight_created` Kafka publication, per-investigation token budget logging.
**Addresses:** AI narrative insights, anomaly correlation, scheduled narrative reports, BYOK LLM usage
**Avoids:** ADK instability (Pitfall #3) — wrap behind port, pin version, keep adapter thin; LLM cost explosion (Pitfall #4) — max_iterations=3-5, aggregate data before context, log tokens_used per insight
**Research flag (HIGH PRIORITY):** Google ADK API must be verified against live documentation before writing any investigator code. The `Agent`, `Tool`, `max_iterations`, and session management APIs in ARCHITECTURE.md are conceptual. Also verify LiteLLM's BYOK key-injection interface for multi-provider support.

### Phase 6: Slack Channel and Delivery
**Rationale:** Insight delivery closes the loop. With insights being generated, this phase makes the system tangibly useful. Ad-hoc queries complete the interactive experience.
**Delivers:** Slack Block Kit message formatting for insights, proactive alert delivery consuming `insight_created`, outbound message queue with rate limiting (1 msg/sec/channel), threaded message model (summaries in channel, detail in threads), ad-hoc Slack query handler routed via HTTP to Core.
**Addresses:** Slack notifications for anomalies, ad-hoc Slack queries, Slack-native interaction
**Avoids:** Slack rate limits and message spam (Pitfall #9) — outbound queue with throttling, batch related anomalies into single message
**Research flag:** Confirm Socket Mode vs. Events API choice for local dev (Socket Mode requires no public URL; Events API requires HTTPS); verify current Block Kit block types available for structured metric display

### Phase 7: Production Hardening and OSS Polish
**Rationale:** Before any real-world or OSS usage, the system needs Docker image optimization, integration test coverage, and setup documentation.
**Delivers:** Multi-stage Docker builds for all services (target <200MB images), `.dockerignore`, Kafka memory caps (1GB) and MongoDB memory caps (512MB) in Docker Compose, MongoDB index verification script, integration test suite with testcontainers, structlog JSON configuration for production / colored for dev, README with first-run instructions.
**Addresses:** Docker Compose one-command setup (completeness), OSS credibility, observability baseline
**Avoids:** Docker image size bloat (Pitfall #17) — multi-stage builds; Docker resource limits (Pitfall #13) — memory caps, KRaft mode for Zookeeper elimination; structlog misconfiguration (Pitfall #15)

### Phase Ordering Rationale

- **Credentials before data:** GitHub, Slack, and LLM API keys must be stored securely before any external call is made from any service.
- **Hexagonal skeleton in Phase 1:** Establishing ports and adapters early prevents a costly refactor when investigators need to swap between ADK versions or LLM providers.
- **Data ingestion before computation:** Metric calculators need normalized streams; investigators need metrics; delivery needs insights. The dependency chain is strict and directional.
- **Anomaly detection before AI investigators:** Investigators are triggered by `anomaly_detected` events; building investigators without the trigger means relying entirely on synthetic test fixtures.
- **Debouncing in Phases 2 and 3:** Both debounce levels (connector and calculator) must be in place before any load testing or production data, or metrics will be inflated.
- **Delivery last:** Slack delivery is the user-facing end of the pipeline; it is most meaningful to implement after the full pipeline produces real insights.

### Research Flags

Phases needing deeper research during planning:
- **Phase 2 (GitHub Connector):** Verify current GitHub webhook event payloads — field names and nesting for `pull_request`, `pull_request_review`, and `push` events matter for normalization correctness
- **Phase 5 (AI Investigators):** HIGH PRIORITY. Google ADK API surface is the most significant unknown in the entire project. Verify `Agent`, `Tool`, `max_iterations`, session management, and async execution patterns against live docs before writing investigator code. Also verify LiteLLM BYOK key injection pattern.
- **Phase 6 (Slack Channel):** Confirm Socket Mode vs. Events API decision; verify Block Kit blocks available for metric display tables and trend indicators

Phases with standard patterns (research likely skippable):
- **Phase 1 (Foundation):** uv, FastAPI, pydantic-settings, Docker Compose, and Fernet patterns are well-documented and stable
- **Phase 3 (Metric Calculators):** Time-series windowing, UTC alignment, and APScheduler are mature with extensive documentation
- **Phase 4 (Anomaly Detection):** Statistical threshold detection (Z-score, percentile baseline) is standard; no novel patterns required
- **Phase 7 (Hardening):** Multi-stage Docker, Ruff, mypy, pre-commit, and testcontainers patterns are mature

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (core: FastAPI, Pydantic, Motor, confluent-kafka, Ruff, structlog) | HIGH | Well-established libraries with stable APIs. Version numbers need `pip index versions` verification but the choices are sound. |
| Stack (ADK, LiteLLM) | LOW | Fast-moving libraries. ADK released April 2025. Both need live-doc verification before Phase 5. API surfaces may have changed significantly from training data. |
| Features | HIGH | Domain knowledge is strong; feature set is well-validated against known competitors (LinearB, Jellyfish, Swarmia, Faros AI). Dependency chain is clear and internally consistent. |
| Architecture | HIGH | DDD + Hexagonal + Kafka event-driven patterns are drawn from canonical sources (Evans, Vernon, Confluent docs). Data flow and topic design are sound for v1 scope. |
| Pitfalls | HIGH | Pitfalls are based on fundamental infrastructure behavior (Kafka offsets, webhook retry behavior, MongoDB schema freedom, Slack rate limits) that is stable and well-documented. ADK instability assessment is grounded in release timeline. |

**Overall confidence:** MEDIUM — elevated to HIGH for all phases except Phase 5 (AI Investigators), which depends on ADK and LiteLLM API verification.

### Gaps to Address

- **Google ADK current API surface:** The investigator patterns in ARCHITECTURE.md are explicitly conceptual. The actual `Agent`, `Tool` decorator, `max_iterations`, and session management APIs must be verified against live ADK documentation before Phase 5 begins. If the API has changed significantly, the investigator adapter design will need revision.

- **LiteLLM BYOK injection pattern:** How LiteLLM routes calls to user-supplied API keys (vs. a centrally managed key) needs validation. The BYOK use case may require non-obvious LiteLLM configuration for per-request key injection.

- **Slack Socket Mode vs. Events API decision:** The Channel Service needs a firm decision before Phase 6. Socket Mode is simpler for local dev (no public HTTPS required); Events API is production-grade but complicates Docker Compose networking. This decision should be made during Phase 6 planning.

- **Kafka KRaft vs. Zookeeper in Docker Compose:** STACK.md recommends KRaft mode (Kafka 3.7+, no Zookeeper) to eliminate the 3-JVM-process overhead on developer machines. Confirm KRaft availability in the target `confluentinc/cp-kafka` Docker image before Phase 1 Docker Compose setup.

- **MongoDB schema evolution strategy:** The architecture specifies Pydantic-only writes, but has no versioning strategy for field additions or renames across service deployments. This is acceptable for v1 single-user but should be addressed before any multi-user or production deployment.

- **Competitor feature drift (2025-2026):** LinearB, Swarmia, and others may have shipped AI narrative features in late 2025 or early 2026, changing the differentiation landscape. The narrative-insight differentiator should be validated against current competitor feature sets before investing heavily in the AI layer.

## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md` — project requirements, constraints, and architectural decisions
- Confluent Kafka documentation — offset management, consumer group patterns, KRaft mode, topic design
- MongoDB documentation — schema validation, index patterns, aggregation pipelines
- Eric Evans, *Domain-Driven Design* — entity, aggregate, value object, and domain event patterns
- Alistair Cockburn — hexagonal architecture (ports and adapters)
- Slack API documentation — rate limits (1 msg/sec/channel), Block Kit, bolt-python, Socket Mode

### Secondary (MEDIUM confidence)
- FastAPI, Pydantic v2, Motor, pytest, structlog, APScheduler — training data (cutoff ~May 2025), stable and widely-documented APIs
- confluent-kafka Python client — librdkafka documentation and community usage patterns
- GitHub Webhooks documentation — delivery headers (`X-GitHub-Delivery`), retry behavior, HMAC verification, rate limits
- Engineering metrics domain knowledge — LinearB, Jellyfish, Swarmia, Faros AI feature analysis

### Tertiary (LOW confidence)
- Google ADK (~1.x) — released April 2025; training data knowledge only; verify before Phase 5
- LiteLLM (~1.55+) — fast-moving; training data knowledge only; verify before Phase 5
- All `~` version numbers in STACK.md — web search was unavailable during research; treat all versions as estimates requiring `pip index versions` verification before dependency lock

---
*Research completed: 2026-03-27*
*Ready for roadmap: yes*
