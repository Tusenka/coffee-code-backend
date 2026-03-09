import os

import pytest

from db.user_helper_repository import UserHelperRepository
from db.user_repository import UserRepository

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


@pytest.fixture(scope="session")
def user_repo() -> UserRepository:
    return UserRepository()


@pytest.fixture(scope="session")
def user_helper_repo() -> UserHelperRepository:
    return UserHelperRepository()
