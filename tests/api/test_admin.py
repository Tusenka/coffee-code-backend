import pytest
from fastapi.testclient import TestClient


class TestApi:
    @pytest.mark.positive
    def test_update_skills(self, client: TestClient):
        pass
