import datetime
from typing import Callable
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from sqlalchemy.orm import Session

from agent.db.agent_repository import UserAgentRepository
from agent.service.agent_recommendation_service import AgentRecommendationService
from api.schemas import UserUpdate
from db.constants import GoalName
from db.enums import UserMatchStatus, MatchStatus
from db.model import User, Match
from db.user_helper_repository import UserHelperRepository
from tests.agent.constants import CORRECT_DATETIME, SkillRef


@pytest.mark.agent
class TestUserAgentRepository:
    """Integration tests for UserAgentRepository."""

    @pytest.mark.positive
    def test_get_all_unmatched_user_ids_strict_mode(
        self,
        agent_repo: UserAgentRepository,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        session: Session,
    ):
        agent_repo._forced_reset_match_states()
        user1 = get_activated_user()

        unmatched_ids = agent_repo.list_unmatched_user_ids()
        assert user1.id in unmatched_ids

        user1.settings.is_active = False
        session.merge(user1.settings)

        session.commit()

        unmatched_ids = agent_repo.list_unmatched_user_ids()
        assert user1.id not in unmatched_ids

        user1.settings.is_active = True
        session.merge(user1.settings)
        session.commit()

        agent_repo.mark_user_match_state(
            user_id=user1.id, session=session, status=UserMatchStatus.FILLED
        )
        session.commit()

        unmatched_ids = agent_repo.list_unmatched_user_ids(strict=True)
        assert user1.id not in unmatched_ids

        agent_repo.mark_user_match_state(
            user_id=user1.id, session=session, status=UserMatchStatus.EVALUATION
        )
        session.commit()

        unmatched_ids = agent_repo.list_unmatched_user_ids(strict=True)
        assert user1.id not in unmatched_ids

    @pytest.mark.parametrize(
        "new_status",
        [UserMatchStatus.UNFILLED, UserMatchStatus.EVALUATION],
    )
    @pytest.mark.positive
    def test_get_all_unmatched_user_ids_weak_mode(
        self,
        agent_repo: UserAgentRepository,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        session: Session,
        new_status: UserMatchStatus,
    ):
        agent_repo._forced_reset_match_states()
        user1 = get_activated_user()

        agent_repo.mark_user_match_state(
            user_id=user1.id, session=session, status=new_status
        )
        session.commit()

        unmatched_ids = agent_repo.list_unmatched_user_ids(strict=False)
        assert user1.id in unmatched_ids

    @pytest.mark.positive
    @pytest.mark.parametrize(
        "day, hour,expected_timedelta",
        [
            (0, 0, datetime.timedelta(days=4)),
            (2, 4, datetime.timedelta(days=6, hours=4)),
            (3, 0, datetime.timedelta(days=0, hours=0)),
            (6, 23, datetime.timedelta(days=3, hours=23)),
        ],
    )
    def test_create_match_base(
        self,
        agent_repo: UserAgentRepository,
        get_activated_user: Callable[[], User],
        user_helper_repo: UserHelperRepository,
        day: int,
        hour: int,
        expected_timedelta: datetime.timedelta,
        session: Session,
    ):
        user1 = get_activated_user()
        user2 = get_activated_user()

        quant_id = user_helper_repo.get_quant_by_hour_day(day=day, hour=hour).id
        match_id = agent_repo.create_match(
            initiator_user_id=user1.id,
            target_user_id=user2.id,
            quant_id=quant_id,
            session=session,
            start_date=CORRECT_DATETIME.date(),
            video_link="mocke_videolink",
        )
        match = agent_repo._get_match_by_id_and_session(
            match_id=match_id, session=session
        )
        expected_datetime = (CORRECT_DATETIME + expected_timedelta).replace(tzinfo=None)

        assert match.status == MatchStatus.UNCOMPLETED
        assert match.quant.id == quant_id
        assert match.date_at == expected_datetime
        assert match.initiator_user_id == user1.id
        assert match.target_user_id == user2.id

    @pytest.mark.negative
    @pytest.mark.skip("Skip due to teardown")
    def test_create_match_duplicate(
        self,
        agent_repo: UserAgentRepository,
        get_activated_user: Callable[[], User],
        helper_repo: UserHelperRepository,
        session: Session,
    ):
        user1 = get_activated_user()
        user2 = get_activated_user()

        agent_repo.create_match(
            initiator_user_id=user1.id,
            target_user_id=user2.id,
            quant_id=1,
            start_date=CORRECT_DATETIME.date(),
            session=session,
            video_link="mock link",
        )
        agent_repo.create_match(
            initiator_user_id=user1.id,
            target_user_id=user2.id,
            quant_id=2,
            start_date=CORRECT_DATETIME.date(),
            session=session,
            video_link="mock link",
        )
        with pytest.raises((IntegrityError, PendingRollbackError)):
            agent_repo.create_match(
                initiator_user_id=user1.id,
                target_user_id=user2.id,
                quant_id=1,
                start_date=CORRECT_DATETIME.date(),
                session=session,
                video_link="mock link",
            )
        # TODO::Implement sql trigger
        # skipped
        # with pytest.raises(IntegrityError):
        #     agent_repo.create_match(
        #         initiator_user_id=user2.id,
        #         target_user_id=user1.id,
        #         quant_id=1,
        #         start_date=CORRECT_DATETIME.date(),
        #         session=session,
        #         video_link="mock link",
        #     )
        #     session.commit()

    def test_reset_user_match_status(
        self,
        agent_repo: UserAgentRepository,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        session: Session,
    ):
        agent_repo._forced_reset_match_states()
        user1 = get_activated_user()
        user2 = get_activated_user()
        user3 = get_activated_user()

        agent_recommendation_service._create_match(
            initiator_user=user1,
            target_user=user2,
            session=session,
            quant_id=1,
            today=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=24),
        )
        match2 = agent_recommendation_service._create_match(
            initiator_user=user3,
            target_user=user2,
            session=session,
            quant_id=1,
            today=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=7),
        )

        session.commit()

        agent_repo.reset_match_states()

        session.expire_all()

        match_state1 = agent_repo.get_user_match_state(
            user_id=user1.id, session=session
        )
        match_state2 = agent_repo.get_user_match_state(
            user_id=user2.id, session=session
        )
        match_state3 = agent_repo.get_user_match_state(
            user_id=user3.id, session=session
        )

        assert match_state1
        assert match_state1.current_status == UserMatchStatus.UNFILLED

        assert match_state2
        assert match_state2.current_status == UserMatchStatus.FILLED

        assert match_state3.current_status == UserMatchStatus.FILLED

        agent_repo.transfer_match_to_new_status(
            match_id=match2, new_status=MatchStatus.COMPLETED
        )

        agent_repo.reset_match_states()

        session.expire_all()

        match_state2 = agent_repo.get_user_match_state(
            user_id=user2.id, session=session
        )
        match_state3 = agent_repo.get_user_match_state(
            user_id=user3.id, session=session
        )

        assert match_state3.current_status == UserMatchStatus.UNFILLED
        assert match_state2.current_status == UserMatchStatus.UNFILLED

    @pytest.mark.positive
    @pytest.mark.parametrize(
        "max_cos, expect_present", [(0.4, True), (0.2, True), (0.1, False)]
    )
    @pytest.mark.slow
    def test_generate_match_base(
        self,
        agent_repo: UserAgentRepository,
        get_activated_user: Callable[[], User],
        max_cos: float,
        session: Session,
        expect_present: bool,
        user_helper_repo: UserHelperRepository,
    ):
        user = get_activated_user()

        # we check goals in another requests, for non strict mode
        agent_repo.update_user_goals(
            user_id=user.id,
            goals=[
                user_helper_repo.get_goal_by_name(goal_name=GoalName.BRAINSTORM).id,
                user_helper_repo.get_goal_by_name(
                    goal_name=GoalName.EXPERIENCE_EXCHANGE
                ).id,
            ],
        )
        agent_repo._forced_reset_match_states()
        session.expire_all()

        assert user.skills

        # check scores
        session.expire_all()

        session.flush()
        match_scores = agent_repo.generate_agent_matches(
            user_id=user.id, session=session, max_cos=max_cos, strict=not expect_present
        )

        if expect_present:
            assert match_scores

        assert all(score.score > 0 for score in match_scores)
        assert all(score.cosine_distance <= max_cos for score in match_scores)
        assert all(
            agent_repo._get_user_goal_ids(
                user_id=score.user_id, session=session
            ).intersection(
                agent_repo._get_user_goal_ids(user_id=user.id, session=session)
            )
            for score in match_scores
        )

        assert (
            sorted(match_scores, key=lambda a: (a.cosine_distance, 0 - a.score))
            == match_scores
        )

    @pytest.mark.positive
    @pytest.mark.parametrize(
        "goals, expected_goals, skill_ref, expected_skill_ref",
        [
            (
                [GoalName.BRAINSTORM],
                [GoalName.BRAINSTORM],
                SkillRef.ALL_SKILLS,
                SkillRef.ALL_SKILLS,
            ),
            (
                [GoalName.MENTOR_GOAL],
                [GoalName.MENTEE_GOAL],
                SkillRef.MENTOR_SKILLS,
                SkillRef.MENTEE_SKILLS,
            ),
            (
                [GoalName.MENTEE_GOAL],
                [GoalName.MENTOR_GOAL],
                SkillRef.MENTEE_SKILLS,
                SkillRef.MENTOR_SKILLS,
            ),
            (
                [GoalName.MENTOR_GOAL, GoalName.MENTEE_GOAL],
                [GoalName.MENTEE_GOAL, GoalName.MENTOR_GOAL],
                SkillRef.MENTEE_SKILLS,
                SkillRef.MENTEE_MENTOR_SKILLS,
            ),
        ],
    )
    @pytest.mark.slow
    def test_generate_match_goal_types(
        self,
        agent_repo: UserAgentRepository,
        get_activated_user: Callable[[], User],
        session: Session,
        goals: list[GoalName],
        expected_goals: list[GoalName],
        skill_ref: SkillRef,
        expected_skill_ref: SkillRef,
        get_skill: Callable[[], UUID],
        user_helper_repo: UserHelperRepository,
    ):
        user = get_activated_user()

        user = self._update_user_skills_by_random(
            get_skill=get_skill, user_id=user.id, agent_repo=agent_repo
        )

        user_goal_ids = [
            user_helper_repo.get_goal_by_name(goal_name=goal).id for goal in goals
        ]
        expected_goal_ids = [
            user_helper_repo.get_goal_by_name(goal_name=goal).id for goal in goals
        ]

        agent_repo.update_user_goals(user_id=user.id, goals=user_goal_ids)

        session.flush()

        match_scores = agent_repo.generate_agent_matches(
            user_id=user.id, session=session, max_cos=0.5, strict=False
        )
        user_ids = [score.user_id for score in match_scores]

        session.commit()
        session.expire_all()

        self._assert_goals(
            expected_goal_ids=expected_goal_ids,
            user_ids=user_ids,
            agent_repo=agent_repo,
            session=session,
        )
        self._assert_skill(
            user_id=user.id,
            matched_user_ids=user_ids,
            skill_ref=skill_ref,
            expected_skill_ref=expected_skill_ref,
            agent_repo=agent_repo,
            session=session,
        )

    @pytest.mark.positive
    @pytest.mark.slow
    def test_generate_match_mode(
        self,
        agent_repo: UserAgentRepository,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        session: Session,
    ):
        user = get_activated_user()
        agent_repo._forced_reset_match_states(status=UserMatchStatus.EVALUATION)

        match_scores = agent_repo.generate_agent_matches(
            user_id=user.id, session=session, max_cos=0.5, strict=True
        )
        assert not match_scores

        match_scores = agent_repo.generate_agent_matches(
            user_id=user.id, session=session, max_cos=0.5, strict=False
        )

        assert match_scores

    @pytest.mark.positive
    def test_list_users_without_embeddings(
        self,
        agent_repo: UserAgentRepository,
        get_activated_user: Callable[[], User | None],
        session: Session,
    ):
        user = get_activated_user()
        agent_repo.update_user_data(
            user_data=UserUpdate(bio="new bio for embedding"), user_id=user.id
        )

        session.expire_all()

        user_bios = agent_repo.list_users_without_embeddings(session=session)

        assert user.id in [u[0] for u in user_bios]

    @pytest.mark.parametrize(
        "skipped_status",
        [
            MatchStatus.SKIPPED,
            MatchStatus.CANCELED_BY_TARGET,
            MatchStatus.CANCELED_BY_INITIATOR,
            MatchStatus.COMPLETED,
        ],
    )
    def test_finish_meets(
        self,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        agent_repo: UserAgentRepository,
        get_match: Callable[[UUID, UUID, int, datetime.datetime], Match],
        skipped_status: MatchStatus,
    ):
        user1 = get_activated_user()
        user2 = get_activated_user()
        current_datetime = datetime.datetime.now(datetime.UTC)

        match = get_match(
            user1.id,
            user2.id,
            -1,
            current_datetime - datetime.timedelta(hours=2),
        )

        match_later_date = get_match(
            user1.id,
            user2.id,
            -1,
            current_datetime + datetime.timedelta(hours=2),
        )
        skipped_by_status_match = get_match(
            user1.id,
            user2.id,
            -1,
            current_datetime - datetime.timedelta(hours=3),
        )
        agent_repo.transfer_match_to_new_status(
            match_id=skipped_by_status_match.id, new_status=skipped_status
        )

        assert match.status == MatchStatus.UNCOMPLETED
        assert match_later_date.status == MatchStatus.UNCOMPLETED

        agent_repo.finish_meets(end_date=current_datetime)

        match = agent_repo.get_match_by_id(match_id=match.id)
        match_later_date = agent_repo.get_match_by_id(match_id=match_later_date.id)
        skipped_by_status_match = agent_repo.get_match_by_id(
            match_id=skipped_by_status_match.id
        )

        assert match.status == MatchStatus.COMPLETED
        assert match_later_date.status == MatchStatus.UNCOMPLETED
        assert skipped_by_status_match.status == skipped_status

    @pytest.mark.parametrize(
        "skipped_status",
        [
            MatchStatus.SKIPPED,
            MatchStatus.CANCELED_BY_TARGET,
            MatchStatus.CANCELED_BY_INITIATOR,
            MatchStatus.COMPLETED,
        ],
    )
    def testst_start_meets(
        self,
        agent_recommendation_service: AgentRecommendationService,
        get_activated_user: Callable[[], User],
        agent_repo: UserAgentRepository,
        get_match: Callable[[UUID, UUID, int, datetime.datetime], Match],
        skipped_status: MatchStatus,
    ):
        user1 = get_activated_user()
        user2 = get_activated_user()
        user3 = get_activated_user()
        current_datetime = datetime.datetime.now(datetime.UTC)

        match = get_match(
            user1.id,
            user2.id,
            -1,
            current_datetime - datetime.timedelta(hours=1),
        )

        match_later_date = get_match(
            user1.id,
            user2.id,
            -1,
            current_datetime + datetime.timedelta(hours=1),
        )
        skipped_by_status_match = get_match(
            user1.id,
            user3.id,
            -1,
            current_datetime - datetime.timedelta(hours=1),
        )
        agent_repo.transfer_match_to_new_status(
            match_id=skipped_by_status_match.id, new_status=skipped_status
        )

        assert match.status == MatchStatus.UNCOMPLETED
        assert match_later_date.status == MatchStatus.UNCOMPLETED

        agent_repo.start_meets(
            start_date=current_datetime - datetime.timedelta(hours=1)
        )

        match = agent_repo.get_match_by_id(match_id=match.id)
        match_later_date = agent_repo.get_match_by_id(match_id=match_later_date.id)
        skipped_by_status_match = agent_repo.get_match_by_id(
            match_id=skipped_by_status_match.id
        )

        assert match.status == MatchStatus.ONGOING
        assert match_later_date.status == MatchStatus.UNCOMPLETED
        assert skipped_by_status_match.status == skipped_status

    def _assert_goals(
        self,
        expected_goal_ids: list[UUID],
        user_ids: list[UUID],
        agent_repo: UserAgentRepository,
        session: Session,
    ):
        user_goals_ids = [
            set(agent_repo._get_user_goal_ids(user_id=u, session=session))
            for u in user_ids
        ]

        assert all(
            any(goal_id in goal_ids for goal_id in expected_goal_ids)
            for goal_ids in user_goals_ids
        ), f"goals {expected_goal_ids} hasn't intersecion for {user_goals_ids}"

    @staticmethod
    def _update_user_skills_by_random(
        get_skill: Callable[[], UUID], user_id: UUID, agent_repo: UserAgentRepository
    ) -> User:
        # prepare user skills
        skills_list = [get_skill(), get_skill(), get_skill()]
        mentor_skills = [get_skill()]
        mentee_skills = [get_skill()]

        agent_repo.update_user_skills(user_id=user_id, skills=skills_list)
        agent_repo.update_user_mentor_skills(user_id=user_id, skills=mentor_skills)
        agent_repo.update_user_mentee_skills(user_id=user_id, skills=mentee_skills)

        user = agent_repo.get_user_by_id(user_id=user_id)
        assert user

        return user

    def _assert_skill(
        self,
        user_id: UUID,
        matched_user_ids: list[UUID],
        skill_ref: SkillRef,
        expected_skill_ref: SkillRef,
        agent_repo: UserAgentRepository,
        session: Session,
    ):
        assert all(
            self._intersect_skill(
                skill_ref.get_skill_ids(
                    p=agent_repo.get_user_by_id_and_session(
                        user_id=user_id, session=session
                    )
                ),
                expected_skill_ref.get_skill_ids(
                    p=agent_repo.get_user_by_id_and_session(
                        user_id=matched_user_id, session=session
                    )
                ),
            )
            for matched_user_id in matched_user_ids
        )

    @staticmethod
    def _intersect_skill(in_skills: list[UUID], out_skills: list[UUID]):
        return set(skill for skill in in_skills).intersection(
            skill for skill in out_skills
        )
