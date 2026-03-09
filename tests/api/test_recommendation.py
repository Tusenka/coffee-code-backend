from http import HTTPStatus
from typing import Callable
from uuid import UUID

import pytest
from httpx import Cookies
from starlette.testclient import TestClient

from db.model import User
from service.model import UserProfile, UserProfileL1AccessList, UserProfileL1Access
from service.recommendation_service import RecommendationService
from tests.api.constants import API_VERSION
from tests.api.constants import CORRECT_EMAIL


class TestRecommendationApi:
    @pytest.mark.positive
    def test_recommended_profiles(
        self,
        client: TestClient,
        jwt_cookies: Cookies,
        enrich_user_tags,
        get_user_profile: Callable[[], UserProfile],
    ):
        profile = get_user_profile()
        response = client.get(
            f"{API_VERSION}/recommended_profiles", cookies=jwt_cookies
        )

        assert response.status_code == HTTPStatus.OK

        user_profiles = UserProfileL1AccessList.model_validate(response.json())

        assert user_profiles
        assert all(profile.user.id != p.user.id for p in user_profiles.profiles)

    @pytest.mark.positive
    def test_get_recommended_profile(
        self,
        client: TestClient,
        jwt_cookies: Cookies,
        enrich_user_tags,
        get_user_profile: Callable[[], UserProfile],
    ):
        profile = get_user_profile()
        user_profiles = self._get_profile_preview(client, jwt_cookies, profile.user.id)

        assert user_profiles

    @pytest.mark.positive
    def test_get_profile(
        self,
        client: TestClient,
        jwt_cookies: Cookies,
        enrich_user_tags,
        get_user_profile: Callable[[], UserProfile],
    ):
        profile = get_user_profile()
        user_profiles = self._get_profile_preview(client, jwt_cookies, profile.user.id)

        assert user_profiles

    @staticmethod
    def _get_profile_preview(
        client: TestClient, jwt_cookies: Cookies, id: UUID
    ) -> UserProfileL1Access:
        response = client.get(
            f"{API_VERSION}/profile_preview/{id}", cookies=jwt_cookies
        )

        assert response.status_code == HTTPStatus.OK
        user_profile = UserProfileL1Access.model_validate(response.json())
        return user_profile

    @pytest.mark.positive
    def test_send_request(
        self,
        client: TestClient,
        jwt_cookies: Cookies,
        enrich_user_tags,
        get_user_with_email: Callable[[str], User],
    ):
        profile = get_user_with_email(CORRECT_EMAIL)
        response = client.post(
            f"{API_VERSION}/profile/{profile.id}/send", cookies=jwt_cookies
        )

        assert response.status_code == HTTPStatus.OK

    @pytest.mark.positive
    def test_send_request_idempotency(
        self,
        client: TestClient,
        jwt_cookies: Cookies,
        enrich_user_tags,
        get_user_with_email: Callable[[str], User],
    ):
        profile = get_user_with_email(CORRECT_EMAIL)
        client.post(f"{API_VERSION}/profile/{profile.id}/send", cookies=jwt_cookies)
        response = client.post(
            f"{API_VERSION}/profile/{profile.id}/send", cookies=jwt_cookies
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.positive
    def test_accept_request(
        self,
        client: TestClient,
        jwt_cookies: Cookies,
        enrich_user_tags,
        recommendation_service: RecommendationService,
        get_current_user: Callable[[], User],
        get_user_with_email: Callable[[str], User],
    ):
        user = get_current_user()
        target_user = get_user_with_email(CORRECT_EMAIL)
        recommendation_service._send_match_request(
            initiator_user=target_user, target_user=user
        )

        response = client.post(
            f"{API_VERSION}/profile/{target_user.id}/accept",
            cookies=jwt_cookies,
        )

        assert response.status_code == HTTPStatus.OK

    @pytest.mark.positive
    def test_reject_request(
        self,
        client: TestClient,
        jwt_cookies: Cookies,
        enrich_user_tags,
        recommendation_service: RecommendationService,
        get_current_user: Callable[[], User],
        get_user_with_email: Callable[[str], User],
    ):
        user = get_current_user()
        target_user = get_user_with_email(CORRECT_EMAIL)
        recommendation_service._send_match_request(
            initiator_user=target_user, target_user=user
        )

        response = client.post(
            f"{API_VERSION}/profile/{target_user.id}/reject",
            cookies=jwt_cookies,
        )

        assert response.status_code == HTTPStatus.OK
