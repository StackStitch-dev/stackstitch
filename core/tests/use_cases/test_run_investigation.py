"""Tests for RunInvestigation use case."""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.application.use_cases.run_investigation import RunInvestigation
from core.domain.entities.investigation import InvestigatorResult, InvestigationStep
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
)


@pytest.fixture
def use_case(
    investigation_repo: InMemoryInvestigationRepository,
    insight_repo: InMemoryInsightRepository,
    invocation_repo: InMemoryInvocationRepository,
    investigator: FakeInvestigator,
    event_publisher: InMemoryEventPublisher,
) -> RunInvestigation:
    return RunInvestigation(
        investigation_repo=investigation_repo,
        insight_repo=insight_repo,
        invocation_repo=invocation_repo,
        investigator=investigator,
        event_publisher=event_publisher,
    )


@pytest.mark.asyncio
async def test_creates_investigation_and_calls_investigator(
    use_case: RunInvestigation,
    investigator: FakeInvestigator,
) -> None:
    project_id = uuid4()
    trigger_ref = uuid4()

    await use_case.execute(
        project_id=project_id,
        trigger="anomaly",
        trigger_ref=trigger_ref,
        query="Why did cycle time spike?",
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

    insight = await use_case.execute(
        project_id=project_id,
        trigger="anomaly",
        trigger_ref=trigger_ref,
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

    insight = await use_case.execute(
        project_id=project_id,
        trigger="anomaly",
        trigger_ref=uuid4(),
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
async def test_emits_insight_created(
    use_case: RunInvestigation,
    event_publisher: InMemoryEventPublisher,
) -> None:
    project_id = uuid4()

    insight = await use_case.execute(
        project_id=project_id,
        trigger="anomaly",
        trigger_ref=uuid4(),
    )

    assert insight is not None
    assert len(event_publisher.events) == 1
    event = event_publisher.events[0]
    assert isinstance(event, InsightCreated)
    assert event.insight_id == insight.id
    assert event.project_id == project_id


@pytest.mark.asyncio
async def test_creates_invocation_for_insight(
    use_case: RunInvestigation,
    invocation_repo: InMemoryInvocationRepository,
) -> None:
    project_id = uuid4()
    trigger_ref = uuid4()

    await use_case.execute(
        project_id=project_id,
        trigger="anomaly",
        trigger_ref=trigger_ref,
    )

    invocations = list(invocation_repo._store.values())
    assert len(invocations) == 1
    inv = invocations[0]
    assert inv.source == InvocationSource.INSIGHT
    assert inv.project_id == project_id


@pytest.mark.asyncio
async def test_investigation_failure_persists_failed_state(
    investigation_repo: InMemoryInvestigationRepository,
    insight_repo: InMemoryInsightRepository,
    invocation_repo: InMemoryInvocationRepository,
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
        investigator=failing,
        event_publisher=event_publisher,
    )

    result = await use_case.execute(
        project_id=uuid4(),
        trigger="adhoc",
        trigger_ref=uuid4(),
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
    )

    assert insight is not None
    assert insight.insight_type == InsightType.AD_HOC_RESPONSE
