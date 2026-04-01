"""RunInvestigation use case -- creates investigation, calls investigator, produces insight (D-64)."""

from __future__ import annotations

from uuid import UUID

from core.application.ports.event_publisher import EventPublisher
from core.application.ports.investigator import Investigator
from core.application.ports.repositories import (
    InsightRepository,
    InvocationRepository,
    InvestigationRepository,
)
from core.domain.entities.insight import Insight
from core.domain.entities.investigation import Investigation
from core.domain.entities.invocation import Invocation
from core.domain.enums import InsightType, InvestigationTrigger, InvocationSource


class RunInvestigation:
    """Creates an Investigation, calls the Investigator port, persists Insight + Invocation."""

    def __init__(
        self,
        investigation_repo: InvestigationRepository,
        insight_repo: InsightRepository,
        invocation_repo: InvocationRepository,
        investigator: Investigator,
        event_publisher: EventPublisher,
    ) -> None:
        self._investigation_repo = investigation_repo
        self._insight_repo = insight_repo
        self._invocation_repo = invocation_repo
        self._investigator = investigator
        self._event_publisher = event_publisher

    async def execute(
        self,
        project_id: UUID,
        trigger: str,
        trigger_ref: UUID,
        query: str | None = None,
    ) -> Insight | None:
        trigger_enum = InvestigationTrigger(trigger)

        investigation = Investigation(
            project_id=project_id,
            trigger=trigger_enum,
            trigger_ref=trigger_ref,
            query=query,
        )
        investigation.start()

        try:
            result = await self._investigator.investigate(investigation, context={})
            investigation.complete(result)

            insight_type = (
                InsightType.ANOMALY_EXPLANATION
                if trigger_enum == InvestigationTrigger.ANOMALY
                else InsightType.AD_HOC_RESPONSE
            )

            insight = Insight(
                project_id=project_id,
                investigation_id=investigation.id,
                title=result.findings[:100],
                narrative=result.findings,
                insight_type=insight_type,
            )

            await self._investigation_repo.save(investigation)
            await self._insight_repo.save(insight)

            # Harvest events from insight entity and publish
            events = insight.flush_events()
            await self._event_publisher.publish_many(events)

            invocation = Invocation(
                thread_id=trigger_ref,
                project_id=project_id,
                source=InvocationSource.INSIGHT,
                role="system",
                message=f"New insight: {insight.title}",
            )
            await self._invocation_repo.save(invocation)

            return insight

        except Exception as e:
            investigation.fail(str(e))
            await self._investigation_repo.save(investigation)
            return None
