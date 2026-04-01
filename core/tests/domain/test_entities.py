from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

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
from core.domain.events.domain_events import (
    InsightCreated,
    MessageCreated,
    MetricUpdated,
    StreamUpdated,
)
from core.domain.exceptions import InvalidEntityStateError


# --- Stream & StreamDataPoint ---


class TestStreamDataPoint:
    def test_instantiate(self) -> None:
        from core.domain.entities.stream import StreamDataPoint

        now = datetime.now(timezone.utc)
        sdp = StreamDataPoint(timestamp=now, data={"pr_number": 42, "action": "opened"})
        assert sdp.timestamp == now
        assert sdp.data == {"pr_number": 42, "action": "opened"}

    def test_frozen(self) -> None:
        from core.domain.entities.stream import StreamDataPoint

        sdp = StreamDataPoint(
            timestamp=datetime.now(timezone.utc), data={"key": "value"}
        )
        with pytest.raises(ValidationError):
            sdp.timestamp = datetime.now(timezone.utc)  # type: ignore[misc]


class TestStream:
    def test_instantiate(self) -> None:
        from core.domain.entities.stream import Stream

        pid = uuid4()
        s = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=pid)
        assert s.source == "github"
        assert s.stream_type == StreamType.PULL_REQUEST
        assert s.project_id == pid
        assert s.data_points == []

    def test_add_data_point(self) -> None:
        from core.domain.entities.stream import Stream, StreamDataPoint

        pid = uuid4()
        s = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=pid)
        dp = StreamDataPoint(timestamp=datetime.now(timezone.utc), data={"pr": 1})
        s.add_data_point(dp)
        assert len(s.data_points) == 1
        assert s.data_points[0] is dp

    def test_add_data_point_collects_stream_updated_event(self) -> None:
        from core.domain.entities.stream import Stream, StreamDataPoint

        pid = uuid4()
        s = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=pid)
        dp = StreamDataPoint(timestamp=datetime.now(timezone.utc), data={"pr": 1})
        s.add_data_point(dp)
        events = s.flush_events()
        assert len(events) == 1
        assert isinstance(events[0], StreamUpdated)
        assert events[0].source == "github"
        assert events[0].stream_type == "pull_request"
        assert events[0].project_id == pid

    def test_flush_events_clears(self) -> None:
        from core.domain.entities.stream import Stream, StreamDataPoint

        pid = uuid4()
        s = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=pid)
        s.add_data_point(StreamDataPoint(timestamp=datetime.now(timezone.utc), data={"pr": 1}))
        s.flush_events()
        assert s.flush_events() == []

    def test_equality_same_composite_key(self) -> None:
        from core.domain.entities.stream import Stream

        pid = uuid4()
        s1 = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=pid)
        s2 = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=pid)
        assert s1 == s2

    def test_equality_different_data_points(self) -> None:
        from core.domain.entities.stream import Stream, StreamDataPoint

        pid = uuid4()
        s1 = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=pid)
        s2 = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=pid)
        s2.add_data_point(
            StreamDataPoint(timestamp=datetime.now(timezone.utc), data={"x": 1})
        )
        assert s1 == s2  # same composite key despite different data_points

    def test_hash_same_composite_key(self) -> None:
        from core.domain.entities.stream import Stream

        pid = uuid4()
        s1 = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=pid)
        s2 = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=pid)
        assert hash(s1) == hash(s2)

    def test_inequality_different_key(self) -> None:
        from core.domain.entities.stream import Stream

        pid = uuid4()
        s1 = Stream(source="github", stream_type=StreamType.PULL_REQUEST, project_id=pid)
        s2 = Stream(source="github", stream_type=StreamType.COMMIT, project_id=pid)
        assert s1 != s2


# --- Metric & MetricDataPoint ---


class TestMetricDataPoint:
    def test_instantiate(self) -> None:
        from core.domain.entities.metric import MetricDataPoint

        now = datetime.now(timezone.utc)
        mdp = MetricDataPoint(value=3.14, timestamp=now)
        assert mdp.value == 3.14
        assert mdp.timestamp == now

    def test_frozen(self) -> None:
        from core.domain.entities.metric import MetricDataPoint

        mdp = MetricDataPoint(value=1.0, timestamp=datetime.now(timezone.utc))
        with pytest.raises(ValidationError):
            mdp.value = 2.0  # type: ignore[misc]


