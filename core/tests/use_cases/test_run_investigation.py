"""Tests for RunInvestigation use case."""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.application.use_cases.run_investigation import RunInvestigation
from core.domain.entities.investigation import InvestigatorResult, InvestigationStep
from core.domain.entities.thread import Thread
from core.domain.enums import (
    InsightType,
    InvestigationStatus,
    InvestigationStepType,
    InvocationSource,
)
from core.domain.events.domain_events import InsightCreated
from tests.fakes.event_publisher import InMemoryEventPublisher
from tests.fakes.investigator import FakeInvestigator
from tests.fakes.repositories import (
    InMemoryInsightRepository,
    InMemoryInvocationRepository,
    InMemoryInvestigationRepository,
    InMemoryThreadRepository,
)


@pytest.fixture
def use_case(
    investigation_repo: InMemoryInvestigationRepository,
    insight_repo: InMemoryInsightRepository,
    invocation_repo: InMemoryInvocationRepository,
    thread_repo: InMemoryThreadRepository,
    investigator: FakeInvestigator,
    event_publisher: InMemoryEventPublisher,
) -> RunInvestigation:
    return RunInvestigation(
        investigation_repo=investigation_repo,
        insight_repo=insight_repo,
        invocation_repo=invocation_repo,
        thread_repo=thread_repo,
        investigator=investigator,
        event_publisher=event_publisher,
    )


# --- Core investigation behavior ---


@pytest.mark.asyncio
async def test_creates_investigation_and_calls_investigator(
    use_case: RunInvestigation,
    investigator: FakeInvestigator,
) -> None:
    project_id = uuid4()
    trigger_ref = uuid4()
    thread_id = uuid4()

    await use_case.execute(
        project_id=project_id,
        trigger="anomaly",
        trigger_ref=trigger_ref,
        query="Why did cycle time spike?",
        thread_id=thread_id,
    )

    assert len(investigator.calls) == 1
    investigation, context = investigator.calls[0]
    assert investigation.project_id == project_id
    assert investigation.query == "Why did cycle time spike?"


@pytest.mark.asyncio
async def test_creates_insight_from_result(
    use_case: RunInvestigation,
    insight_repo: InMemoryInsightRepository,
) -> None:
    project_id = uuid4()
    trigger_ref = uuid4()
    thread_id = uuid4()

    insight = await use_case.execute(
        project_id=project_id,
        trigger="anomaly",
        trigger_ref=trigger_ref,
        thread_id=thread_id,
    )

    assert insight is not None
    assert insight.narrative == "test findings"
    assert insight.insight_type == InsightType.ANOMALY_EXPLANATION


@pytest.mark.asyncio
async def test_persists_investigation_and_insight(
    use_case: RunInvestigation,
    investigation_repo: InMemoryInvestigationRepository,
    insight_repo: InMemoryInsightRepository,
) -> None:
    project_id = uuid4()
    thread_id = uuid4()

    insight = await use_case.execute(
        project_id=project_id,
        trigger="anomaly",
        trigger_ref=uuid4(),
        thread_id=thread_id,
    )

    assert insight is not None
    # Investigation is persisted
    assert len(investigation_repo._store) == 1
    investigation = list(investigation_repo._store.values())[0]
    assert investigation.status == InvestigationStatus.COMPLETED

    # Insight is persisted
    stored_insight = await insight_repo.get_by_id(insight.id)
    assert stored_insight is not None


@pytest.mark.asyncio
async def test_investigation_failure_persists_failed_state(
    investigation_repo: InMemoryInvestigationRepository,
    insight_repo: InMemoryInsightRepository,
    invocation_repo: InMemoryInvocationRepository,
    thread_repo: InMemoryThreadRepository,
    event_publisher: InMemoryEventPublisher,
) -> None:
    """If Investigator raises, Investigation is marked FAILED and persisted, no Insight created."""

    class FailingInvestigator(FakeInvestigator):
        async def investigate(self, investigation, context):
            raise RuntimeError("LLM unavailable")

    failing = FailingInvestigator(
        preset_result=InvestigatorResult(
            steps=[InvestigationStep(step_type=InvestigationStepType.REASONING, reasoning="x")],
            findings="",
            tokens_used=0,
        )
    )

    use_case = RunInvestigation(
        investigation_repo=investigation_repo,
        insight_repo=insight_repo,
        invocation_repo=invocation_repo,
        thread_repo=thread_repo,
        investigator=failing,
        event_publisher=event_publisher,
    )

    result = await use_case.execute(
        project_id=uuid4(),
        trigger="adhoc",
        trigger_ref=uuid4(),
        thread_id=uuid4(),
    )

    assert result is None
    assert len(investigation_repo._store) == 1
    investigation = list(investigation_repo._store.values())[0]
    assert investigation.status == InvestigationStatus.FAILED
    assert investigation.findings == "LLM unavailable"

    # No insight created
    assert len(insight_repo._store) == 0
    # No events emitted
    assert len(event_publisher.events) == 0


@pytest.mark.asyncio
async def test_adhoc_trigger_creates_ad_hoc_response_insight(
    use_case: RunInvestigation,
    insight_repo: InMemoryInsightRepository,
) -> None:
    insight = await use_case.execute(
        project_id=uuid4(),
        trigger="adhoc",
        trigger_ref=uuid4(),
        query="What happened last week?",
        thread_id=uuid4(),
    )

    assert insight is not None
    assert insight.insight_type == InsightType.AD_HOC_RESPONSE


# --- Ad-hoc invocation (targeted to one thread) ---


