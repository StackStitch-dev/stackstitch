# Domain Pitfalls

**Domain:** Engineering Operational Intelligence Platform
**Project:** StackStitch
**Researched:** 2026-03-27

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Kafka Consumer Offset Management Gone Wrong
**What goes wrong:** Messages are lost or processed multiple times because consumer offsets are committed before processing completes (or not committed at all).
**Why it happens:** Default `enable.auto.commit=true` in confluent-kafka commits offsets on a timer, not after successful processing. If the process crashes between commit and processing, messages are skipped.
**Consequences:** Metrics are wrong. Missing stream data points. Duplicate insights. Data integrity collapses silently.
**Prevention:** Disable `enable.auto.commit`. Manually commit offsets only after successful processing. Implement idempotent consumers (use event IDs to deduplicate).
**Detection:** Metrics don't match raw data counts. Gaps in time-series data. Compare stream counts with GitHub API counts.

### Pitfall 2: MongoDB Schema Drift Without Validation
**What goes wrong:** MongoDB's schema-free nature means different code paths write different shapes to the same collection. Over time, queries break on missing or unexpected fields.
**Why it happens:** "Schemaless" is treated as "no need to think about schema." No validation layer between domain models and MongoDB.
**Consequences:** Queries fail silently (missing fields return None). Aggregation pipelines produce wrong results. Debugging is painful because the data looks almost-right.
**Prevention:** Use Pydantic models as the serialization/deserialization layer for ALL MongoDB operations. Consider MongoDB schema validation (JSON Schema) on collections for defense in depth. Never write raw dicts.
**Detection:** Unexpected None values in query results. Aggregation pipeline errors. Data shape assertions in tests.

### Pitfall 3: Google ADK API Instability
**What goes wrong:** ADK is new (April 2025). APIs change between versions. Code written against one version breaks on update.
**Why it happens:** Fast-moving library in active development. Google's track record of breaking changes in developer tools.
**Consequences:** Investigator code breaks on dependency update. Blocked on upstream fixes. Team wastes time on migration instead of features.
**Prevention:** Pin ADK version strictly. Wrap ADK behind a port/interface (hexagonal architecture protects you here). Write integration tests that exercise actual ADK behavior. Keep adapter layer thin so you can swap to LangGraph or direct API calls if ADK stalls.
**Detection:** CI failures after dependency updates. Runtime errors in agent execution. Monitor ADK changelog before upgrading.

