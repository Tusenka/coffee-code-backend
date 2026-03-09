from typing import Callable
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from agent.db.agent_repository import UserAgentRepository
from agent.service.agent_recommendation_service import AgentRecommendationService
from db.constants import GoalName
from db.enums import UserMatchStatus, MatchStatus
from db.model import User, Match
from db.user_helper_repository import UserHelperRepository


@pytest.mark.agent
class TestAgentRecommendationService:
    """Integration tests for AgentRecommendationService without mocks."""

    @pytest.mark.slow
    @pytest.mark.postitive
    def test_generate_matches_basic(
        self,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        agent_repo: UserAgentRepository,
        session: Session,
    ):
        """
        Test that generate_matches creates a possible match and a match for two users.
        This test assumes there are at least two users with overlapping quants and compatible skills/goals.
        """
        user = get_activated_user()
        agent_recommendation_service.generate_matches()

        match_state = agent_repo.get_user_match_state(user_id=user.id, session=session)

        assert not agent_repo.list_unmatched_user_ids()
        assert match_state.current_status == UserMatchStatus.FILLED

    @pytest.mark.positive
    @pytest.mark.slow
    def test_generate_matches_completeness(
        self,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        agent_repo: UserAgentRepository,
        session: Session,
    ):
        """
        Test that generate_matches creates all possible matches .
        Make exactly one user unmatched, for example user1.
        Generate all possible matches again.

        Ensure that the user(user1) is matched.
        """
        user = get_activated_user()

        agent_recommendation_service.generate_matches()

        match_state = agent_repo.get_user_match_state(user_id=user.id, session=session)

        assert match_state.current_status == UserMatchStatus.FILLED
        assert not agent_repo.list_unmatched_user_ids()

        # reset match state for the user
        self._reset_user_match_state(agent_repo, session, user)

        session.expire_all()
        match_state = agent_repo.get_user_match_state(user_id=user.id, session=session)

        assert match_state.current_status == UserMatchStatus.UNFILLED
        assert agent_repo.list_unmatched_user_ids()

        agent_recommendation_service.generate_matches()

        session.expire_all()
        match_state = agent_repo.get_user_match_state(user_id=user.id, session=session)

        assert not agent_repo.list_unmatched_user_ids(strict=False)
        assert match_state.current_status == UserMatchStatus.FILLED

    @staticmethod
    def _reset_user_match_state(
        agent_repo: UserAgentRepository, session: Session, user: User
    ):
        matches = agent_repo.list_user_matches(user_id=user.id)
        for m in matches:
            agent_repo.transfer_match_to_new_status(
                match_id=m.id, new_status=MatchStatus.COMPLETED, session=session
            )
        session.commit()
        agent_repo.reset_match_states()

    def test_choose_interval(
        self,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        agent_repo: UserAgentRepository,
        session: Session,
    ):
        """Test that the interval selection chooses a valid quant."""
        initiator_user_id = get_activated_user().id
        agent_repo.update_user_quants(user_id=initiator_user_id, quants=[1, 2, 3, 4, 5])
        target_user_id = get_activated_user().id
        agent_repo.update_user_quants(user_id=target_user_id, quants=[2, 3, 5])

        initiator_user = agent_repo.get_user_by_id_and_session(
            user_id=initiator_user_id, session=session
        )
        target_user = agent_repo.get_user_by_id_and_session(
            user_id=target_user_id, session=session
        )

        quant_id = agent_recommendation_service._choose_interval(
            initiator_user=initiator_user,
            target_user=target_user,
            excluded_intervals=[1, 5],
        )

        assert quant_id in [2, 3]

    def test_get_match_raw(
        self,
        agent_recommendation_service: AgentRecommendationService,
        get_match: Callable[[UUID, UUID], Match],
        get_activated_user: Callable[[], User],
    ):
        """Test retrieving a match by ID."""
        user1 = get_activated_user()
        user2 = get_activated_user()
        match = get_match(user1.id, user2.id)

        match = agent_recommendation_service.get_match_raw(match.id)

        assert match.id == match.id
        assert match.initiator_user_id == user1.id
        assert match.target_user_id == user2.id

    def test_is_already_matching(
        self,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        session: Session,
    ):
        pass

    def test_choose_pair(
        self,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        agent_repo: UserAgentRepository,
        session: Session,
        user_helper_repo: UserHelperRepository,
    ):
        """Test that interval selection chooses a valid quant."""
        initiator_user = get_activated_user()
        agent_repo.update_user_goals(
            user_id=initiator_user.id,
            goals=[user_helper_repo.get_goal_by_name(GoalName.BRAINSTORM).id],
        )
        target_user_id = agent_recommendation_service._choose_pair(
            user_id=initiator_user.id, session=session, strict=False
        )
        target_user = agent_repo.get_user_by_id_and_session(
            user_id=target_user_id, session=session
        )
        initiator_user = agent_repo.get_user_by_id(user_id=initiator_user.id)

        assert set(q.id for q in initiator_user.quants).intersection(
            set(q.id for q in target_user.quants)
        )
        assert set(g.id for g in initiator_user.goals).intersection(
            set(g.id for g in target_user.goals)
        )
