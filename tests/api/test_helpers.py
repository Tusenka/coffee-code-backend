from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from service.model import SkillList, TimezoneList, GoalList
from tests.api.constants import API_VERSION


class TestHelperEndpoints:
    @pytest.mark.positive
    def test_get_skills(self, client: TestClient):
        """Test GET /skills endpoint."""
        response = client.get(f"{API_VERSION}/skills")

        assert response.status_code == HTTPStatus.OK

        assert SkillList.model_validate(response.json())

    @pytest.mark.positive
    def test_get_timezones(self, client: TestClient):
        """Test GET /timezones endpoint."""
        response = client.get(f"{API_VERSION}/timezones")

        assert response.status_code == HTTPStatus.OK
        assert TimezoneList.model_validate(response.json())

    @pytest.mark.positive
    def test_get_goals(self, client: TestClient):
        """Test GET /goals endpoint."""
        response = client.get(f"{API_VERSION}/goals")

        assert GoalList.model_validate(response.json())
