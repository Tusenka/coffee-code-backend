from http import HTTPStatus

import pytest
from httpx import Cookies
from pydantic import TypeAdapter
from starlette.testclient import TestClient

from api.schemas import UserUpdate, ContactUpdate
from db.constants import PHOTO_PREVIEW_TYPE
from service.model import UserProfile
from tests.api.constants import API_VERSION
from tests.api.constants import USER_UPDATE_DATA


class TestUserProfile:
    @pytest.mark.positive
    def test_get_profile(self, client: TestClient, jwt_cookies: dict):
        response = client.get(url=f"{API_VERSION}/profile", cookies=jwt_cookies)

        assert response.status_code == 200
        assert TypeAdapter(UserProfile).validate_json(response.json())

    @pytest.mark.positive
    def test_update_profile(self, client: TestClient, jwt_cookies: Cookies):
        user_profile = self._update_profile(
            client=client, jwt_cookies=jwt_cookies, user_data=USER_UPDATE_DATA
        )

        self._assert_profile_updated(expected=USER_UPDATE_DATA, actual=user_profile)

    @staticmethod
    def _get_profile(client: TestClient, jwt_cookies: Cookies) -> UserProfile:
        response = client.get(url=f"{API_VERSION}/profile", cookies=jwt_cookies)

        assert response.status_code == HTTPStatus.OK

        return TypeAdapter(UserProfile).validate_json(response.json())

    @staticmethod
    def _update_profile(
        client: TestClient, jwt_cookies: Cookies, user_data: UserUpdate
    ) -> UserProfile:
        response = client.patch(
            url=f"{API_VERSION}/profile",
            cookies=jwt_cookies,
            json=user_data.model_dump(mode="json"),
        )

        assert response.status_code == HTTPStatus.OK

        response = client.get(url=f"{API_VERSION}/profile", cookies=jwt_cookies)

        assert response.status_code == HTTPStatus.OK

        user_profile = TypeAdapter(UserProfile).validate_json(response.json())

        return user_profile

    def test_update_user_contacts(self, client: TestClient, jwt_cookies: Cookies):
        contact_datas = [
            ContactUpdate(name="setka", value="value"),
            ContactUpdate(name="email", value="admin@coffee-code.ru"),
        ]
        response = client.patch(
            url=f"{API_VERSION}/contacts",
            cookies=jwt_cookies,
            json=[
                contact_data.model_dump(mode="json") for contact_data in contact_datas
            ],
        )

        assert response.status_code == HTTPStatus.OK

        response = client.get(url=f"{API_VERSION}/profile", cookies=jwt_cookies)

        assert response.status_code == HTTPStatus.OK

        user_profile = TypeAdapter(UserProfile).validate_json(response.json())

        assert user_profile.contacts
        assert not [c for c in user_profile.contacts if c.name == "email"]

    @staticmethod
    def _assert_profile_updated(
        expected: UserUpdate,
        actual: UserProfile,
    ):
        assert actual.user.first_name == (
            expected.first_name or actual.user.first_name
        ), "first_name mismatch"
        assert actual.user.last_name == (expected.last_name or actual.user.last_name), (
            "last_name mismatch"
        )
        assert actual.user.telegram_username == (
            expected.telegram_username or actual.user.telegram_username
        ), "telegram_username mismatch"
        assert actual.user.phone == (expected.phone or actual.user.phone), (
            "phone mismatch"
        )
        assert actual.user.bio == (expected.bio or actual.user.bio), "bio mismatch"
        assert actual.user.education == (expected.education or actual.user.education), (
            "education mismatch"
        )
        assert actual.user.workplace == (expected.workplace or actual.user.workplace), (
            "workplace mismatch"
        )
        assert actual.user.birthday == (expected.birthday or actual.user.birthday), (
            "birthday mismatch"
        )
        if expected.email:
            assert actual.user.email == expected.email, "email mismatch"

        if expected.telegram_photo_url:
            assert (
                actual.user.photos[PHOTO_PREVIEW_TYPE] == expected.telegram_photo_url
            ), "telegram_photo_url mismatch"

        assert actual.user.updated_at is not None, "updated_at is None"
        assert actual.user.updated_at > actual.user.created_at, (
            "updated_at not greater than created_at"
        )

        assert actual.user_settings.is_active == (
            expected.is_active or actual.user_settings.is_active
        ), "is_active mismatch"
        assert actual.user_settings.count_meets_in_week == (
            expected.count_meets_in_week or actual.user_settings.count_meets_in_week
        ), "count_meets_in_week mismatch"
        assert actual.user_settings.use_email_channel == (
            expected.use_email_channel or actual.user_settings.use_email_channel
        ), "use_email_channel mismatch"
        assert actual.user_settings.use_telegram_channel == (
            expected.use_telegram_channel or actual.user_settings.use_telegram_channel
        ), "use_telegram_channel mismatch"
