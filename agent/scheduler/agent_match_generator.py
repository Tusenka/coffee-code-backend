from dataclasses import dataclass, field
import logging
import time

from opentelemetry.trace.status import StatusCode

from agent.metrics.config import get_tracer
from agent.metrics.instruments import record_error
from agent.metrics.utils import perf
from agent.scheduler.scheduler import Scheduler
from agent.service.agent_recommendation_service import AgentRecommendationService

logger = logging.getLogger(__name__)


@dataclass
class AgentMatchGenerator:
    agent_recommendation_service: AgentRecommendationService = field(
        default_factory=AgentRecommendationService
    )

    def run(self):
        Scheduler.every_day_at(f=self.generate_matches, time="06:00")

    @perf("agent generate matches")
    def generate_matches(self):
        tracer = get_tracer(__name__)
        logger.info("generate matches")
        with tracer.start_as_current_span("agent.match_generation") as span:
            span.set_attribute("component", "agent")
            span.set_attribute("scheduler", "daily")
            span.add_event("generation_started")
            start_time = time.perf_counter()
            try:
                self.agent_recommendation_service.generate_matches()
            except Exception as e:
                logger.exception("Ошибка при создании паросочетания.\n%s", e)
                record_error(error_type="match_generation_error")
                span.record_exception(e)
                span.set_status(StatusCode.ERROR, str(e))
                span.add_event("generation_failed", attributes={"error": str(e)})
                raise  # Прокидывание исключения для повторного проведения создания паросочетаний планировщиком.
            duration = time.perf_counter() - start_time
            span.add_event(
                "generation_completed", attributes={"duration_seconds": duration}
            )
            span.set_attribute("generation.duration_seconds", duration)
