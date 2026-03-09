import datetime
import random
from typing import Callable
from unittest.mock import Mock
from uuid import UUID

import pytest
from sqlalchemy import Column
from sqlalchemy.orm import Session

from agent.db.schema import UserScoreSchema, MeetScoreDBSchema
from api.schemas import MeetScoreSchema
from db.constants import GoalName
from db.enums import MatchRequestStatus as DaoMatchRequestStatus
from db.exceptions import RequestNotFound
from db.model import User as DaoUser, User, Match, Skill, Goal
from db.user_helper_repository import UserHelperRepository
from db.user_repository import UserRepository
from service.exceptions import RequestAlreadySent, ProfileAccessDenied
from service.model import (
    MatchRequestStatus,
    MatchStatus,
    UserProfileL1AccessList,
    Goal,
    Match,
)
from service.recommendation_service import RecommendationService
from service.user_service import UserService
from tests.service.constants import CORRECT_EMAIL, SkillRef


class TestRecommendationService:
    @pytest.mark.positive
    def test_send_request(
        self,
        get_user_with_email: Callable[[str], DaoUser],
        recommendation_service: RecommendationService,
        user_repo: UserRepository,
    ):
        initiator_user = get_user_with_email(CORRECT_EMAIL)
        target_user = get_user_with_email(CORRECT_EMAIL)

        self._assert_user_status(
            initiator_user,
            target_user,
            recommendation_service,
            target_status=MatchRequestStatus.UNSENT,
        )

        recommendation_service._send_match_request(
            initiator_user=initiator_user, target_user=target_user
        )

        assert user_repo.get_match_request(
            initiator_user_id=initiator_user.id, target_user_id=target_user.id
        )
        assert (
            user_repo.get_match_request(
                initiator_user_id=initiator_user.id, target_user_id=target_user.id
            ).status
            == DaoMatchRequestStatus.PENDING
        )

        self._assert_user_status(
            initiator_user=initiator_user,
            target_user=target_user,
            user_service=recommendation_service,
            target_status=MatchRequestStatus.ALREADY_SENT,
        )

        self._assert_user_status(
            initiator_user=target_user,
            target_user=initiator_user,
            user_service=recommendation_service,
            target_status=MatchRequestStatus.RECEIVED,
        )

    @staticmethod
    def _assert_user_status(
        initiator_user: DaoUser,
        target_user: DaoUser,
        user_service: RecommendationService,
        target_status: MatchRequestStatus = MatchRequestStatus.UNSENT,
    ):
        target_profile = user_service.get_user_l1_profile(
            target_user_id=target_user.id, initiator_user_id=initiator_user.id
        )

        assert target_profile
        assert target_profile.match_request_status == target_status

    @pytest.mark.positive
    def test_send_request_cross_request(
        self,
        get_user_with_email: Callable[[str], DaoUser],
        recommendation_service: RecommendationService,
        user_repo: UserRepository,
    ):
        initiator_user = get_user_with_email(CORRECT_EMAIL)
        target_user = get_user_with_email(CORRECT_EMAIL)

        recommendation_service._send_match_request(
            initiator_user=target_user, target_user=initiator_user
        )
        recommendation_service._send_match_request(
            initiator_user=initiator_user, target_user=target_user
        )

        assert not user_repo.get_match_request(
            initiator_user_id=initiator_user.id, target_user_id=target_user.id
        )
        assert (
            user_repo.get_match_request(
                target_user_id=initiator_user.id, initiator_user_id=target_user.id
            ).status
            == DaoMatchRequestStatus.APPROVED
        )

        self._assert_user_status(
            initiator_user=target_user,
            target_user=initiator_user,
            user_service=recommendation_service,
            target_status=MatchRequestStatus.SENT_AND_ACCEPTED,
        )
        self._assert_user_status(
            initiator_user=initiator_user,
            target_user=target_user,
            user_service=recommendation_service,
            target_status=MatchRequestStatus.RECEIVED_AND_ACCEPTED,
        )

    @pytest.mark.positive
    def test_send_request_idempotency(
        self,
        get_user_with_email: Callable[[str], DaoUser],
        recommendation_service: RecommendationService,
        user_repo: UserRepository,
    ):
        user = get_user_with_email(CORRECT_EMAIL)
        user_2 = get_user_with_email(CORRECT_EMAIL)

        recommendation_service._send_match_request(
            initiator_user=user, target_user=user_2
        )

        with pytest.raises(RequestAlreadySent):
            recommendation_service._send_match_request(
                initiator_user=user, target_user=user_2
            )

        assert user_repo.get_match_request(
            initiator_user_id=user.id, target_user_id=user_2.id
        )
        self._assert_user_status(
            initiator_user=user,
            target_user=user_2,
            user_service=recommendation_service,
            target_status=MatchRequestStatus.ALREADY_SENT,
        )

    @pytest.mark.positive
    def test_accept_request(
        self,
        get_user_with_email: Callable[[str], DaoUser],
        recommendation_service: RecommendationService,
        user_repo: UserRepository,
    ):
        initiator_user = get_user_with_email(CORRECT_EMAIL)
        target_user = get_user_with_email(CORRECT_EMAIL)

        recommendation_service._send_match_request(
            initiator_user=initiator_user, target_user=target_user
        )
        recommendation_service._accept_match_request(
            initiator_user=target_user, target_user=initiator_user
        )

        assert user_repo.get_match_request(
            initiator_user_id=initiator_user.id, target_user_id=target_user.id
        )

        self._assert_user_status(
            initiator_user=initiator_user,
            target_user=target_user,
            user_service=recommendation_service,
            target_status=MatchRequestStatus.SENT_AND_ACCEPTED,
        )
        self._assert_user_status(
            initiator_user=target_user,
            target_user=initiator_user,
            user_service=recommendation_service,
            target_status=MatchRequestStatus.RECEIVED_AND_ACCEPTED,
        )

    @pytest.mark.positive
    def test_reject_request(
        self,
        get_user_with_email: Callable[[str], DaoUser],
        recommendation_service: RecommendationService,
        user_repo: UserRepository,
    ):
        initiator_user = get_user_with_email(CORRECT_EMAIL)
        target_user = get_user_with_email(CORRECT_EMAIL)

        recommendation_service._send_match_request(
            initiator_user=initiator_user, target_user=target_user
        )
        recommendation_service._reject_match_request(
            initiator_user=target_user, target_user=initiator_user
        )

        self._assert_user_status(
            initiator_user=initiator_user,
            target_user=target_user,
            user_service=recommendation_service,
            target_status=MatchRequestStatus.SENT_AND_REJECTED,
        )
        self._assert_user_status(
            initiator_user=target_user,
            target_user=initiator_user,
            user_service=recommendation_service,
            target_status=MatchRequestStatus.RECEIVED_AND_REJECTED,
        )

    @pytest.mark.negative
    def test_accept_request_not_exist(
        self,
        get_user_with_email: Callable[[str], DaoUser],
        recommendation_service: RecommendationService,
        user_repo: UserRepository,
    ):
        user = get_user_with_email(CORRECT_EMAIL)
        user_2 = get_user_with_email(CORRECT_EMAIL)

        recommendation_service._send_match_request(
            target_user=user, initiator_user=user_2
        )

        with pytest.raises(RequestNotFound):
            recommendation_service._accept_match_request(
                initiator_user=user_2, target_user=user
            )

    @pytest.mark.negative
    def test_create_match(
        self,
        get_user_with_email: Callable[[str], DaoUser],
        recommendation_service: RecommendationService,
    ):
        initiator_user = get_user_with_email(CORRECT_EMAIL)
        target_user = get_user_with_email(CORRECT_EMAIL)

        recommendation_service.create_test_match(
            initiator_user_id=initiator_user.id,
            target_user_id=target_user.id,
            quant_id=1,
            start_date=datetime.datetime.today(),
        )
        match_list = recommendation_service.list_user_matches(user_id=initiator_user.id)

        assert match_list.meet
        match = next(
            match
            for match in match_list.meet
            if match.user_id == initiator_user.id
            and match.target_user.user.id == target_user.id
        )
        assert match
        assert match.status == MatchStatus.UNCOMPLETED

    @pytest.mark.positive
    @pytest.mark.parametrize("type_access", ["meet", "request"])
    def test_view_long_profile_access_allowed(
        self,
        get_user_with_email: Callable[[str], DaoUser],
        recommendation_service: RecommendationService,
        type_access: str,
    ):
        initiator_user = get_user_with_email(CORRECT_EMAIL)
        target_user = get_user_with_email(CORRECT_EMAIL)

        match type_access:
            case "meet":
                recommendation_service.create_test_match(
                    initiator_user_id=initiator_user.id,
                    target_user_id=target_user.id,
                    quant_id=1,
                    start_date=datetime.date.today(),
                )
            case "request":
                recommendation_service.send_match_request(
                    initiator_user_id=initiator_user.id, target_user_id=target_user.id
                )
                recommendation_service._accept_match_request(
                    initiator_user=target_user, target_user=initiator_user
                )

        assert recommendation_service.check_and_get_user_l2_profile(
            initiator_user_id=initiator_user.id, target_user_id=target_user.id
        )
        assert recommendation_service.check_and_get_user_l2_profile(
            target_user_id=initiator_user.id, initiator_user_id=target_user.id
        )

    @pytest.mark.negative
    @pytest.mark.parametrize("type_access", ["meet", "request"])
    def test_view_long_profile_access_forbidden(
        self,
        get_user_with_email: Callable[[str], DaoUser],
        recommendation_service: RecommendationService,
        type_access: str,
    ):
        initiator_user = get_user_with_email(CORRECT_EMAIL)
        another_user = get_user_with_email(CORRECT_EMAIL)
        target_user = get_user_with_email(CORRECT_EMAIL)

        match type_access:
            case "meet":
                recommendation_service.create_test_match(
                    initiator_user_id=initiator_user.id,
                    target_user_id=another_user.id,
                    quant_id=1,
                    start_date=datetime.date.today(),
                )
            case "request":
                recommendation_service.send_match_request(
                    initiator_user_id=initiator_user.id, target_user_id=another_user.id
                )
                recommendation_service._accept_match_request(
                    initiator_user=another_user, target_user=initiator_user
                )

        with pytest.raises(ProfileAccessDenied):
            recommendation_service.check_and_get_user_l2_profile(
                initiator_user_id=initiator_user.id, target_user_id=target_user.id
            )
        with pytest.raises(ProfileAccessDenied):
            recommendation_service.check_and_get_user_l2_profile(
                target_user_id=initiator_user.id, initiator_user_id=target_user.id
            )

    @pytest.mark.positive
    def test_match_criteria_filled(
        self,
        get_activated_user: Callable[[], User],
        recommendation_service: RecommendationService,
        user_repo: UserRepository,
        user_service: UserService,
        get_skill_id: Callable[[], Skill],
        user_helper_repo: UserHelperRepository,
        get_match: Callable[[], Match],
    ):
        initiator_user = get_activated_user()
        target_user = get_activated_user()
        common_skill_id = get_skill_id()
        mentor_skill_id = common_skill_id
        mentee_skill_id = get_skill_id()

        mentor_goal_id = user_helper_repo.get_goal_by_name(GoalName.MENTOR_GOAL).id
        mentee_goal_id = user_helper_repo.get_goal_by_name(GoalName.MENTEE_GOAL).id
        common_goal_id = user_helper_repo.get_goal_by_name(GoalName.BRAINSTORM).id

        self._update_user_tags(
            goals=[mentor_goal_id, mentee_goal_id, common_goal_id],
            mentor_skill_ids=[mentor_skill_id],
            mentee_skill_ids=[mentee_skill_id],
            skill_ids=[common_skill_id, mentor_skill_id],
            user_id=initiator_user.id,
            user_service=user_service,
        )
        self._update_user_tags(
            goals=[mentor_goal_id, mentee_goal_id, common_goal_id],
            mentor_skill_ids=[mentee_skill_id],
            mentee_skill_ids=[mentor_skill_id],
            skill_ids=[common_skill_id, mentee_skill_id],
            user_id=target_user.id,
            user_service=user_service,
        )

        distance = random.random()
        match_id = get_match(
            initiator_user.id,
            target_user.id,
            -1,
            None,
            distance,
        ).id
        i_matches = recommendation_service.list_user_matches(user_id=initiator_user.id)
        i_match = [m for m in i_matches.meet if m.id == match_id]

        assert len(i_match) == 1
        i_match = i_match[0]

        initiator_user = user_repo.get_user_by_id(user_id=initiator_user.id)
        target_user = user_repo.get_user_by_id(user_id=target_user.id)

        self._assert_match_criteria(
            distance, i_match, initiator_user, target_user, user_repo
        )

    @staticmethod
    def _assert_match_criteria(
        distance: float,
        i_match: Match,
        initiator_user: User,
        target_user: User,
        user_repo: UserRepository,
    ):
        i_goals = user_repo._pure_goals(initiator_user.goals)

        assert set(i_match.match_criteria.common_skills) == set(
            s.name for s in set(initiator_user.skills).intersection(target_user.skills)
        )
        assert set(i_match.match_criteria.common_goals) == set(
            s.name for s in set(i_goals).intersection(target_user.goals)
        )
        assert set(i_match.match_criteria.mentor_role) == set(
            s.name
            for s in set(initiator_user.mentor_skills).intersection(
                target_user.mentee_skills
            )
        )
        assert set(i_match.match_criteria.mentee_role) == set(
            s.name
            for s in set(initiator_user.mentee_skills).intersection(
                target_user.mentor_skills
            )
        )
        assert i_match.match_criteria.rate == 1 - distance

    @staticmethod
    def _update_user_tags(
        goals: list[UUID],
        mentee_skill_ids: list[UUID],
        mentor_skill_ids: list[UUID],
        skill_ids: list[UUID],
        user_id: UUID,
        user_service: UserService,
    ):
        user_service.update_user_skills(user_id=user_id, skills=skill_ids)
        user_service.update_user_mentor_skills(user_id=user_id, skills=mentee_skill_ids)
        user_service.update_user_mentee_skills(user_id=user_id, skills=mentor_skill_ids)
        user_service.update_user_goals(user_id=user_id, goals=goals)

    @pytest.mark.positive
    def test_match_criteria_base(
        self,
        get_activated_user: Callable[[], User],
        recommendation_service: RecommendationService,
        user_repo: UserRepository,
        user_service: UserService,
        get_match: Callable[[...], Match],
    ):
        initiator_user = get_activated_user()
        target_user = get_activated_user()
        distance = random.random()
        match_id = get_match(
            initiator_user.id,
            target_user.id,
            -1,
            None,
            distance,
        ).id
        i_matches = recommendation_service.list_user_matches(user_id=initiator_user.id)
        i_match = [m for m in i_matches.meet if m.id == match_id]

        self._assert_match_criteria(
            distance=distance,
            i_match=i_match[0],
            initiator_user=initiator_user,
            target_user=target_user,
            user_repo=user_repo,
        )
        self._assert_match_criteria(
            distance=distance,
            i_match=i_match[0],
            initiator_user=target_user,
            target_user=initiator_user,
            user_repo=user_repo,
        )

    @pytest.mark.positive
    def test_add_review_base(
        self,
        get_activated_user: Callable[[], User],
        recommendation_service: RecommendationService,
        user_service: UserService,
    ):
        initiator_user = get_activated_user()
        target_user = get_activated_user()
        match_id = recommendation_service.create_test_match(
            initiator_user_id=initiator_user.id,
            target_user_id=target_user.id,
            quant_id=1,
            start_date=datetime.datetime.today(),
        )

        recommendation_service.add_review(
            score=MeetScoreSchema(
                score=5,
                meet_id=match_id,
                review="Nice from initiator user",
            ),
            user_id=initiator_user.id,
        )
        recommendation_service.add_review(
            score=MeetScoreSchema(
                score=8,
                meet_id=match_id,
                review="Nice from target user",
            ),
            user_id=target_user.id,
        )

        i_matches = recommendation_service.list_user_matches(user_id=initiator_user.id)

        t_matches = recommendation_service.list_user_matches(user_id=target_user.id)

        i_match = [m for m in i_matches.meet if m.id == match_id]

        assert len(i_match) == 1
        assert i_match[0].match_score.review == "Nice from initiator user"
        assert i_match[0].match_score.score == 5

        t_match = [m for m in t_matches.meet if m.id == match_id]

        assert len(t_match) == 1
        assert t_match[0].match_score.review == "Nice from target user"
        assert t_match[0].match_score.score == 8

    @pytest.mark.positive
    def test_add_review_idempotency(
        self,
        get_activated_user: Callable[[], User],
        recommendation_service: RecommendationService,
    ):
        initiator_user = get_activated_user()
        target_user = get_activated_user()
        match_id = recommendation_service.create_test_match(
            initiator_user_id=initiator_user.id,
            target_user_id=target_user.id,
            quant_id=1,
            start_date=datetime.datetime.today(),
        )

        recommendation_service.add_review(
            score=MeetScoreSchema(
                score=3,
                meet_id=match_id,
                review="Nice from initiator user",
            ),
            user_id=initiator_user.id,
        )
        recommendation_service.add_review(
            score=MeetScoreSchema(score=5, meet_id=match_id), user_id=initiator_user.id
        )

        i_matches = recommendation_service.list_user_matches(user_id=initiator_user.id)

        i_match = [m for m in i_matches.meet if m.id == match_id]

        assert len(i_match) == 1
        assert i_match[0].match_score.review == "Nice from initiator user"
        assert i_match[0].match_score.score == 5

    @pytest.mark.parametrize(
        "transition",
        [
            MatchStatus.COMPLETED,
            MatchStatus.SKIPPED,
            MatchStatus.CANCELED_BY_TARGET,
            MatchStatus.CANCELED_BY_INITIATOR,
        ],
    )
    def test_complete_match_transitions(
        self,
        get_user_with_email: Callable[[str], DaoUser],
        recommendation_service: RecommendationService,
        notification_service: Mock,
        transition: MatchStatus,
    ):
        initiator_user = get_user_with_email(CORRECT_EMAIL)
        target_user = get_user_with_email(CORRECT_EMAIL)

        match_id = recommendation_service.create_test_match(
            initiator_user_id=initiator_user.id,
            target_user_id=target_user.id,
            quant_id=1,
            start_date=datetime.datetime.today(),
        )

        match transition:
            case MatchStatus.COMPLETED:
                recommendation_service.complete_match(match_id=match_id)
                # TODO: assert

            case MatchStatus.SKIPPED:
                recommendation_service.skip_match(match_id=match_id)
                # TODO: assert meet is skipped

            case MatchStatus.CANCELED_BY_INITIATOR:
                recommendation_service.cancel_match(
                    match_id=match_id, user_id=initiator_user.id
                )
                notification_service.cancel_match.assert_called()

            case MatchStatus.CANCELED_BY_TARGET:
                recommendation_service.cancel_match(
                    match_id=match_id, user_id=target_user.id
                )

                notification_service.cancel_match.assert_called()
        # TODO: Add tests to send notifications

        meet = recommendation_service.get_match_from_initiator(match_id=match_id)
        assert meet.status == transition

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
                SkillRef.MENTEE_MENTOR_SKILLS,
                SkillRef.MENTEE_MENTOR_SKILLS,
            ),
        ],
    )
    def test_recommended_profile_list(
        self,
        get_activated_user: Callable[[], DaoUser],
        recommendation_service: RecommendationService,
        user_repo: UserRepository,
        get_skill_id,
        user_helper_repo: UserHelperRepository,
        goals: list[GoalName],
        expected_goals: list[GoalName],
        skill_ref: SkillRef,
        expected_skill_ref: SkillRef,
    ):
        user = get_activated_user()
        user = self._update_user_skills_by_random(
            get_skill=get_skill_id, user_id=user.id, user_repo=user_repo
        )

        user_goal_ids = [
            user_helper_repo.get_goal_by_name(goal_name=goal).id for goal in goals
        ]
        # expected_goal_ids = [
        #     user_helper_repo.get_goal_id_by_name(goal_name=goal)
        #     for goal in expected_goals
        # ]
        user_repo.update_user_goals(user_id=user.id, goals=user_goal_ids)

        profile_list: UserProfileL1AccessList = (
            recommendation_service.list_user_l1_recommended_profiles(user_id=user.id)
        )

        assert profile_list.profiles
        # self._assert_goals(goal_ids=expected_goal_ids, profile_list=profile_list) -- TODO: We encount goals into accounts but not relies on it
        assert all(
            self._intersect_skill(
                skill_ref.get_skill_ids(p=user), expected_skill_ref.get_skill_ids(p=p)
            )
            for p in profile_list.profiles
        )

    def _assert_goals(
        self, goal_ids: list[UUID], profile_list: UserProfileL1AccessList
    ):
        assert any(
            any(
                self._has_goals(expected_goal_id=goal_id, goals=p.goals)
                for goal_id in goal_ids
            )
            for p in profile_list.profiles
        ), (
            f"goals {goal_ids} hasn't intersecion for {[[g.id for g in p.goals] for p in profile_list.profiles]}"
        )

    @staticmethod
    def _update_user_skills_by_random(
        get_skill: Callable[[], UUID], user_id: UUID, user_repo: UserRepository
    ) -> DaoUser:
        # prepare user skills
        skills_list = [get_skill(), get_skill(), get_skill()]
        mentor_skills = [get_skill()]
        mentee_skills = [get_skill()]

        user_repo.update_user_skills(user_id=user_id, skills=skills_list)
        user_repo.update_user_mentor_skills(user_id=user_id, skills=mentor_skills)
        user_repo.update_user_mentee_skills(user_id=user_id, skills=mentee_skills)

        user = user_repo.get_user_by_id(user_id=user_id)

        assert user

        return user

    @staticmethod
    def _has_goals(expected_goal_id, goals: list[Goal]):
        return expected_goal_id in set(g.id for g in goals)

    @staticmethod
    def _intersect_skill(in_skills: list[UUID], out_skills: list[UUID]):
        return set(skill for skill in in_skills).intersection(
            skill for skill in out_skills
        )