### Pitfall 4: LLM Cost Explosion from Naive Agent Loops
**What goes wrong:** AI investigators make too many LLM calls per investigation. Tool-use loops spiral: agent calls tool, processes result, calls another tool, repeat. Costs become unpredictable.
**Why it happens:** No limits on agent iterations. Passing entire raw datasets to LLM context. No caching of common queries. Agent system prompt too vague, causing the LLM to explore unnecessarily.
**Consequences:** Users get unexpectedly high LLM bills (undermines BYOK trust). Slow investigation response times. Users disable AI features.
**Prevention:** Set `max_iterations` on agents (3-5 per investigation). Summarize/aggregate data before passing to LLM (don't send 500 raw PRs). Cache common tool query results with short TTL. Implement token budget per investigation. Log token usage per insight for monitoring. Write specific system prompts that guide agents toward focused investigations.
**Detection:** Track `tokens_used` per insight. Dashboard/log alert on investigations exceeding budget. Weekly cost reports.

### Pitfall 5: Webhook Deduplication Failure
**What goes wrong:** GitHub sends the same webhook multiple times (retries on timeout). Without deduplication, the same PR event creates duplicate stream data points, inflating all downstream metrics.
**Why it happens:** GitHub retries webhooks that don't get a 2xx response within 10 seconds. Network issues cause duplicate deliveries. No idempotency check on ingestion.
**Consequences:** Inflated metrics (PR count doubled). Duplicate anomaly alerts. Users lose trust when numbers don't match GitHub.
**Prevention:** Store webhook delivery IDs (`X-GitHub-Delivery` header) in a dedup collection and reject duplicates. Use MongoDB unique indexes on `(source, external_id, event_type)`. Return 200 immediately before async processing (process via internal queue or Kafka).
**Detection:** Duplicate entries in stream collections. Metrics that don't match GitHub's own counts. Unique index violations in logs.

## Moderate Pitfalls

### Pitfall 6: Debounce Window Too Short or Too Long
**What goes wrong:** Too short = still recalculate N times per event burst. Too long = metrics feel stale, insights are delayed by minutes.
**Prevention:** Start with 5-second window for connectors, 10-second for calculators. Make configurable via environment variables. Log debounce hits vs emissions to tune.

### Pitfall 7: Blocking the FastAPI Event Loop
**What goes wrong:** Synchronous operations (confluent-kafka poll, heavy computation, synchronous PyMongo calls) block the asyncio event loop, making the API unresponsive.
**Prevention:** Run confluent-kafka consumer in a background thread (see STACK.md pattern). Use Motor (async) not PyMongo (sync) in async code paths. Use `asyncio.to_thread()` for CPU-bound work. Never call synchronous I/O in an async handler.

### Pitfall 8: Over-Engineered DDD for v1
**What goes wrong:** Team spends weeks designing perfect aggregates, value objects, domain services, and domain events before shipping anything. Analysis paralysis on "is this an entity or a value object?"
**Prevention:** Start with the happy path. Entities and use cases first. Add value objects and sophisticated domain events as complexity demands. A working system with pragmatic DDD is better than a theoretically perfect domain model with no features. Iterate the domain model as you learn from real data.

### Pitfall 9: Slack Rate Limits and Message Spam
**What goes wrong:** Burst of anomalies triggers many Slack messages simultaneously. Slack rate-limits the app (~1 msg/sec/channel). Messages are dropped or delayed. Users feel spammed.
**Prevention:** Implement a message queue with rate limiting for Slack. Batch related anomalies into a single message when possible (e.g., "3 anomalies detected in the last hour: ..."). Use threads for detail and main channel messages for summaries only.

### Pitfall 10: Kafka Topic Proliferation
**What goes wrong:** Creating a topic per data type per source per project. Dozens of topics for a simple setup. Kafka overhead grows, monitoring becomes complex.
**Prevention:** Four core topics: `stream_updated`, `metric_updated`, `anomaly_detected`, `insight_created`. Differentiate by message content (event type, source fields), not by topic name. Partition by `project_id`.

### Pitfall 11: GitHub API Rate Limits for Polling/Backfill
**What goes wrong:** Backfill/polling operations hit GitHub's 5000 req/hour rate limit. Connector crashes, gets blocked, or silently stops fetching.
**Prevention:** Track remaining rate limit from `X-RateLimit-Remaining` response header. Implement exponential backoff with jitter. For initial backfill, use GraphQL to fetch more data per request. Prefer webhooks for real-time; polling only for backfill.

### Pitfall 12: Metric Time Window Alignment Issues
**What goes wrong:** Metrics computed in overlapping or misaligned time windows produce inconsistent aggregations. "Daily" metrics don't sum to "weekly" because windows don't align.
**Prevention:** Use fixed hourly windows as the base unit (e.g., 2026-03-27T14:00 to 2026-03-27T15:00). Daily = 24 hourly windows. Weekly = 7 daily aggregations. Never use sliding windows for stored metrics. UTC everywhere.

## Minor Pitfalls

### Pitfall 13: Docker Compose Resource Limits
**What goes wrong:** Kafka and MongoDB consume excessive memory in Docker Compose, slowing developer machines. Kafka with Zookeeper = 3 JVM processes.
**Prevention:** Set memory limits in Docker Compose (Kafka: 1GB, MongoDB: 512MB, Zookeeper: 256MB). Consider KRaft mode (Kafka without Zookeeper, available in Kafka 3.7+) to eliminate one container.

### Pitfall 14: Timezone Handling in Metrics
**What goes wrong:** Metrics aggregated by "day" use different timezones across data sources. "Today's" metrics include yesterday's data for some users.
**Prevention:** Store ALL timestamps in UTC. Convert to user timezone only at display time (Slack message formatting). Use UTC for all aggregation windows. Document this decision prominently.

### Pitfall 15: structlog Configuration Gotcha
**What goes wrong:** structlog not configured properly produces unreadable output or loses context between async calls.
**Prevention:** Configure structlog early in application startup. Use `structlog.contextvars` (not `structlog.threadlocal`) for async-safe context propagation. JSON formatting for production, colored console for development.

### Pitfall 16: Forgotten MongoDB Indexes
**What goes wrong:** Queries become slow as data grows because no indexes exist for common query patterns. Full collection scans on every metric calculation.
**Prevention:** Define indexes alongside collection creation in infrastructure setup code. Key indexes: `(project_id, timestamp)` on streams, `(metric_type, project_id, window_start)` on metric data points, `(project_id, created_at)` on insights. Use `explain()` to verify index usage.

### Pitfall 17: Docker Image Size Bloat
**What goes wrong:** Single-stage Docker builds produce 2GB+ images with build tools, dev dependencies, and cache files.
**Prevention:** Use multi-stage builds. Stage 1: install dependencies with uv. Stage 2: copy only installed packages and application code into slim Python image. Use `.dockerignore` aggressively.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Core domain setup | Over-engineering DDD (#8) | Ship entities + use cases first; add sophistication iteratively |
| Kafka integration | Offset management (#1), blocking event loop (#7) | Manual commits, background thread consumer |
| MongoDB setup | Schema drift (#2), forgotten indexes (#16) | Pydantic-only writes, indexes in setup code |
| GitHub connector | Webhook dedup (#5), rate limits (#11) | Delivery ID tracking, rate limit header monitoring |
| Metric calculators | Debounce tuning (#6), time windows (#12), timezone (#14) | Configurable windows, fixed hourly base, UTC everywhere |
| Anomaly detection | False positive storm -> Slack spam (#9) | Rate limit Slack, aggregate related anomalies |
| AI investigators | LLM cost (#4), ADK instability (#3) | Token budgets, ADK behind port interface |
| Slack channel | Rate limits (#9), message formatting | Outbound queue with throttling, Block Kit templates |
| Docker deployment | Resource limits (#13), image size (#17) | Memory caps, multi-stage builds |

## Sources

- Kafka consumer offset management: Confluent documentation
- GitHub webhook behavior: GitHub API documentation (webhooks, rate limits)
- MongoDB schema validation: MongoDB documentation
- Slack rate limits: Slack API documentation
- Google ADK maturity assessment: Based on release timeline (April 2025)
- General domain knowledge of engineering metrics platforms
