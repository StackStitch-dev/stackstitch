---
phase: 02A
slug: docker-compose-mongodb-adapters
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 02A — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio 0.24+ |
| **Config file** | `core/pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `cd core && uv run pytest tests/integration/ -x -q` |
| **Full suite command** | `cd core && uv run pytest tests/ --cov=core --cov-report=term-missing` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd core && uv run pytest tests/integration/ -x -q`
- **After every plan wave:** Run `cd core && uv run pytest tests/ --cov=core --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02A-01-01 | 01 | 1 | INFR-01 | smoke (manual) | `docker compose up -d && docker compose ps` | N/A | ⬜ pending |
| 02A-02-01 | 02 | 2 | INFR-02 | integration | `cd core && uv run pytest tests/integration/test_stream_repository.py -x` | ❌ W0 | ⬜ pending |
| 02A-02-02 | 02 | 2 | INFR-02 | integration | `cd core && uv run pytest tests/integration/test_metric_repository.py -x` | ❌ W0 | ⬜ pending |
| 02A-02-03 | 02 | 2 | INFR-02 | integration | `cd core && uv run pytest tests/integration/test_insight_repository.py -x` | ❌ W0 | ⬜ pending |
| 02A-02-04 | 02 | 2 | INFR-02 | integration | `cd core && uv run pytest tests/integration/test_investigation_repository.py -x` | ❌ W0 | ⬜ pending |
| 02A-02-05 | 02 | 2 | INFR-02 | integration | `cd core && uv run pytest tests/integration/test_thread_repository.py -x` | ❌ W0 | ⬜ pending |
| 02A-02-06 | 02 | 2 | INFR-02 | integration | `cd core && uv run pytest tests/integration/test_invocation_repository.py -x` | ❌ W0 | ⬜ pending |
| 02A-03-01 | 03 | 2 | INFR-02 | integration | `cd core && uv run pytest tests/integration/test_health.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `core/tests/integration/__init__.py` — package init
- [ ] `core/tests/integration/conftest.py` — shared MongoDB container fixture (session-scoped)
- [ ] `core/tests/integration/test_stream_repository.py` — stubs for INFR-02
- [ ] `core/tests/integration/test_metric_repository.py` — stubs for INFR-02
- [ ] `core/tests/integration/test_insight_repository.py` — stubs for INFR-02
- [ ] `core/tests/integration/test_investigation_repository.py` — stubs for INFR-02
- [ ] `core/tests/integration/test_thread_repository.py` — stubs for INFR-02
- [ ] `core/tests/integration/test_invocation_repository.py` — stubs for INFR-02
- [ ] `core/tests/integration/test_health.py` — stubs for INFR-02
- [ ] Dependencies: `pymongo`, `fastapi`, `uvicorn`, `pydantic-settings`, `testcontainers[mongodb]`, `httpx`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker Compose starts all services | INFR-01 | Requires Docker daemon and compose orchestration | Run `docker compose up -d`, verify all containers healthy with `docker compose ps` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
