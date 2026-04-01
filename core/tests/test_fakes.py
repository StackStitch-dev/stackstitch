"""Tests for in-memory fakes -- verifying each fake implements its port correctly."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from core.domain.entities.insight import Insight
from core.domain.entities.investigation import Investigation, InvestigatorResult, InvestigationStep
from core.domain.entities.invocation import Invocation
from core.domain.entities.metric import Metric, MetricDataPoint
from core.domain.entities.stream import Stream, StreamDataPoint
from core.domain.entities.thread import Message, Thread
from core.domain.enums import (
    InsightType,
    InvestigationStatus,
    InvestigationStepType,
    InvestigationTrigger,
    InvocationSource,
    InvocationStatus,
    MessageRole,
    MetricType,
    StreamType,
)
from core.domain.events.domain_events import StreamUpdated, MetricUpdated

from tests.fakes import (
    FakeAgent,
    FakeInvestigator,
    FakeMessageDeliverer,
    FakeMetricMonitor,
    FakeMetricsCalculator,
    InMemoryEventPublisher,
    InMemoryInsightRepository,
    InMemoryInvocationRepository,
    InMemoryInvestigationRepository,
    InMemoryMetricRepository,
    InMemoryStreamRepository,
    InMemoryThreadRepository,
)


# --- Stream Repository ---

class TestInMemoryStreamRepository:
    async def test_save_and_get_by_key(self) -> None:
        repo = InMemoryStreamRepository()
        project_id = uuid4()
        stream = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=project_id)
        await repo.save(stream)
        result = await repo.get_by_key("github", StreamType.PULL_REQUEST, project_id)
        assert result is not None
        assert result.source == "github"
        assert result.stream_type == StreamType.PULL_REQUEST

    async def test_get_by_key_returns_none_when_not_found(self) -> None:
        repo = InMemoryStreamRepository()
        result = await repo.get_by_key("github", StreamType.COMMIT, uuid4())
        assert result is None

    async def test_save_overwrites_existing(self) -> None:
        repo = InMemoryStreamRepository()
        project_id = uuid4()
        stream = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=project_id)
        stream.add_data_point(StreamDataPoint(timestamp=datetime.now(timezone.utc), data={"pr": 1}))
        await repo.save(stream)

        stream2 = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=project_id)
        stream2.add_data_point(StreamDataPoint(timestamp=datetime.now(timezone.utc), data={"pr": 2}))
        await repo.save(stream2)

        result = await repo.get_by_key("github", StreamType.PULL_REQUEST, project_id)
        assert result is not None
        assert len(result.data_points) == 1
        assert result.data_points[0].data == {"pr": 2}


# --- Metric Repository ---

class TestInMemoryMetricRepository:
    async def test_save_and_get_by_key(self) -> None:
        repo = InMemoryMetricRepository()
        project_id = uuid4()
        metric = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=project_id)
        await repo.save(metric)
        result = await repo.get_by_key(MetricType.PR_CYCLE_TIME, project_id)
        assert result is not None
        assert result.metric_type == MetricType.PR_CYCLE_TIME

    async def test_get_by_key_returns_none(self) -> None:
        repo = InMemoryMetricRepository()
        result = await repo.get_by_key(MetricType.PR_THROUGHPUT, uuid4())
        assert result is None


# --- Insight Repository ---

class TestInMemoryInsightRepository:
    async def test_save_and_get_by_id(self) -> None:
        repo = InMemoryInsightRepository()
        insight = Insight(
            project_id=uuid4(),
            investigation_id=uuid4(),
            title="Test Insight",
            narrative="Some findings",
            insight_type=InsightType.ANOMALY_EXPLANATION,
        )
        await repo.save(insight)
        result = await repo.get_by_id(insight.id)
        assert result is not None
        assert result.title == "Test Insight"

    async def test_get_by_id_returns_none(self) -> None:
        repo = InMemoryInsightRepository()
        result = await repo.get_by_id(uuid4())
        assert result is None


# --- Investigation Repository ---

class TestInMemoryInvestigationRepository:
    async def test_save_and_get_by_id(self) -> None:
        repo = InMemoryInvestigationRepository()
        investigation = Investigation(
            project_id=uuid4(),
            trigger=InvestigationTrigger.ANOMALY,
            trigger_ref=uuid4(),
        )
        await repo.save(investigation)
        result = await repo.get_by_id(investigation.id)
        assert result is not None
        assert result.trigger == InvestigationTrigger.ANOMALY

    async def test_get_by_id_returns_none(self) -> None:
        repo = InMemoryInvestigationRepository()
        result = await repo.get_by_id(uuid4())
        assert result is None


# --- Thread Repository ---

class TestInMemoryThreadRepository:
    async def test_save_and_get_by_id(self) -> None:
        repo = InMemoryThreadRepository()
        thread = Thread(project_id=uuid4())
        await repo.save(thread)
        result = await repo.get_by_id(thread.id)
        assert result is not None
        assert result.project_id == thread.project_id

    async def test_get_by_id_returns_none(self) -> None:
        repo = InMemoryThreadRepository()
        result = await repo.get_by_id(uuid4())
        assert result is None


# --- Invocation Repository ---

class TestInMemoryInvocationRepository:
    async def test_save_and_get_by_id(self) -> None:
        repo = InMemoryInvocationRepository()
        invocation = Invocation(
            thread_id=uuid4(),
            project_id=uuid4(),
            source=InvocationSource.USER_MESSAGE,
            role="user",
            message="What happened?",
        )
        await repo.save(invocation)
        result = await repo.get_by_id(invocation.id)
        assert result is not None
        assert result.message == "What happened?"

    async def test_save_many(self) -> None:
        repo = InMemoryInvocationRepository()
        thread_id = uuid4()
        project_id = uuid4()
        invocations = [
            Invocation(thread_id=thread_id, project_id=project_id, source=InvocationSource.USER_MESSAGE, role="user", message="msg1"),
            Invocation(thread_id=thread_id, project_id=project_id, source=InvocationSource.INSIGHT, role="system", message="msg2"),
        ]
        await repo.save_many(invocations)
        r1 = await repo.get_by_id(invocations[0].id)
        r2 = await repo.get_by_id(invocations[1].id)
        assert r1 is not None
        assert r2 is not None

    async def test_get_pending_by_thread_id(self) -> None:
        repo = InMemoryInvocationRepository()
        thread_id = uuid4()
        project_id = uuid4()

        pending = Invocation(thread_id=thread_id, project_id=project_id, source=InvocationSource.USER_MESSAGE, role="user", message="pending")
        done = Invocation(thread_id=thread_id, project_id=project_id, source=InvocationSource.USER_MESSAGE, role="user", message="done")
        done.mark_processing()
        done.mark_done()
        other_thread = Invocation(thread_id=uuid4(), project_id=project_id, source=InvocationSource.USER_MESSAGE, role="user", message="other")

        await repo.save_many([pending, done, other_thread])
        results = await repo.get_pending_by_thread_id(thread_id)
        assert len(results) == 1
        assert results[0].message == "pending"


# --- Event Publisher ---

class TestInMemoryEventPublisher:
    async def test_publish_appends(self) -> None:
        pub = InMemoryEventPublisher()
        event = StreamUpdated(source="github", stream_type="pull_request", project_id=uuid4())
        await pub.publish(event)
        assert len(pub.events) == 1
        assert pub.events[0] == event

    async def test_publish_many_extends(self) -> None:
        pub = InMemoryEventPublisher()
        events = [
            StreamUpdated(source="github", stream_type="pull_request", project_id=uuid4()),
            MetricUpdated(metric_type="pr_cycle_time", project_id=uuid4()),
        ]
        await pub.publish_many(events)
        assert len(pub.events) == 2

    async def test_clear_resets(self) -> None:
        pub = InMemoryEventPublisher()
        await pub.publish(StreamUpdated(source="github", stream_type="pull_request", project_id=uuid4()))
        pub.clear()
        assert len(pub.events) == 0


# --- Fake Investigator ---

class TestFakeInvestigator:
    async def test_returns_preset_result(self) -> None:
        result = InvestigatorResult(
            steps=[InvestigationStep(step_type=InvestigationStepType.REASONING, reasoning="thought")],
            findings="found something",
            tokens_used=100,
        )
        fake = FakeInvestigator(preset_result=result)
        investigation = Investigation(project_id=uuid4(), trigger=InvestigationTrigger.ANOMALY, trigger_ref=uuid4())
        output = await fake.investigate(investigation, {"key": "value"})
        assert output == result
        assert len(fake.calls) == 1
        assert fake.calls[0] == (investigation, {"key": "value"})


# --- Fake Metrics Calculator ---

class TestFakeMetricsCalculator:
    async def test_returns_preset_results(self) -> None:
        points = [MetricDataPoint(value=42.0, timestamp=datetime.now(timezone.utc))]
        fake = FakeMetricsCalculator(preset_results=points)
        stream = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=uuid4())
        output = await fake.calculate(stream)
        assert output == points
        assert len(fake.calls) == 1


# --- Fake Metric Monitor ---

class TestFakeMetricMonitor:
    async def test_records_checked_metrics(self) -> None:
        fake = FakeMetricMonitor()
        metric = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=uuid4())
        result = await fake.check(metric)
        assert len(fake.checked_metrics) == 1
        assert fake.checked_metrics[0] == metric
        assert result is None

    async def test_returns_preset_anomaly(self) -> None:
        from core.application.ports.metric_monitor import AnomalyResult

        anomaly = AnomalyResult(
            severity="high",
            description="test anomaly",
            metric_value=15.0,
            threshold=10.0,
        )
        fake = FakeMetricMonitor(preset_anomaly=anomaly)
        metric = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=uuid4())
        result = await fake.check(metric)
        assert result == anomaly


# --- Fake Agent ---

class TestFakeAgent:
    async def test_returns_preset_response(self) -> None:
        fake = FakeAgent(preset_response="Hello!")
        thread = Thread(project_id=uuid4())
        invocations = [
            Invocation(thread_id=thread.id, project_id=thread.project_id, source=InvocationSource.USER_MESSAGE, role="user", message="hi"),
        ]
        output = await fake.process(thread, invocations)
        assert output == "Hello!"
        assert len(fake.calls) == 1
        assert fake.calls[0] == (thread, invocations)


# --- Fake Message Deliverer ---

class TestFakeMessageDeliverer:
    async def test_records_deliveries(self) -> None:
        fake = FakeMessageDeliverer()
        thread_id = uuid4()
        await fake.deliver(thread_id, "Here is the report")
        assert len(fake.deliveries) == 1
        assert fake.deliveries[0] == (thread_id, "Here is the report")
