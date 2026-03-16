import os
from typing import Callable
from uuid import UUID

import pytest

from db.enums import NotificationType
from db.model import Notification
from db.notification_repository import NotificationRepository
from db.user_helper_repository import UserHelperRepository
from db.user_repository import UserRepository
from tests.db.constants import NotificationData

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


@pytest.fixture(scope="session")
def user_repo() -> UserRepository:
    return UserRepository()


@pytest.fixture(scope="session")
def user_helper_repo() -> UserHelperRepository:
    return UserHelperRepository()


@pytest.fixture(scope="session")
def notification_repo() -> NotificationRepository:
    return NotificationRepository()


@pytest.fixture(scope="session")
def notification_factory(
    notification_repo: NotificationRepository,
) -> Callable[..., Notification]:
    def ans(user_id: UUID):
        return notification_repo.create(
            user_id=user_id,
            notification_type=NotificationType.MATCH_CREATED,
            title=NotificationData.title,
        )

    return ans
