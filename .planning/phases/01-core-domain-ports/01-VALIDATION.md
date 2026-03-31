---
phase: 1
slug: core-domain-ports
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | `core/pyproject.toml` (Wave 0 — needs creation) |
| **Quick run command** | `cd core && uv run pytest tests/ -x -q` |
| **Full suite command** | `cd core && uv run pytest tests/ --cov=src/core --cov-report=term-missing` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd core && uv run pytest tests/ -x -q`
- **After every plan wave:** Run `cd core && uv run pytest tests/ --cov=src/core --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | INFR-05.1 | unit | `uv run pytest tests/domain/test_entities.py -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | INFR-05.2 | unit | `uv run pytest tests/domain/test_entities.py -x` + mypy | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | INFR-05.3 | unit | `uv run pytest tests/use_cases/ -x` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | INFR-05.4 | unit | `uv run pytest tests/ -x` | ❌ W0 | ⬜ pending |
| 01-01-05 | 01 | 1 | INFR-05.5 | smoke | `ls` verification | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `core/pyproject.toml` — project setup with dependencies (pydantic, pytest, pytest-asyncio, pytest-cov, ruff, mypy) and pytest config (`asyncio_mode = "auto"`)
- [ ] `core/src/core/__init__.py` — package init
- [ ] `core/tests/conftest.py` — shared fixtures with in-memory fakes
- [ ] `core/tests/fakes/` — all in-memory fake implementations
- [ ] ruff + mypy configuration in pyproject.toml

*Existing infrastructure covers none — this is the first phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Directory structure follows hexagonal layout | INFR-05.5 | Structural convention, not runtime behavior | Verify `core/domain/`, `core/application/ports/`, `core/application/use_cases/` directories exist |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
