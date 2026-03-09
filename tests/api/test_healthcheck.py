from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient


class TestApiUserAttributes:
    @pytest.mark.positive
    def test_healthcheck(
        self,
        client: TestClient,
    ):
        response = client.get("/api/health")

        assert response.status_code == HTTPStatus.OK
