from dataclasses import dataclass
import datetime
import logging

from agent.db.agent_repository import UserAgentRepository
from agent.metrics.config import get_tracer
from agent.metrics.utils import perf
from agent.scheduler.scheduler import Scheduler

logger = logging.getLogger(__name__)


@dataclass
class AgentMatchStatusUpdater:
    agent_repo: UserAgentRepository = UserAgentRepository()

    def run(self):
        Scheduler.every_hour_at(f=self.finish_meets, time=":05")
        Scheduler.every_hour_at(f=self.start_meets, time=":05")

    @perf("agent for finish meets")
    def finish_meets(self):
        tracer = get_tracer(__name__)
        logger.info("finish meets")
        with tracer.start_as_current_span("agent.finish_meets") as span:
            end_date = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
            self.agent_repo.finish_meets(end_date=end_date)

    @perf("agent for starting meets")
    def start_meets(self):
        logger.info("start meets")
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("agent.start_meets") as span:
            start_date = datetime.datetime.now(datetime.UTC)
            self.agent_repo.start_meets(start_date=start_date)
