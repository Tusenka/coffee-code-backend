import pytest

from db.user_helper_repository import UserHelperRepository
from db.user_repository import UserRepository
from tests.helpers import HelperDataLoader


def pytest_addoption(parser):
    parser.addoption(
        "--skip-load", action="store_true", default=False, help="skip generate db data"
    )


@pytest.fixture(scope="session")
def user_repo() -> UserRepository:
    return UserRepository()


@pytest.fixture(scope="session")
def user_helper_repo() -> UserHelperRepository:
    return UserHelperRepository()


@pytest.fixture(scope="session", autouse=True)
def prepare_data(
    user_helper_repo: UserHelperRepository, user_repo: UserRepository, request
) -> None:
    if request.config.getoption("--skip-load"):
        return
    HelperDataLoader.load_helper_data(user_helper_repo=user_helper_repo)
    HelperDataLoader.generate_user_profiles(
        user_repo=user_repo,
    )