class TestMetric:
    def test_instantiate(self) -> None:
        from core.domain.entities.metric import Metric

        pid = uuid4()
        m = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=pid)
        assert m.metric_type == MetricType.PR_CYCLE_TIME
        assert m.project_id == pid
        assert m.data_points == []

    def test_add_data_point(self) -> None:
        from core.domain.entities.metric import Metric, MetricDataPoint

        pid = uuid4()
        m = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=pid)
        dp = MetricDataPoint(value=42.0, timestamp=datetime.now(timezone.utc))
        m.add_data_point(dp)
        assert len(m.data_points) == 1

    def test_add_data_point_collects_metric_updated_event(self) -> None:
        from core.domain.entities.metric import Metric, MetricDataPoint

        pid = uuid4()
        m = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=pid)
        dp = MetricDataPoint(value=42.0, timestamp=datetime.now(timezone.utc))
        m.add_data_point(dp)
        events = m.flush_events()
        assert len(events) == 1
        assert isinstance(events[0], MetricUpdated)
        assert events[0].metric_type == "pr_cycle_time"
        assert events[0].project_id == pid

    def test_flush_events_clears(self) -> None:
        from core.domain.entities.metric import Metric, MetricDataPoint

        pid = uuid4()
        m = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=pid)
        m.add_data_point(MetricDataPoint(value=1.0, timestamp=datetime.now(timezone.utc)))
        m.flush_events()
        assert m.flush_events() == []

    def test_equality_based_on_composite_key(self) -> None:
        from core.domain.entities.metric import Metric

        pid = uuid4()
        m1 = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=pid)
        m2 = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=pid)
        assert m1 == m2

    def test_hash_based_on_composite_key(self) -> None:
        from core.domain.entities.metric import Metric

        pid = uuid4()
        m1 = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=pid)
        m2 = Metric(metric_type=MetricType.PR_CYCLE_TIME, project_id=pid)
        assert hash(m1) == hash(m2)


# --- Investigation, InvestigationStep, InvestigatorResult ---


class TestInvestigationStep:
    def test_instantiate(self) -> None:
        from core.domain.entities.investigation import InvestigationStep

        step = InvestigationStep(
            step_type=InvestigationStepType.TOOL_CALL,
            tool_name="query_metrics",
            input_data={"metric": "pr_cycle_time"},
            output_data={"avg": 4.2},
            reasoning="Need to check metric trends",
            tokens_used=150,
        )
        assert step.step_type == InvestigationStepType.TOOL_CALL
        assert step.tool_name == "query_metrics"
        assert step.tokens_used == 150

    def test_frozen(self) -> None:
        from core.domain.entities.investigation import InvestigationStep

        step = InvestigationStep(
            step_type=InvestigationStepType.REASONING,
            reasoning="Analyzing...",
        )
        with pytest.raises(ValidationError):
            step.reasoning = "changed"  # type: ignore[misc]


class TestInvestigatorResult:
    def test_instantiate(self) -> None:
        from core.domain.entities.investigation import InvestigationStep, InvestigatorResult

        steps = [
            InvestigationStep(
                step_type=InvestigationStepType.REASONING,
                reasoning="Analyzing anomaly",
            )
        ]
        result = InvestigatorResult(
            steps=steps, findings="PR cycle time spiked due to holidays", tokens_used=500
        )
        assert len(result.steps) == 1
        assert result.findings == "PR cycle time spiked due to holidays"
        assert result.tokens_used == 500

    def test_frozen(self) -> None:
        from core.domain.entities.investigation import InvestigatorResult

        result = InvestigatorResult(steps=[], findings="test", tokens_used=100)
        with pytest.raises(ValidationError):
            result.findings = "changed"  # type: ignore[misc]


class TestInvestigation:
    def _make_investigation(self) -> "Investigation":  # type: ignore[name-defined]  # noqa: F821
        from core.domain.entities.investigation import Investigation

        return Investigation(
            project_id=uuid4(),
            trigger=InvestigationTrigger.ANOMALY,
            trigger_ref=uuid4(),
            query="Why did cycle time spike?",
        )

    def test_instantiate(self) -> None:
        inv = self._make_investigation()
        assert inv.status == InvestigationStatus.PENDING
        assert inv.steps == []
        assert inv.findings is None
        assert inv.tokens_used == 0

    def test_start_transitions_to_running(self) -> None:
        inv = self._make_investigation()
        inv.start()
        assert inv.status == InvestigationStatus.RUNNING

    def test_start_raises_if_not_pending(self) -> None:
        inv = self._make_investigation()
        inv.start()
        with pytest.raises(InvalidEntityStateError):
            inv.start()

    def test_complete_transitions_to_completed(self) -> None:
        from core.domain.entities.investigation import InvestigatorResult

        inv = self._make_investigation()
        inv.start()
        result = InvestigatorResult(
            steps=[], findings="All clear", tokens_used=200
        )
        inv.complete(result)
        assert inv.status == InvestigationStatus.COMPLETED
        assert inv.findings == "All clear"
        assert inv.tokens_used == 200

    def test_complete_raises_if_not_running(self) -> None:
        from core.domain.entities.investigation import InvestigatorResult

        inv = self._make_investigation()
        result = InvestigatorResult(steps=[], findings="test", tokens_used=0)
        with pytest.raises(InvalidEntityStateError):
            inv.complete(result)

    def test_fail_transitions_to_failed(self) -> None:
        inv = self._make_investigation()
        inv.start()
        inv.fail("Timeout exceeded")
        assert inv.status == InvestigationStatus.FAILED
        assert inv.findings == "Timeout exceeded"

    def test_fail_raises_if_not_running(self) -> None:
        inv = self._make_investigation()
        with pytest.raises(InvalidEntityStateError):
            inv.fail("error")

    def test_collect_and_flush_events(self) -> None:
        from core.domain.events.domain_events import DomainEvent

        inv = self._make_investigation()
        event = DomainEvent()
        inv.collect_event(event)
        flushed = inv.flush_events()
        assert len(flushed) == 1
        assert flushed[0] is event
        assert inv.flush_events() == []


