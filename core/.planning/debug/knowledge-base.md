# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## invocation-orchestration-design — Proactive anomaly alert flow broken because trigger_ref was overloaded as delivery thread_id
- **Date:** 2026-03-31
- **Error patterns:** trigger_ref overloaded, no thread for proactive alerts, anomaly insight not delivered, InsightCreated missing thread_id, RunInvestigation uses trigger_ref as thread_id
- **Root cause:** RunInvestigation used trigger_ref as both "what triggered the investigation" and "which thread to deliver to". Anomaly-triggered investigations have no pre-existing thread, so invocations targeted non-existent threads and Orchestrate silently returned.
- **Fix:** Separated trigger_ref from delivery target by adding optional thread_id parameter to RunInvestigation. Anomaly insights (no thread_id) broadcast to all project threads via ThreadRepository.get_by_project_id(). InsightCreated event and Insight entity gained optional thread_id field.
- **Files changed:** run_investigation.py, domain_events.py, insight.py, repositories.py, tests/fakes/repositories.py, test_run_investigation.py
---

