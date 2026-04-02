from __future__ import annotations

from uuid import uuid4

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from core.domain.entities.investigation import Investigation, InvestigationStep, InvestigatorResult
from core.domain.enums import (
    InvestigationStatus,
    InvestigationStepType,
    InvestigationTrigger,
)
from core.infrastructure.adapters.mongodb.investigation_repository import (
    MongoInvestigationRepository,
)


@pytest.fixture
def repo(mongo_db: AsyncDatabase) -> MongoInvestigationRepository:
    return MongoInvestigationRepository(mongo_db)


def _make_investigation(**overrides) -> Investigation:
    defaults = {
        "project_id": uuid4(),
        "trigger": InvestigationTrigger.ANOMALY,
        "trigger_ref": uuid4(),
    }
    defaults.update(overrides)
    return Investigation(**defaults)


@pytest.mark.asyncio
async def test_save_and_get_by_id(repo: MongoInvestigationRepository) -> None:
    inv = _make_investigation(query="Why is cycle time high?")
    await repo.save(inv)

    loaded = await repo.get_by_id(inv.id)
    assert loaded is not None
    assert loaded.id == inv.id
    assert loaded.project_id == inv.project_id
    assert loaded.trigger == inv.trigger
    assert loaded.trigger_ref == inv.trigger_ref
    assert loaded.query == "Why is cycle time high?"
    assert loaded.status == InvestigationStatus.PENDING
    assert loaded.steps == []
    assert loaded.findings is None
    assert loaded.tokens_used == 0
    assert loaded.created_at == inv.created_at


@pytest.mark.asyncio
async def test_get_by_id_not_found(repo: MongoInvestigationRepository) -> None:
    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_save_with_steps_embedded(repo: MongoInvestigationRepository) -> None:
    step1 = InvestigationStep(
        step_type=InvestigationStepType.TOOL_CALL,
        tool_name="query_metrics",
        input_data={"metric": "pr_cycle_time"},
        output_data={"value": 42.5},
        reasoning="Checking cycle time metric",
        tokens_used=100,
    )
    step2 = InvestigationStep(
        step_type=InvestigationStepType.REASONING,
        reasoning="Cycle time is elevated due to large PRs",
        tokens_used=50,
    )
    inv = _make_investigation(steps=[step1, step2])
    await repo.save(inv)

    loaded = await repo.get_by_id(inv.id)
    assert loaded is not None
    assert len(loaded.steps) == 2
    assert loaded.steps[0].step_type == InvestigationStepType.TOOL_CALL
    assert loaded.steps[0].tool_name == "query_metrics"
    assert loaded.steps[0].input_data == {"metric": "pr_cycle_time"}
    assert loaded.steps[0].output_data == {"value": 42.5}
    assert loaded.steps[0].reasoning == "Checking cycle time metric"
    assert loaded.steps[0].tokens_used == 100
    assert loaded.steps[1].step_type == InvestigationStepType.REASONING
    assert loaded.steps[1].tool_name is None
    assert loaded.steps[1].reasoning == "Cycle time is elevated due to large PRs"
    assert loaded.steps[1].tokens_used == 50


@pytest.mark.asyncio
async def test_save_completed_investigation(repo: MongoInvestigationRepository) -> None:
    inv = _make_investigation()
    inv.start()
    result = InvestigatorResult(
        steps=[
            InvestigationStep(
                step_type=InvestigationStepType.OBSERVATION,
                reasoning="Found root cause",
                tokens_used=200,
            )
        ],
        findings="Large PRs causing slow reviews",
        tokens_used=200,
    )
    inv.complete(result)
    await repo.save(inv)

    loaded = await repo.get_by_id(inv.id)
    assert loaded is not None
    assert loaded.status == InvestigationStatus.COMPLETED
    assert loaded.findings == "Large PRs causing slow reviews"
    assert loaded.tokens_used == 200
    assert len(loaded.steps) == 1


@pytest.mark.asyncio
async def test_save_overwrites_on_duplicate_id(repo: MongoInvestigationRepository) -> None:
    inv = _make_investigation()
    await repo.save(inv)

    inv.start()
    await repo.save(inv)

    loaded = await repo.get_by_id(inv.id)
    assert loaded is not None
    assert loaded.status == InvestigationStatus.RUNNING
