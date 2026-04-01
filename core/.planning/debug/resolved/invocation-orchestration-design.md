---
status: resolved
trigger: "The Orchestrate use case and Invocation entity appear designed only for user-message flow. Need to verify they handle anomaly insights, investigation results, and all trigger sources correctly."
created: 2026-03-31T00:00:00Z
updated: 2026-03-31T00:01:00Z
---

## Current Focus

hypothesis: Fix applied -- separated trigger_ref from delivery target, added broadcast logic for anomaly insights, added thread_id to InsightCreated event
test: All 123 tests passing, 13 RunInvestigation tests (8 new) covering broadcast, targeted, no-threads, cross-project isolation, event thread_id, trigger_ref separation
expecting: User confirms the fix addresses all three flows correctly
next_action: Await human verification

## Symptoms

expected:
- Invocations should support multiple trigger sources: user messages, anomaly-detected insights, investigation-generated insights
- The Orchestrate use case should handle all invocation types appropriately
- The Invocation entity should model the relationship between trigger source and expected action

actual:
- Invocation and Orchestrate appear designed primarily for the "user message -> agent response" flow
- Unclear how anomaly-detected insights create invocations or get delivered
- Unclear how investigation results flow back through the orchestration layer

errors: No runtime errors -- this is a design review and architectural correction.

reproduction: Read all files related to invocations, orchestration, investigations, insights, and the monitor_metric flow.

started: Original phase 1 design. Needs review before building adapters in phase 2.

## Eliminated

- hypothesis: "Orchestrate is only designed for user messages"
  evidence: The drain loop is source-agnostic -- it processes ANY pending Invocation regardless of source. Tests confirm it handles both USER_MESSAGE and INSIGHT sources in the same batch (test_drain_loop_processes_pending_invocations). The SpawningAgent test proves the drain loop correctly handles mid-loop Invocation creation. The design is intentionally generic.
  timestamp: 2026-03-31T00:01:00Z

- hypothesis: "Investigation results don't flow back through orchestration"
  evidence: RunInvestigation.execute() explicitly creates an Invocation(source=INSIGHT) after producing an Insight (line 79-86). Per D-66, InsightCreated event triggers Orchestrate. The Agent-initiated investigation flow works because the Agent calls RunInvestigation as a tool mid-drain-loop, the new INSIGHT Invocation is picked up in the next while-loop iteration.
  timestamp: 2026-03-31T00:01:00Z

## Evidence

- timestamp: 2026-03-31T00:00:10Z
  checked: Flow 1 -- User message (ad-hoc question) end-to-end
  found: COMPLETE. HandleMessage creates Thread + USER_MESSAGE Invocation -> MessageCreated triggers Orchestrate -> drain loop passes invocations to Agent -> Agent can call RunInvestigation as tool (D-34) -> new INSIGHT Invocation created -> picked up in next drain loop iteration -> final response delivered via MessageDeliverer.
  implication: The user-message flow is fully designed and works correctly.

- timestamp: 2026-03-31T00:00:20Z
  checked: Flow 2 -- Anomaly detection (proactive alert) end-to-end
  found: BROKEN at step 3. The flow: MonitorMetric emits AnomalyDetected -> (per D-64) RunInvestigation reacts -> creates Investigation + Insight + Invocation. BUT: RunInvestigation uses `trigger_ref` as `thread_id` for the Invocation (line 80). For anomaly-triggered investigations, there is NO pre-existing Thread. The AnomalyDetected event has no thread_id. Whatever UUID is passed as trigger_ref gets used as thread_id, but no Thread with that ID exists. Orchestrate.execute() would find no Thread and return immediately (line 35-36: `if thread is None: return`).
  implication: Proactive alerts from anomaly detection CANNOT reach the user. This is the critical gap.

- timestamp: 2026-03-31T00:00:30Z
  checked: RunInvestigation.trigger_ref semantics
  found: trigger_ref is overloaded -- for ADHOC investigations it's the thread_id (the conversation where the user asked), for ANOMALY investigations it would be... what? The metric ID? There's no Metric.id (metrics use composite keys per D-20). The AnomalyDetected event has no UUID field at all. The Investigation entity stores trigger_ref as a UUID, but the anomaly flow has no natural UUID to use.
  implication: trigger_ref has an identity crisis for the anomaly flow. It can't be both "thread to deliver to" and "thing that triggered the investigation."

- timestamp: 2026-03-31T00:00:40Z
  checked: InsightCreated event payload
  found: InsightCreated has insight_id, investigation_id, project_id. It does NOT have a thread_id. Per D-66, this event should trigger Orchestrate, but Orchestrate.execute() requires a thread_id parameter. The event subscriber (adapter) would need to know which thread_id to pass, but that information is buried inside the Invocation created by RunInvestigation.
  implication: The event-to-Orchestrate wiring for InsightCreated is possible but fragile -- the subscriber would need to query the Invocation to find the thread_id, or the event needs to carry it.

