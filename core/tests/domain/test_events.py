from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.domain.events.domain_events import (
    AnomalyDetected,
    DomainEvent,
    InsightCreated,
    MessageCreated,
    MetricUpdated,
    StreamDataPointCreated,
    StreamUpdated,
)


class TestDomainEventBase:
    def test_auto_generated_fields(self) -> None:
        event = DomainEvent()
        assert event.event_id is not None
        assert event.occurred_at is not None

    def test_frozen(self) -> None:
        event = DomainEvent()
        with pytest.raises(ValidationError):
            event.event_id = uuid4()  # type: ignore[misc]


class TestStreamDataPointCreated:
    def test_instantiate(self) -> None:
        now = datetime.now(timezone.utc)
        pid = uuid4()
        event = StreamDataPointCreated(
            source="github",
            stream_type="pull_request",
            project_id=pid,
            timestamp=now,
            data={"pr_number": 42},
        )
        assert event.source == "github"
        assert event.stream_type == "pull_request"
        assert event.project_id == pid
        assert event.timestamp == now
        assert event.data == {"pr_number": 42}
        assert event.event_id is not None

    def test_frozen(self) -> None:
        event = StreamDataPointCreated(
            source="github",
            stream_type="pull_request",
            project_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            data={},
        )
        with pytest.raises(ValidationError):
            event.source = "jira"  # type: ignore[misc]


class TestStreamUpdated:
    def test_instantiate(self) -> None:
        event = StreamUpdated(
            source="github", stream_type="commit", project_id=uuid4()
        )
        assert event.source == "github"
        assert event.event_id is not None


class TestMetricUpdated:
    def test_instantiate(self) -> None:
        event = MetricUpdated(metric_type="pr_cycle_time", project_id=uuid4())
        assert event.metric_type == "pr_cycle_time"


class TestAnomalyDetected:
    def test_instantiate(self) -> None:
        event = AnomalyDetected(
            metric_type="pr_cycle_time",
            project_id=uuid4(),
            severity="high",
            description="Cycle time 3x above average",
            metric_value=12.5,
            threshold=4.0,
        )
        assert event.severity == "high"
        assert event.metric_value == 12.5
        assert event.threshold == 4.0

    def test_frozen(self) -> None:
        event = AnomalyDetected(
            metric_type="pr_cycle_time",
            project_id=uuid4(),
            severity="high",
            description="test",
            metric_value=10.0,
            threshold=3.0,
        )
        with pytest.raises(ValidationError):
            event.severity = "low"  # type: ignore[misc]


class TestInsightCreated:
    def test_instantiate(self) -> None:
        event = InsightCreated(
            insight_id=uuid4(), investigation_id=uuid4(), project_id=uuid4()
        )
        assert event.insight_id is not None
        assert event.event_id is not None


class TestMessageCreated:
    def test_instantiate(self) -> None:
        event = MessageCreated(thread_id=uuid4(), message_content="hello")
        assert event.message_content == "hello"
        assert event.event_id is not None
