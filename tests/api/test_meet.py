import random
from http import HTTPStatus
from typing import Callable
from uuid import UUID

import pytest
from httpx import Cookies
from starlette.testclient import TestClient

from agent.db.schema import MeetScoreDBSchema
from api.schemas import MeetScoreSchema
from db.model import User, Match
from service.model import (
    UserProfile,
    UserProfileL1AccessList,
    UserProfileL1Access,
    MeetList,
)
from service.recommendation_service import RecommendationService
from service.user_service import UserService
from tests.api.constants import API_VERSION
from tests.api.constants import CORRECT_EMAIL


class TestRecommendationApi:
    @pytest.mark.positive
    def test_get_meets(
        self,
        client: TestClient,
        jwt_cookies: Cookies,
        get_user_profile: Callable[[], UserProfile],
        get_activated_user: Callable[[], User],
        user_service: UserService,
        get_match: Callable[[...], Match],
    ):
        profile = get_user_profile()
        user_id = profile.user.id
        target_user_id = get_activated_user().id
        user_service.update_user_skills(
            skills=[s.id for s in profile.skills], user_id=target_user_id
        )
        match_id = get_match(user_id, target_user_id, -1, None, 0.5).id
        response = client.get(f"{API_VERSION}/meets", cookies=jwt_cookies)

        assert response.status_code == HTTPStatus.OK

        user_meets = MeetList.model_validate(response.json())
        user_meet = [m for m in user_meets.meet if m.id == match_id]

        assert user_meet
        user_meet = user_meet[0]

        assert user_meet.status
        assert user_meet.match_criteria
        assert user_meet.match_criteria.common_skills

    @pytest.mark.positive
    def test_create_review(
        self,
        client: TestClient,
        jwt_cookies: Cookies,
        get_user_profile: Callable[[], UserProfile],
        get_activated_user: Callable[[], User],
        user_service: UserService,
        get_match: Callable[[...], Match],
    ):
        profile = get_user_profile()
        user_id = profile.user.id
        target_user_id = get_activated_user().id
        user_service.update_user_skills(
            skills=[s.id for s in profile.skills], user_id=target_user_id
        )
        match_id = get_match(user_id, target_user_id, -1, None, 0.5).id
        score = MeetScoreSchema(
            meet_id=match_id, score=random.randint(0, 10), review="some_cool_review"
        )

        response = client.patch(
            f"{API_VERSION}/review",
            cookies=jwt_cookies,
            json=score.model_dump(mode="json"),
        )

        assert response.status_code == HTTPStatus.OK

        response = client.get(f"{API_VERSION}/meets", cookies=jwt_cookies)

        user_meets = MeetList.model_validate(response.json())
        user_meet = [m for m in user_meets.meet if m.id == match_id]

        assert user_meet
        user_meet = user_meet[0]

        assert user_meet.match_score
        assert user_meet.match_score.review == "some_cool_review"
        assert user_meet.match_score.score == score.score
