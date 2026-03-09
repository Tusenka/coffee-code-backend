import datetime
from typing import Callable
from uuid import UUID

import pytest

from agent.db.agent_repository import UserAgentRepository
from agent.scheduler.agent_match_status_updater import AgentMatchStatusUpdater
from agent.service.agent_recommendation_service import AgentRecommendationService
from db.enums import MatchStatus
from db.model import User, Match


@pytest.mark.agent
class TestMatchStatusUpdater:
    def test_finish_meets(
        self,
        agent_match_status_updater: AgentMatchStatusUpdater,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        agent_repo: UserAgentRepository,
        get_match: Callable[[UUID, UUID, int, datetime.datetime], Match],
    ):
        user1 = get_activated_user()
        user2 = get_activated_user()
        match = get_match(
            user1.id,
            user2.id,
            -1,
            datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1),
        )

        assert match.status == MatchStatus.UNCOMPLETED

        agent_match_status_updater.finish_meets()

        match = agent_repo.get_match_by_id(match_id=match.id)

        assert match.status == MatchStatus.COMPLETED

    def test_start_meets(
        self,
        agent_match_status_updater: AgentMatchStatusUpdater,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        get_match: Callable[[UUID, UUID, int, datetime.datetime], Match],
        agent_repo: UserAgentRepository,
    ):
        user1 = get_activated_user()
        user2 = get_activated_user()
        match = get_match(user1.id, user2.id, -1, datetime.datetime.now(datetime.UTC))

        agent_match_status_updater.start_meets()

        match = agent_repo.get_match_by_id(match_id=match.id)

        assert match.status == MatchStatus.ONGOING
