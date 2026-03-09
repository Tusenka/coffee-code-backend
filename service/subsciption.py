import dataclasses
import logging
from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from db.model import MatchRequest, Match
from db.user_repository import UserRepository
from service.model import UserSubscription

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class SubscriptionService:
    user_repository: UserRepository = UserRepository()

    def upsert_user_subscriptions(
        self,
        user_id: UUID,
        name: str,
        max_requests_per_week: int,
        max_matches_per_week: int,
        valid_until: datetime,
    ):
        sub_type = self.user_repository.upsert_subscription_type(
            name=name,
            max_requests_per_week=max_requests_per_week,
            max_matches_per_week=max_matches_per_week,
        )
        self.user_repository.upgrade_user_subscription(
            user_id=user_id, subscription_type=sub_type, valid_until=valid_until
        )

        return valid_until

    def get_active_user_subscription(
        self, user_id: UUID, session: Session | None = None
    ):
        return UserSubscription.from_dao(
            self.user_repository.get_active_user_subscription(
                user_id=user_id, session=session
            )
        )

    def validate_sent_requests_count(
        self,
        user_subscription: UserSubscription,
        sent_match_requests: list[MatchRequest],
    ) -> bool:
        logger.debug(
            """Проверка количества отправленных запросов на образование пары в неделю...
            Подписка отправителя и её условия: %s.
            Список отправленных запросов: %s.
            """,
            user_subscription,
            sent_match_requests,
        )

        today = date.today()
        end_week, start_week = self._extract_week(today)

        count_requests = len(
            [m for m in sent_match_requests if end_week >= m.created_at >= start_week]
        )

        if count_requests < user_subscription.max_requests_per_week:
            logger.info(
                "Количество отправленных запросов в неделю на образование пары (%d) не превосходит таковое по условиям имеющейся у отправителя подписки %d.",
                count_requests,
                user_subscription.max_matches_per_week,
            )
            return True
        else:
            logger.info(
                "Количество отправленных запросов в неделю на образование пары (%d) превосходит таковое по условиям имеющейся у отправителя подписки %d.",
                count_requests,
                user_subscription.max_matches_per_week,
            )
            return False

    def validate_match_count(
        self,
        user_subscription: UserSubscription,
        matches: list[Match],
        start_date: date,
    ) -> bool:
        end_week, start_week = self._extract_week(start_date)

        count_requests = len(
            [m for m in matches if end_week >= m.date_at >= start_week]
        )

        if count_requests < user_subscription.max_requests_per_week:
            return True
        else:
            return False

    @staticmethod
    def _extract_week(start_date: date) -> tuple[datetime, datetime]:
        start_week = datetime.combine(
            start_date - timedelta(days=start_date.weekday()), datetime.min.time()
        )
        end_week = datetime.combine(start_week + timedelta(days=6), datetime.min.time())
        return end_week, start_week
