# Feature Landscape

**Domain:** Engineering Operational Intelligence Platform
**Researched:** 2026-03-27

## Table Stakes

Features users expect from an engineering intelligence tool. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| GitHub webhook ingestion (PRs, commits, reviews) | Core data source; without it, there is no data | Medium | Must handle webhook verification, deduplication, and rate limits |
| Normalized data stream storage | Raw data is useless without normalization | Medium | Standard format: type, source, project_id, timestamp, data |
| PR cycle time metrics | The most commonly requested engineering metric | Low | Time from PR open to merge. Foundational. |
| PR throughput / frequency metrics | Basic productivity signal | Low | PRs merged per time window |
| Review turnaround time | Key collaboration metric | Low | Time from review request to first review |
| Time-window aggregations | Users expect daily/weekly/monthly views | Medium | Hourly base, aggregatable upward |
| Slack notifications for anomalies | Core delivery mechanism; without proactive alerts the tool is passive | Medium | Must format clearly, not spam |
| Ad-hoc Slack queries | Users expect to ask questions and get answers | High | Requires agent with tool-use to query stores |
| Secure credential storage | Users must trust the tool with their API tokens | Low | Encrypt at rest, never log secrets |
| Docker Compose one-command setup | OSS users expect easy local deployment | Medium | Single `docker compose up` must work |

## Differentiators

Features that set StackStitch apart from dashboard-centric tools (LinearB, Jellyfish, Sleuth, Swarmia).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AI narrative insights (not just numbers) | Most tools show dashboards; StackStitch explains WHY metrics changed | High | Core differentiator. Investigators correlate across data sources and produce text. |
| Cross-source anomaly correlation | "PR cycle time spiked because there were 3 incidents this week" | High | Requires multi-source data correlation and LLM reasoning. Limited in v1 (GitHub only). |
| Recurring pattern detection | "This is the 3rd sprint where reviews slow down on Fridays" | High | Agents read past insights to detect patterns over time |
| BYOK (Bring Your Own Key) | No surprise AI bills; users control LLM costs | Low | Users provide their own API key. Removes billing complexity. |
| Scheduled narrative reports | Automated weekly summaries without asking | Medium | Deterministic investigators on cron schedules |
| Audit trail with correlation IDs | Full traceability from raw webhook to insight | Medium | Important for trust and debugging |
| Slack-native interaction (no dashboard) | Meet engineers where they already are | Medium | No context switching. Rich Block Kit messages. |

## Anti-Features

Features to explicitly NOT build in v1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Web dashboard / charts | Massive scope increase, competing with established tools (Grafana, LinearB) | Slack-only for v1. Rich Block Kit messages can display key data effectively. |
| Multi-user / org management | Complexity explosion (auth, permissions, tenancy) | Single-user, single-project. Enterprise features reserved for paid version. |
| Custom metric definitions | Exposes too much complexity to users early on | Ship sensible defaults. Make calculators extensible via code for contributors. |
| Real-time streaming dashboard | WebSocket infrastructure, frontend framework needed | Batch-computed metrics with scheduled delivery. Real-time adds little value for weekly trends. |
| OAuth social login | Auth infrastructure for a single-user tool is waste | API key or env-var based access. No login needed for v1. |
| Jira / Sentry / Calendar connectors | Each connector is significant work; dilutes v1 focus | Design the connector interface to be extensible. Implement GitHub only. Others post-v1. |
| Mobile app | Entirely different platform, zero leverage from core | Slack IS the mobile interface (users already have Slack mobile). |
| Token billing / usage metering | Business complexity that delays shipping | BYOK eliminates this entirely for OSS. |
| DORA metrics labeling | Contested, political -- "are we measuring the right thing?" debates | Compute the raw data (cycle time, frequency, etc.) without labeling them DORA. Let users interpret. |

## Feature Dependencies

```
Credential Store (gate for all external API calls)
  |
GitHub Webhook Ingestion
  -> Stream Normalization & Storage
    -> Metric Calculators (cycle time, throughput, review turnaround)
      -> Anomaly Detection
        -> AI Investigators (correlate data, explain anomalies)
          -> Insight Storage
            -> Slack Proactive Alerts (push insights to users)

Parallel track (after Metric Calculators exist):
  APScheduler -> Deterministic Investigators -> Insight Storage -> Slack Alerts

Independent (after Insight Storage exists):
  Ad-hoc Slack Queries (agent + tools to query any store)

Prerequisite for any LLM call:
  BYOK Configuration (load user's LLM API key)
```

## MVP Recommendation

**Prioritize (in order):**

1. **Credential store + BYOK config** -- gate for all external integrations and LLM calls
2. **GitHub webhook ingestion + stream normalization** -- the data foundation
3. **Metric calculators (cycle time, throughput, review turnaround)** -- first value signal
4. **Anomaly detection** -- identifies when something is worth investigating
5. **Deterministic investigators** (scheduled reports) -- first insight output, template-based, no LLM needed
6. **AI investigators** -- the core differentiator, requires everything above plus LLM
7. **Slack proactive alerts** -- delivers insights to users
8. **Ad-hoc Slack queries** -- interactive experience, the "wow" moment

**Defer to post-MVP:**
- **Recurring pattern detection:** Needs accumulated historical insights (weeks of data) before useful
- **Additional connectors (Jira, Sentry, Calendar):** Design the interface now, implement later
- **OpenTelemetry observability:** Nice to have but not blocking for single-user deployment

## Sources

- Project requirements from `.planning/PROJECT.md`
- Domain knowledge of engineering metrics platforms (LinearB, Jellyfish, Sleuth, Swarmia, Faros AI)
- Training data analysis of engineering intelligence tool feature sets