@pytest.mark.asyncio
async def test_adhoc_creates_single_invocation_for_thread(
    use_case: RunInvestigation,
    invocation_repo: InMemoryInvocationRepository,
) -> None:
    project_id = uuid4()
    thread_id = uuid4()

    await use_case.execute(
        project_id=project_id,
        trigger="adhoc",
        trigger_ref=uuid4(),
        thread_id=thread_id,
    )

    invocations = list(invocation_repo._store.values())
    assert len(invocations) == 1
    inv = invocations[0]
    assert inv.source == InvocationSource.INSIGHT
    assert inv.thread_id == thread_id
    assert inv.project_id == project_id


# --- Anomaly invocation (broadcast to all project threads) ---


@pytest.mark.asyncio
async def test_anomaly_broadcasts_to_all_project_threads(
    use_case: RunInvestigation,
    thread_repo: InMemoryThreadRepository,
    invocation_repo: InMemoryInvocationRepository,
) -> None:
    """Anomaly insight (no thread_id) creates one invocation per project thread."""
    project_id = uuid4()
    t1 = Thread(id=uuid4(), project_id=project_id)
    t2 = Thread(id=uuid4(), project_id=project_id)
    await thread_repo.save(t1)
    await thread_repo.save(t2)

    await use_case.execute(
        project_id=project_id,
        trigger="anomaly",
        trigger_ref=uuid4(),
        # no thread_id -- broadcast
    )

    invocations = list(invocation_repo._store.values())
    assert len(invocations) == 2
    thread_ids = {inv.thread_id for inv in invocations}
    assert thread_ids == {t1.id, t2.id}
    for inv in invocations:
        assert inv.source == InvocationSource.INSIGHT
        assert inv.project_id == project_id


@pytest.mark.asyncio
async def test_anomaly_no_threads_stores_insight_no_invocations(
    use_case: RunInvestigation,
    insight_repo: InMemoryInsightRepository,
    invocation_repo: InMemoryInvocationRepository,
) -> None:
    """Anomaly insight with no project threads: insight is stored, no invocations created."""
    project_id = uuid4()

    insight = await use_case.execute(
        project_id=project_id,
        trigger="anomaly",
        trigger_ref=uuid4(),
        # no thread_id, and no threads in repo
    )

    assert insight is not None
    stored = await insight_repo.get_by_id(insight.id)
    assert stored is not None

    invocations = list(invocation_repo._store.values())
    assert len(invocations) == 0


@pytest.mark.asyncio
async def test_anomaly_ignores_threads_from_other_projects(
    use_case: RunInvestigation,
    thread_repo: InMemoryThreadRepository,
    invocation_repo: InMemoryInvocationRepository,
) -> None:
    """Broadcast only targets threads belonging to the same project."""
    project_id = uuid4()
    other_project_id = uuid4()

    own_thread = Thread(id=uuid4(), project_id=project_id)
    other_thread = Thread(id=uuid4(), project_id=other_project_id)
    await thread_repo.save(own_thread)
    await thread_repo.save(other_thread)

    await use_case.execute(
        project_id=project_id,
        trigger="anomaly",
        trigger_ref=uuid4(),
    )

    invocations = list(invocation_repo._store.values())
    assert len(invocations) == 1
    assert invocations[0].thread_id == own_thread.id


# --- InsightCreated event ---


@pytest.mark.asyncio
async def test_emits_insight_created_with_thread_id_for_adhoc(
    use_case: RunInvestigation,
    event_publisher: InMemoryEventPublisher,
) -> None:
    thread_id = uuid4()
    project_id = uuid4()

    insight = await use_case.execute(
        project_id=project_id,
        trigger="adhoc",
        trigger_ref=uuid4(),
        thread_id=thread_id,
    )

    assert insight is not None
    assert len(event_publisher.events) == 1
    event = event_publisher.events[0]
    assert isinstance(event, InsightCreated)
    assert event.insight_id == insight.id
    assert event.project_id == project_id
    assert event.thread_id == thread_id


@pytest.mark.asyncio
async def test_emits_insight_created_with_none_thread_id_for_anomaly(
    use_case: RunInvestigation,
    event_publisher: InMemoryEventPublisher,
) -> None:
    project_id = uuid4()

    insight = await use_case.execute(
        project_id=project_id,
        trigger="anomaly",
        trigger_ref=uuid4(),
        # no thread_id
    )

    assert insight is not None
    assert len(event_publisher.events) == 1
    event = event_publisher.events[0]
    assert isinstance(event, InsightCreated)
    assert event.thread_id is None


# --- trigger_ref is separate from thread_id ---


@pytest.mark.asyncio
async def test_trigger_ref_stored_on_investigation_not_used_as_thread_id(
    use_case: RunInvestigation,
    investigation_repo: InMemoryInvestigationRepository,
    invocation_repo: InMemoryInvocationRepository,
) -> None:
    """trigger_ref records what triggered the investigation; thread_id controls delivery."""
    project_id = uuid4()
    trigger_ref = uuid4()
    thread_id = uuid4()

    await use_case.execute(
        project_id=project_id,
        trigger="adhoc",
        trigger_ref=trigger_ref,
        thread_id=thread_id,
    )

    # trigger_ref is on the investigation
    investigation = list(investigation_repo._store.values())[0]
    assert investigation.trigger_ref == trigger_ref

    # thread_id is on the invocation (NOT trigger_ref)
    invocation = list(invocation_repo._store.values())[0]
    assert invocation.thread_id == thread_id
    assert invocation.thread_id != trigger_ref


@pytest.mark.asyncio
async def test_insight_stores_thread_id(
    use_case: RunInvestigation,
    insight_repo: InMemoryInsightRepository,
) -> None:
    thread_id = uuid4()

    insight = await use_case.execute(
        project_id=uuid4(),
        trigger="adhoc",
        trigger_ref=uuid4(),
        thread_id=thread_id,
    )

    assert insight is not None
    assert insight.thread_id == thread_id
