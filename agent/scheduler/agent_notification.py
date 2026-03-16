import logging
import time
from dataclasses import dataclass, field
from uuid import UUID

from opentelemetry.trace.status import StatusCode
from typing_extensions import NamedTuple

from agent.metrics.config import get_tracer
from agent.metrics.instruments import record_error
from agent.metrics.utils import perf
from agent.scheduler.scheduler import Scheduler
from db.model import Match, User
from service.notification_service import NotificationService


class MatchEvent(NamedTuple):
    match: Match | None
    user: User
    target_user: User | None
    manual_result: list[UUID] | None


@dataclass
class AgentNotification:
    notification_service: NotificationService = field(
        default_factory=NotificationService
    )
    events: list[MatchEvent] = field(default_factory=list)

    def run(self):
        Scheduler.every_day_at(self.process_notification_events, time="06:00")

    def add_match_event(
        self,
        match: Match | None,
        user: User,
        target_user: User | None,
        manual_result: list[UUID] | None = None,
    ):
        self.events.append(
            MatchEvent(
                match=match,
                user=user,
                target_user=target_user,
                manual_result=manual_result,
            )
        )

    @perf("agent for process notification events")
    def process_notification_events(self):
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("agent.process_notification_events") as span:
            span.set_attribute("component", "agent")
            span.set_attribute("operation", "notification")
            span.set_attribute("event_count", len(self.events))
            span.add_event("processing_started")
            start_time = time.perf_counter()
            logger = logging.getLogger(__name__)
            for idx, event in enumerate(self.events):
                with tracer.start_as_current_span(
                    "agent.send_notification"
                ) as child_span:
                    child_span.set_attribute("notification_index", idx)
                    child_span.set_attribute(
                        "match_id", event.match.id if event.match else "manual"
                    )
                    try:
                        if event.match:
                            self.notification_service.send_match(
                                initiator_user=event.user,
                                target_user=event.target_user,
                                match=event.match,
                            )
                        else:
                            self.notification_service.send_match_not_found(
                                user=event.user,
                                manual_result=event.manual_result,
                            )
                    except Exception as e:
                        logger.exception(
                            "Не удалось отправить уведомление по паре %s.\n%s",
                            event.match.id,
                            e,
                        )
                        record_error(error_type="notification_error")
                        child_span.record_exception(e)
                        child_span.set_status(StatusCode.ERROR, str(e))
                        child_span.add_event(
                            "notification_failed", attributes={"error": str(e)}
                        )
                        # переход к следующему уведомлению
            duration = time.perf_counter() - start_time
            span.add_event(
                "processing_completed", attributes={"duration_seconds": duration}
            )
            span.set_attribute("processing.duration_seconds", duration)
            self.events.clear()
