import pytest
from pydantic import TypeAdapter
from starlette.testclient import TestClient

from service.model import UserProfile
from tests.api.constants import API_VERSION
from tests.api.constants import CORRECT_USER


class TestApi:
    @pytest.mark.positive
    def test_login(self, client: TestClient):
        response = client.post(
            url=f"{API_VERSION}/login", json=CORRECT_USER.model_dump()
        )

        assert response.status_code == 200
        assert response.cookies["Authorization"]
        assert TypeAdapter(UserProfile).validate_json(response.json())