# --- Insight ---


class TestInsight:
    def test_instantiate(self) -> None:
        from core.domain.entities.insight import Insight

        pid = uuid4()
        inv_id = uuid4()
        insight = Insight(
            project_id=pid,
            investigation_id=inv_id,
            title="PR Cycle Time Spike",
            narrative="The PR cycle time increased 3x this week...",
            insight_type=InsightType.ANOMALY_EXPLANATION,
            metadata={"severity": "high"},
        )
        assert insight.project_id == pid
        assert insight.investigation_id == inv_id
        assert insight.title == "PR Cycle Time Spike"
        assert insight.metadata == {"severity": "high"}
        assert insight.id is not None
        assert insight.created_at is not None

    def test_collects_insight_created_on_construction(self) -> None:
        from core.domain.entities.insight import Insight

        pid = uuid4()
        inv_id = uuid4()
        insight = Insight(
            project_id=pid,
            investigation_id=inv_id,
            title="Test",
            narrative="narrative",
            insight_type=InsightType.ANOMALY_EXPLANATION,
        )
        events = insight.flush_events()
        assert len(events) == 1
        assert isinstance(events[0], InsightCreated)
        assert events[0].insight_id == insight.id
        assert events[0].investigation_id == inv_id
        assert events[0].project_id == pid


# --- Thread & Message ---


class TestMessage:
    def test_instantiate(self) -> None:
        from core.domain.entities.thread import Message

        msg = Message(role=MessageRole.USER, content="What happened yesterday?")
        assert msg.role == MessageRole.USER
        assert msg.content == "What happened yesterday?"
        assert msg.timestamp is not None

    def test_frozen(self) -> None:
        from core.domain.entities.thread import Message

        msg = Message(role=MessageRole.USER, content="test")
        with pytest.raises(ValidationError):
            msg.content = "changed"  # type: ignore[misc]


class TestThread:
    def test_instantiate(self) -> None:
        from core.domain.entities.thread import Thread

        pid = uuid4()
        t = Thread(project_id=pid)
        assert t.project_id == pid
        assert t.messages == []
        assert t.id is not None
        assert t.created_at is not None

    def test_add_message(self) -> None:
        from core.domain.entities.thread import Message, Thread

        t = Thread(project_id=uuid4())
        msg = Message(role=MessageRole.USER, content="hello")
        t.add_message(msg)
        assert len(t.messages) == 1
        assert t.messages[0] is msg

    def test_add_message_collects_message_created_event(self) -> None:
        from core.domain.entities.thread import Message, Thread

        t = Thread(project_id=uuid4())
        msg = Message(role=MessageRole.USER, content="hello")
        t.add_message(msg)
        events = t.flush_events()
        assert len(events) == 1
        assert isinstance(events[0], MessageCreated)
        assert events[0].thread_id == t.id
        assert events[0].message_content == "hello"


# --- Invocation ---


class TestInvocation:
    def _make_invocation(self) -> "Invocation":  # type: ignore[name-defined]  # noqa: F821
        from core.domain.entities.invocation import Invocation

        return Invocation(
            thread_id=uuid4(),
            project_id=uuid4(),
            source=InvocationSource.USER_MESSAGE,
            role="user",
            message="What happened with the build?",
        )

    def test_instantiate(self) -> None:
        inv = self._make_invocation()
        assert inv.status == InvocationStatus.PENDING
        assert inv.source == InvocationSource.USER_MESSAGE
        assert inv.id is not None
        assert inv.created_at is not None

    def test_mark_processing(self) -> None:
        inv = self._make_invocation()
        inv.mark_processing()
        assert inv.status == InvocationStatus.PROCESSING

    def test_mark_processing_raises_if_not_pending(self) -> None:
        inv = self._make_invocation()
        inv.mark_processing()
        with pytest.raises(InvalidEntityStateError):
            inv.mark_processing()

    def test_mark_done(self) -> None:
        inv = self._make_invocation()
        inv.mark_processing()
        inv.mark_done()
        assert inv.status == InvocationStatus.DONE

    def test_mark_done_raises_if_not_processing(self) -> None:
        inv = self._make_invocation()
        with pytest.raises(InvalidEntityStateError):
            inv.mark_done()
