import dataclasses
import datetime
from uuid import UUID

from agent.db.schema import MeetScoreDBSchema
from api.schemas import MeetScoreSchema, CreateAdminMeetSchema, TransferAdminMeetSchema
from db.enums import MatchStatus as DaoMatchStatus
from db.model import User, Match
from db.user_repository import UserRepository
from service.exceptions import (
    RequestAlreadySent,
    SubscriptionMatchRequests,
    ProfileAccessDenied,
)
from service.model import (
    UserProfileL1AccessList,
    UserProfileL2Access,
    Match,
    MeetList,
    UserProfileL1Access,
    MatchStatus,
)
from service.notification_service import NotificationService
from service.subsciption import SubscriptionService
from service.timequant_service import TimeQuantService


@dataclasses.dataclass
class RecommendationService:
    user_repo: UserRepository = UserRepository()
    subscription_service: SubscriptionService = dataclasses.field(
        default_factory=lambda: SubscriptionService()
    )
    notification_service: NotificationService = dataclasses.field(
        default_factory=NotificationService
    )

    def send_match_request(self, initiator_user_id: UUID, target_user_id: UUID):
        initiator_user = self.user_repo.get_user_by_id(
            user_id=initiator_user_id, extended=True
        )
        target_user = self.user_repo.get_user_by_id(
            user_id=target_user_id, extended=True
        )

        return self._send_match_request(
            initiator_user=initiator_user, target_user=target_user
        )

    def _send_match_request(self, initiator_user: User, target_user: User):
        subscription = self.subscription_service.get_active_user_subscription(
            user_id=initiator_user.id
        )

        if self.user_repo.get_match_request(
            initiator_user_id=initiator_user.id, target_user_id=target_user.id
        ):
            raise RequestAlreadySent(
                user_id=initiator_user.id, target_user_id=target_user.id
            )

        if self.user_repo.get_match_request(
            target_user_id=initiator_user.id, initiator_user_id=target_user.id
        ):
            self._accept_match_request(
                initiator_user=initiator_user, target_user=target_user
            )
            return

        if self.subscription_service.validate_sent_requests_count(
            user_subscription=subscription,
            sent_match_requests=initiator_user.match_requests_sent,
        ):
            request_id = self.user_repo.send_match_request(
                initiator_user_id=initiator_user.id, target_user_id=target_user.id
            )
            self.notification_service.send_request(
                initiator_user=initiator_user,
                target_user=target_user,
                request_id=request_id,
            )
        else:
            raise SubscriptionMatchRequests(user_id=initiator_user.id)

    def accept_match_request(self, initiator_user_id: UUID, target_user_id: UUID):
        initiator_user = self.user_repo.get_user_by_id(user_id=initiator_user_id)
        target_user = self.user_repo.get_user_by_id(user_id=target_user_id)

        self._accept_match_request(
            initiator_user=initiator_user, target_user=target_user
        )

    def _accept_match_request(self, initiator_user: User, target_user: User):
        request_id = self.user_repo.accept_match(
            initiator_user_id=initiator_user.id, target_user_id=target_user.id
        )

        self.notification_service.accept_request(
            initiator_user=initiator_user,
            target_user=target_user,
            request_id=request_id,
        )

    def reject_match_request(self, initiator_user_id: UUID, target_user_id: UUID):
        initiator_user = self.user_repo.get_user_by_id(user_id=initiator_user_id)
        target_user = self.user_repo.get_user_by_id(user_id=target_user_id)

        self._accept_match_request(
            initiator_user=initiator_user, target_user=target_user
        )

    def _reject_match_request(self, initiator_user: User, target_user: User):
        request_id = self.user_repo.reject_match(
            initiator_user_id=initiator_user.id, target_user_id=target_user.id
        )
        self.notification_service.reject_request(
            initiator_user=initiator_user,
            target_user=target_user,
            request_id=request_id,
        )

    def create_test_match(
        self,
        initiator_user_id: UUID,
        target_user_id: UUID,
        quant_id: int,
        start_date: datetime.date,
    ) -> UUID:
        """Создание пары между двумя пользователями на кванте календаря. Только для тестов."""
        with self.user_repo.db.get_session() as session:
            return self.user_repo.create_match(
                initiator_user_id=initiator_user_id,
                target_user_id=target_user_id,
                quant_id=quant_id,
                start_date=start_date,
                session=session,
                video_link="mock video link",
            )

    def cancel_match(self, match_id: UUID, user_id: UUID):
        """Отмена встречи по идентификатору. `user_id` должен быть её участником и будет значиться как инициатор отменты."""
        self.user_repo.cancel_match(match_id=match_id, user_id=user_id)
        self.notification_service.cancel_match(
            initiator_user=self.user_repo.get_user_by_id(user_id),
            target_user=self.user_repo.get_user_by_id(user_id),
            match=self.user_repo.get_match_by_id(match_id),
        )

    def skip_match(self, match_id: UUID):
        """Пропуск встречи."""
        self.user_repo.transfer_match_to_new_status(
            match_id=match_id, new_status=DaoMatchStatus.SKIPPED
        )

    def complete_match(self, match_id: UUID):
        """Завершить встречу."""
        self.user_repo.transfer_match_to_new_status(
            match_id=match_id, new_status=DaoMatchStatus.COMPLETED
        )

    def get_match_from_initiator(self, match_id: UUID) -> Match:
        match = self.user_repo.get_match_by_id(match_id=match_id)

        target_user = self.user_repo.get_user_by_id(user_id=match.target_user_id)

        return Match.from_dao(
            match=match,
            original_user_id=match.initiator_user_id,
            target_user=target_user,
            to_user_intervals_with_offset=TimeQuantService.to_user_intervals_with_offset,
        )

    def get_match_raw(self, match_id: UUID) -> Match:
        return self.user_repo.get_match_by_id(match_id=match_id)

    def list_user_l1_recommended_profiles(
        self, user_id: UUID
    ) -> UserProfileL1AccessList:
        users = self.user_repo.generate_manual_best_intersection_user_list(
            user_id=user_id
        )
        if not users:
            users = self.user_repo.generate_manual_best_intersection_user_list(
                user_id=user_id, strict=False
            )
        target_user = self.user_repo.get_user_by_id(user_id=user_id, extended=True)

        return UserProfileL1AccessList.from_dao(
            users,
            target_user=target_user,
        )

    def check_and_get_user_l2_profile(
        self, initiator_user_id, target_user_id: UUID
    ) -> UserProfileL2Access:
        if not self.user_repo.get_user_profile_access(
            initiator_user_id=initiator_user_id, target_user_id=target_user_id
        ):
            raise ProfileAccessDenied(
                initiator_user_id=initiator_user_id, target_user_id=target_user_id
            )

        return UserProfileL2Access.from_dao(
            user=self.user_repo.get_user_by_id(user_id=target_user_id)
        )

    def get_user_l1_profile(
        self, target_user_id: UUID, initiator_user_id: UUID
    ) -> UserProfileL1Access:
        return UserProfileL1Access.from_dao(
            initiator_user=self.user_repo.get_user_by_id(
                user_id=initiator_user_id, extended=True
            ),
            target_user=self.user_repo.get_user_by_id(
                user_id=target_user_id, extended=True
            ),
        )

    def add_review(self, score: MeetScoreSchema, user_id: UUID):
        self.user_repo.upsert_review(
            score=MeetScoreDBSchema(
                meet_id=score.meet_id, score=score.score, review=score.review
            ),
            user_id=user_id,
        )

    def list_user_matches(self, user_id: UUID) -> MeetList:
        matches = [
            Match.from_dao(
                match=match,
                original_user_id=user_id,
                target_user=self.user_repo.get_user_by_id(match.target_user_id)
                if match.initiator_user_id == user_id
                else self.user_repo.get_user_by_id(match.initiator_user_id),
                to_user_intervals_with_offset=TimeQuantService.to_user_intervals_with_offset,
            )
            for match in self.user_repo.list_user_matches(user_id=user_id)
        ]

        return MeetList(meet=matches)

    def get_user_match(self, user_id: UUID, match_id: UUID) -> Match:
        match = self.user_repo.get_match_by_id(match_id=match_id)

        return Match.from_dao(
            match=match,
            original_user_id=user_id,
            target_user=self.user_repo.get_user_by_id(match.target_user_id)
            if match.initiator_user_id == user_id
            else self.user_repo.get_user_by_id(match.initiator_user),
            to_user_intervals_with_offset=TimeQuantService.to_user_intervals_with_offset,
        )

    def create_match(self, meet: CreateAdminMeetSchema) -> UUID:
        with self.user_repo.db.get_session() as session:
            match_id = self.user_repo.create_match(
                initiator_user_id=meet.initiator_user_id,
                target_user_id=meet.target_user_id,
                quant_id=meet.quant_id,
                start_date=datetime.date.today(),
                session=session,
                video_link=meet.video_link,
            )
            self.user_repo.create_match_criteria(
                initiator_user_id=meet.initiator_user_id,
                target_user_id=meet.target_user_id,
                match_id=match_id,
                session=session,
                distance=meet.cosine_distance,
            )

            return match_id

    def transfer_meet_status(self, transfer_meet: TransferAdminMeetSchema) -> UUID:
        with self.user_repo.db.get_session() as session:
            match = self.user_repo.get_match_by_id(match_id=transfer_meet.meet_id)
            match transfer_meet.new_status:
                case MatchStatus.COMPLETED:
                    self.user_repo.transfer_match_to_new_status(
                        match_id=transfer_meet.meet_id,
                        session=session,
                        new_status=DaoMatchStatus.COMPLETED,
                    )
                case MatchStatus.SKIPPED:
                    self.user_repo.transfer_match_to_new_status(
                        match_id=transfer_meet.meet_id,
                        session=session,
                        new_status=DaoMatchStatus.SKIPPED,
                    )
                case MatchStatus.CANCELED_BY_INITIATOR:
                    self.user_repo.cancel_match_in_session(
                        match_id=transfer_meet.meet_id,
                        session=session,
                        user_id=match.initiator_user_id,
                    )
                case MatchStatus.CANCELED_BY_INITIATOR:
                    self.user_repo.cancel_match_in_session(
                        match_id=transfer_meet.meet_id,
                        session=session,
                        user_id=match.target_user_id,
                    )

            return transfer_meet.meet_id
