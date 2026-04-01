"""RunInvestigation use case -- creates investigation, calls investigator, produces insight (D-64).

Supports two delivery modes:
- Ad-hoc (thread_id provided): creates one Invocation for the requesting thread.
- Anomaly (no thread_id): broadcasts by creating one Invocation per existing project thread.
  If no threads exist for the project, the insight is stored but not delivered.
"""

from __future__ import annotations

from uuid import UUID

from core.application.ports.event_publisher import EventPublisher
from core.application.ports.investigator import Investigator
from core.application.ports.repositories import (
    InsightRepository,
    InvocationRepository,
    InvestigationRepository,
    ThreadRepository,
)
from core.domain.entities.insight import Insight
from core.domain.entities.investigation import Investigation
from core.domain.entities.invocation import Invocation
from core.domain.enums import InsightType, InvestigationTrigger, InvocationSource


class RunInvestigation:
    """Creates an Investigation, calls the Investigator port, persists Insight + Invocation(s).

    When thread_id is provided (ad-hoc), a single Invocation targets that thread.
    When thread_id is None (anomaly), Invocations are created for every existing
    project thread so the insight is broadcast as a proactive alert.
    """

    def __init__(
        self,
        investigation_repo: InvestigationRepository,
        insight_repo: InsightRepository,
        invocation_repo: InvocationRepository,
        thread_repo: ThreadRepository,
        investigator: Investigator,
        event_publisher: EventPublisher,
    ) -> None:
        self._investigation_repo = investigation_repo
        self._insight_repo = insight_repo
        self._invocation_repo = invocation_repo
        self._thread_repo = thread_repo
        self._investigator = investigator
        self._event_publisher = event_publisher

    async def execute(
        self,
        project_id: UUID,
        trigger: str,
        trigger_ref: UUID,
        query: str | None = None,
        thread_id: UUID | None = None,
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
                thread_id=thread_id,
                title=result.findings[:100],
                narrative=result.findings,
                insight_type=insight_type,
            )

            await self._investigation_repo.save(investigation)
            await self._insight_repo.save(insight)

            # Harvest events from insight entity and publish
            events = insight.flush_events()
            await self._event_publisher.publish_many(events)

            # Create invocations for delivery
            invocations = await self._build_invocations(project_id, thread_id, insight)
            if invocations:
                await self._invocation_repo.save_many(invocations)

            return insight

        except Exception as e:
            investigation.fail(str(e))
            await self._investigation_repo.save(investigation)
            return None

    async def _build_invocations(
        self,
        project_id: UUID,
        thread_id: UUID | None,
        insight: Insight,
    ) -> list[Invocation]:
        """Build targeted or broadcast invocations depending on whether thread_id is set."""
        message = f"New insight: {insight.title}"

        if thread_id is not None:
            # Ad-hoc: single invocation for the requesting thread
            return [
                Invocation(
                    thread_id=thread_id,
                    project_id=project_id,
                    source=InvocationSource.INSIGHT,
                    role="system",
                    message=message,
                )
            ]

        # Anomaly broadcast: one invocation per existing project thread
        threads = await self._thread_repo.get_by_project_id(project_id)
        return [
            Invocation(
                thread_id=t.id,
                project_id=project_id,
                source=InvocationSource.INSIGHT,
                role="system",
                message=message,
            )
            for t in threads
        ]
