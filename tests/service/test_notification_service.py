import datetime
from typing import Callable

import pytest

from db.model import User
from db.user_repository import UserRepository
from service.notification_service import NotificationService
from service.recommendation_service import RecommendationService
from tests.service.constants import CORRECT_EMAIL


@pytest.mark.skip(
    "Skip to stop spamming until CACD-59 is done. Unskip in case of changes in notification service"
)
class TestNotificationService:
    def test_create_match(
        self,
        user_repo: UserRepository,
        recommendation_service: RecommendationService,
        notification_service: NotificationService,
        get_user_with_email: Callable[[str], User],
    ):
        user1 = get_user_with_email(CORRECT_EMAIL)
        user2 = get_user_with_email(CORRECT_EMAIL)

        match_id = recommendation_service.create_test_match(
            initiator_user_id=user1.id,
            target_user_id=user2.id,
            quant_id=1,
            start_date=datetime.datetime.today(),
        )
        match = recommendation_service.get_match_raw(match_id=match_id)

        notification_service.send_match(
            match=match, initiator_user=user1, target_user=user2
        )