- timestamp: 2026-03-31T00:00:50Z
  checked: Orchestrate behavior with INSIGHT-source invocations
  found: Orchestrate is source-agnostic. It calls Agent.process(thread, invocations) regardless of source. The Agent receives the invocations and can see their source/role/message. For an INSIGHT invocation with message="New insight: {title}", the Agent would format and deliver it. This part works IF the Thread exists and contains appropriate context.
  implication: The Orchestrate drain loop itself is fine. The problem is upstream -- how to create/find the Thread for proactive flows.

- timestamp: 2026-03-31T00:01:00Z
  checked: MonitorMetric event output vs RunInvestigation input requirements
  found: MonitorMetric.execute() publishes AnomalyDetected(metric_type, project_id, severity, description, metric_value, threshold). RunInvestigation.execute() expects (project_id, trigger, trigger_ref, query). The adapter subscribing to AnomalyDetected would need to synthesize a trigger_ref UUID and decide what thread to associate with. There is no use case or entity that handles "create a new proactive thread for anomaly delivery."
  implication: Missing use case or logic for creating proactive delivery threads.

## Resolution

root_cause: |
  The design has one critical gap and two minor issues:

  **CRITICAL: No proactive delivery path for anomaly-detected insights.**
  The anomaly flow (MonitorMetric -> AnomalyDetected -> RunInvestigation -> Insight -> Invocation -> Orchestrate -> deliver) breaks because:
  1. There is no Thread for proactive alerts. Threads are only created by HandleMessage when a user sends a message.
  2. RunInvestigation uses trigger_ref as thread_id for the Invocation, but anomaly-triggered investigations have no natural thread_id.
  3. Orchestrate.execute(thread_id) returns immediately if no Thread exists.
  4. No use case creates a "proactive alert thread" for system-initiated communications.

  **MINOR ISSUE 1: trigger_ref is semantically overloaded.**
  For ADHOC investigations, trigger_ref = the thread_id where the user asked the question.
  For ANOMALY investigations, trigger_ref should reference the anomaly/metric, but is forced into the thread_id role.
  This conflation means the Investigation entity can't accurately record what triggered it while also knowing where to deliver results.

  **MINOR ISSUE 2: InsightCreated event lacks thread_id.**
  Per D-66, InsightCreated should trigger Orchestrate. But the event has no thread_id, so the adapter subscriber would need to query the Invocation repository to find the associated thread_id. This is workable but adds an implicit data dependency that isn't expressed in the event contract.

fix: |
  Option A implemented per user direction:

  1. **RunInvestigation** (`run_investigation.py`): Added optional `thread_id` parameter to `execute()`, separated from `trigger_ref`. Added `ThreadRepository` as a new dependency. New `_build_invocations()` method handles two modes:
     - Ad-hoc (thread_id provided): creates one Invocation for the specified thread
     - Anomaly (no thread_id): queries `ThreadRepository.get_by_project_id()` and creates one Invocation per existing project thread. If no threads exist, insight is stored but no invocations are created.

  2. **InsightCreated event** (`domain_events.py`): Added optional `thread_id: UUID | None = None` field. Set when insight targets a specific thread (ad-hoc), None when broadcast (anomaly).

  3. **Insight entity** (`insight.py`): Added optional `thread_id: UUID | None = None` field, passed through to InsightCreated event on construction.

  4. **ThreadRepository** (`repositories.py`): Added `get_by_project_id(project_id) -> list[Thread]` abstract method.

  5. **InMemoryThreadRepository** (`tests/fakes/repositories.py`): Implemented `get_by_project_id()` with in-memory filter.

  6. **Tests** (`test_run_investigation.py`): Rewrote with 13 tests (was 7). New tests cover: broadcast to all project threads, no-threads-no-invocations, cross-project thread isolation, InsightCreated event with/without thread_id, trigger_ref vs thread_id separation, insight stores thread_id.

verification: |
  - 123/123 tests pass (zero regressions)
  - 13 RunInvestigation tests pass (8 new, 5 updated)
  - Ruff and mypy warnings are all pre-existing (TC001/TC003/I001 pattern across entire codebase)

files_changed:
  - core/src/core/application/use_cases/run_investigation.py
  - core/src/core/domain/events/domain_events.py
  - core/src/core/domain/entities/insight.py
  - core/src/core/application/ports/repositories.py
  - core/tests/fakes/repositories.py
  - core/tests/use_cases/test_run_investigation.py
