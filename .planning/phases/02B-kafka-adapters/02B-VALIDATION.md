---
phase: 02B
slug: kafka-adapters
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 02B — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio |
| **Config file** | `core/pyproject.toml` (pytest section) |
| **Quick run command** | `cd core && uv run pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `cd core && uv run pytest tests/ -v --timeout=120 --cov=src/core` |
| **Estimated runtime** | ~45 seconds (with testcontainers Kafka startup) |

---

## Sampling Rate

- **After every task commit:** Run `cd core && uv run pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `cd core && uv run pytest tests/ -v --timeout=120 --cov=src/core`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02B-01-01 | 01 | 1 | INFR-03 | unit | `cd core && uv run pytest tests/unit/infrastructure/adapters/kafka/ -x -q` | ❌ W0 | ⬜ pending |
| 02B-01-02 | 01 | 1 | INFR-03 | unit | `cd core && uv run pytest tests/unit/infrastructure/adapters/kafka/ -x -q` | ❌ W0 | ⬜ pending |
| 02B-02-01 | 02 | 2 | INFR-03 | integration | `cd core && uv run pytest tests/integration/kafka/ -x -q --timeout=120` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/infrastructure/adapters/kafka/` — directory for Kafka adapter unit tests
- [ ] `tests/integration/kafka/` — directory for Kafka integration tests
- [ ] `tests/integration/kafka/conftest.py` — Redpanda/Kafka testcontainer fixture (session-scoped)
- [ ] `confluent-kafka` and `testcontainers[kafka]` — dependencies in pyproject.toml

*Existing pytest infrastructure from Phase 1/2a covers framework and conftest patterns.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker Compose `core-consumer` service starts | INFR-03 | Requires running docker-compose up | `docker compose up core-consumer -d && docker compose logs core-consumer --tail=20` |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
