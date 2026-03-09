from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from httpx import Cookies
from pydantic import TypeAdapter

from api.schemas import LocationUpdate
from db.constants import PHOTO_PREVIEW_TYPE
from db.model import User
from db.user_helper_repository import UserHelperRepository
from service.model import Timezone, Goal, Skill, UserProfile
from service.timequant_models import UserInterval
from service.user_service import UserService
from tests.api.constants import API_VERSION
from tests.api.constants import CORRECT_PHOTO_PATH


class TestApiUserAttributes:
    @pytest.mark.positive
    def test_update_user_attributes(
        self,
        client: TestClient,
        jwt_cookies: Cookies,
        skill: Skill,
        goal: Goal,
        timezone: Timezone,
    ):
        response = client.post(
            f"{API_VERSION}/skills", cookies=jwt_cookies, json=[str(skill.id)]
        )

        assert response.status_code == HTTPStatus.OK

        response = client.post(
            f"{API_VERSION}/skills_can_teach", cookies=jwt_cookies, json=[str(skill.id)]
        )

        assert response.status_code == HTTPStatus.OK

        response = client.post(
            f"{API_VERSION}/skills_want_learn",
            cookies=jwt_cookies,
            json=[str(skill.id)],
        )

        assert response.status_code == HTTPStatus.OK

        response = client.post(
            f"{API_VERSION}/goals", cookies=jwt_cookies, json=[str(goal.id)]
        )
        assert response.status_code == HTTPStatus.OK

        response = client.get(url=f"{API_VERSION}/profile", cookies=jwt_cookies)
        user_profile = TypeAdapter(UserProfile).validate_json(response.json())

        assert skill in set(user_profile.skills)
        assert skill in set(user_profile.mentor_skills)
        assert skill in set(user_profile.mentee_skills)
        assert goal in set(user_profile.goals)

    @pytest.mark.positive
    def test_file_upload(self, client: TestClient, jwt_cookies: Cookies):
        files = {"photo": ("preview.jpg", open(CORRECT_PHOTO_PATH, "rb"))}
        response = client.post(
            f"{API_VERSION}/user_photo",
            files=files,
            params={"photo_type": "preview"},
            cookies=jwt_cookies,
        )

        assert response.status_code == 200

        response = client.get(url=f"{API_VERSION}/profile", cookies=jwt_cookies)
        user_profile = TypeAdapter(UserProfile).validate_json(response.json())

        assert user_profile.user.photos[PHOTO_PREVIEW_TYPE]

    @pytest.mark.positive
    def test_update_user_intervals(
        self,
        client: TestClient,
        correct_user: User,
        jwt_cookies: Cookies,
        intervals: list[UserInterval],
        user_service: UserService,
        user_helper_repo: UserHelperRepository,
    ):
        user_service.update_user_location(
            LocationUpdate(
                timezone_id=user_helper_repo.get_timezone_id_by_ian(ian="UTC")
            ),
            user_id=correct_user.id,
        )
        response = client.post(
            f"{API_VERSION}/user_intervals",
            json=[i.model_dump(by_alias=True) for i in intervals],
            cookies=jwt_cookies,
        )

        assert response.status_code == 200

        response = client.get(url=f"{API_VERSION}/profile", cookies=jwt_cookies)
        user_profile = TypeAdapter(UserProfile).validate_json(response.json())

        assert sorted(
            user_profile.intervals, key=lambda x: (x.day, x.startHour, x.endHour)
        ) == sorted(intervals, key=lambda x: (x.day, x.startHour, x.endHour))
