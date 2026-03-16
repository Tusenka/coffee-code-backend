import datetime
from typing import Callable
from uuid import UUID

import pytest

from db.enums import MatchRequestStatus, NotificationType
from db.model import User, MatchRequest, Match
from db.user_repository import UserRepository
from service.model import Notification
from service.notification_service import NotificationService
from service.recommendation_service import RecommendationService
from tests.service.constants import CORRECT_EMAIL
from db.model import User as DaoUser


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

        self._assert_notification_list(
            user_id=user1.id,
            notifications_service=notification_service,
            match=match,
            expected_type=NotificationType.MATCH_CREATED,
        )
        self._assert_notification_list(
            user_id=user1.id,
            notifications_service=notification_service,
            match=match,
            expected_type=NotificationType.MATCH_CREATED,
        )


    @staticmethod
    def _assert_notification_list(
        user_id: UUID,
        notifications_service: NotificationService,
        match_request: MatchRequest | None = None,
        match: Match | None = None,
        expected_type: NotificationType | None = None,
    ):
        assert match_request is None or match is None
        notifications = notifications_service.list_notifications(
            user_id=user_id, limit=1000
        ).notifications

        assert notifications
        assert [
            n
            for n in notifications
            if (not match_request or n.request_id == match_request.id)
            and (not match_request or n.match_id == match.id)
            and (not expected_type or n.type == expected_type)
        ]
