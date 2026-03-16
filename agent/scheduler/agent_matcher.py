from dataclasses import dataclass, field

from agent.scheduler.scheduler import Scheduler
from agent.service.agent_recommendation_service import AgentRecommendationService


@dataclass
class AgentNotification:
    agent: AgentRecommendationService = field(
        default_factory=AgentRecommendationService
    )

    def run(self):
        Scheduler.every_day_at(self.agent.generate_matches(), time="00:00")
