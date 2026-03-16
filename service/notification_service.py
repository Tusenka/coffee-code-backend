import dataclasses
import logging
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from db.constants import ContactType
from db.enums import NotificationType
from db.exceptions import NotificationForbidden
from db.model import User, Match
from db.notification_repository import NotificationRepository
from service.mail_service import MailService
from service.model import Notification, NotificationList

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class NotificationService:
    mail_service: MailService = MailService()
    notification_repo: NotificationRepository = dataclasses.field(
        default_factory=NotificationRepository
    )

    def send_match(self, initiator_user: User, target_user: User, match: Match):
        self._send_match(user=initiator_user, target_user=target_user, match=match)
        self._send_match(user=target_user, target_user=initiator_user, match=match)

    def cancel_match(self, initiator_user: User, target_user: User, match: Match):
        self._cancel_match(user=initiator_user, target_user=target_user, match=match)
        self._cancel_match(user=target_user, target_user=initiator_user, match=match)

    def _start_meet(self, user: User, target_user: User, match: Match):
        email = self._get_user_email(user.contacts)
        timezone_ = user.timezone.ian if user.timezone else "UTC"
        time = match.date_at.astimezone(ZoneInfo(timezone_))
        msg = f"""
            Привет, {user.first_name}!
            Твоя встреча c пользователем {target_user.first_name} {target_user.last_name}, запланированная на {time.strftime("%m-%d-%Y %H:%M:%S")}, началась.
            {target_user.first_name} {target_user.last_name} из города {target_user.location}.

            Ссылка на его профиль: {self.get_user_profile_url_accept(user_id=target_user.id)}.
            """
        self.mail_service.send_mail(
            to=email,
            subject=f"Coffee & Code: Встреча с {target_user.first_name} {target_user.last_name} началась",
            body=msg,
        )
        # Create notification in lk
        self._create_notification(
            user_id=user.id,
            notification_type=NotificationType.MEET_STARTED,
            title=f"Встреча с {target_user.first_name} {target_user.last_name} началась",
            message=msg.strip(),
            match_id=match.id,
        )

    def _cancel_match(self, user: User, target_user: User, match: Match):
        email = self._get_user_email(user.contacts)
        timezone_ = user.timezone.ian if user.timezone else "UTC"
        time = match.date_at.astimezone(ZoneInfo(timezone_))
        msg = f"""
            Привет, {user.first_name}!
            Твоя встреча c пользователем {target_user.first_name} {target_user.last_name}, запланированная на {time.strftime("%m-%d-%Y %H:%M:%S")}, отменена.
            {target_user.first_name} {target_user.last_name} из города {target_user.location}.

            Ссылка на его профиль: {self.get_user_profile_url_accept(user_id=target_user.id)}.
            """
        self.mail_service.send_mail(
            to=email,
            subject=f"Coffee & Code: Встреча с {target_user.first_name} {target_user.last_name} отменена",
            body=msg,
        )
        # Create notification in lk
        self._create_notification(
            user_id=user.id,
            notification_type=NotificationType.MATCH_CANCELED,
            title=f"Встреча с {target_user.first_name} {target_user.last_name} отменена",
            message=msg.strip(),
            match_id=match.id,
        )

    def _send_match(self, user: User, target_user: User, match: Match):
        email = self._get_user_email(user.contacts)
        timezone_ = user.timezone.ian if user.timezone else "UTC"
        time = match.date_at.astimezone(ZoneInfo(timezone_))
        msg = f"""
            Привет, {user.first_name}!
            Тебе подобрана пара! Встреча пройдёт в {time.strftime("%m-%d-%Y %H:%M:%S")} по часовому поясу {user.timezone.ian}.
            Ссылка на встречу: {match.video_link}

            {target_user.first_name} {target_user.last_name} из города {target_user.locaion}.

            Ссылка на его профиль: {self.get_user_profile_url_accept(user_id=target_user.id)}.
            """
        self.mail_service.send_mail(
            to=email,
            subject=f"Coffee & Code: Знакомство для встречи онлайн {target_user.first_name} {target_user.last_name}",
            body=msg,
        )
        # Create notification in lk
        self._create_notification(
            user_id=user.id,
            notification_type=NotificationType.MATCH_CREATED,
            title=f"Подобрана пара с {target_user.first_name} {target_user.last_name}",
            message=msg.strip(),
            match_id=match.id,
        )

    def accept_request(self, initiator_user: User, target_user: User, request_id: UUID):
        email = self._get_user_email(target_user.contacts)

        initiator_email = self._get_user_email(target_user.contacts)

        msg = f"""
            Привет, {target_user.first_name}!

            {initiator_user.username or initiator_user.first_name} принял твой запрос!

            Вот его профиль:
              * Имя: {initiator_user.first_name} {initiator_user.last_name}
              * О себе: {initiator_user.bio}
              * Интересы и навыки: {", ".join([v.name for v in initiator_user.skills])}
              * Может научить: {", ".join(v.name for v in initiator_user.mentor_skills) or "Не указано"}
              * Хочет научиться: {", ".join(v.name for v in initiator_user.mentee_skills) or "Не указано"}
              * Цели встречи: {", ".join(v.name for v in initiator_user.goals)}
              * Email: {initiator_email}
              * Telegram: {initiator_user.telegram.telegram_username}

            Чтобы посмотреть полный профиль, перейди по ссылке:
            {self.get_user_full_profile(user_id=initiator_user.id)}

            С наилучшими пожеланиями,
            команда Coffee & Code

            admin@coffee-code.ru
            +79269693374
            @coffee_code_IT
            """

        self.mail_service.send_mail(
            to=email,
            subject=f"Coffee & Code: Ответ на заявку на знакомство от {initiator_user.username or initiator_user.first_name}",
            body=msg,
        )

        # Create notification in lk for target_user (the one who receives acceptance)
        self._create_notification(
            user_id=target_user.id,
            notification_type=NotificationType.REQUEST_ACCEPTED,
            title=f"{initiator_user.username or initiator_user.first_name} принял ваш запрос",
            message=msg.strip(),
            request_id=request_id,
        )

    def reject_request(self, initiator_user: User, target_user: User, request_id: UUID):
        contacts = target_user.contacts
        email = self._get_user_email(contacts)

        msg = f"""
            Привет, {target_user.first_name}!

            К сожалению, {initiator_user.username or initiator_user.first_name} пока не готов принять твою заявку на обмен контактами :(

            Ты можешь посмотреть другие подходящие профили: {self.get_user_recommended_profiles_url()}.

            С наилучшими пожеланиями,
            команда Coffee & Code

            admin@coffee-code.ru
            +79269693374
            @coffee_code_IT
            """

        self.mail_service.send_mail(
            to=email,
            subject=f"Coffee & Code: Ответ на заявку на знакомство от {initiator_user.username or initiator_user.first_name}",
            body=msg,
        )
        # Create notification in lk for target_user
        self._create_notification(
            user_id=target_user.id,
            notification_type=NotificationType.REQUEST_REJECTED,
            title=f"{initiator_user.username or initiator_user.first_name} отклонил ваш запрос",
            message=msg.strip(),
            request_id=request_id,
        )

    @staticmethod
    def _get_user_email(contacts) -> Any | None:
        email = [c.value for c in contacts if c.contact_type == ContactType.EMAIL]
        email = email[0] if email else None
        return email

    def send_request(self, initiator_user: User, target_user: User, request_id: UUID):
        email = self._get_user_email(target_user.contacts)

        msg = f"""
            Привет, {target_user.first_name}!

            {initiator_user.username or initiator_user.first_name} хочет с тобой познакомиться и предлагает обменяться опытом.

            Вот его профиль:
              * Имя: {initiator_user.first_name} {initiator_user.last_name}
              * О себе: {initiator_user.bio}
              * Интересы и навыки: {", ".join([v.name for v in initiator_user.skills])}
              * Может научить: {", ".join(v.name for v in initiator_user.mentor_skills) or "Не указано"}
              * Хочет научиться: {", ".join(v.name for v in initiator_user.mentee_skills) or "Не указано"}
              * Цели встречи: {", ".join(v.name for v in initiator_user.goals)}

            Чтобы посмотреть полный профиль и принять запрос на знакомство, перейди по ссылке:
            {self.get_user_recommended_profile_url(user_id=initiator_user.id)}

            С наилучшими пожеланиями,
            команда Coffee & Code

            admin@coffee-code.ru
            +79269693374
            @coffee_code_IT
            """

        self.mail_service.send_mail(
            to=email,
            subject=f"Coffee & Code: Заявка на знакомство от {initiator_user.username or initiator_user.first_name}",
            body=msg,
        )
        # Create notification in lk for target_user
        self._create_notification(
            user_id=target_user.id,
            notification_type=NotificationType.REQUEST_RECEIVED,
            title=f"Новый запрос на знакомство от {initiator_user.username or initiator_user.first_name}",
            message=msg.strip(),
            request_id=request_id,
        )
        self._create_notification(
            user_id=initiator_user.id,
            notification_type=NotificationType.REQUEST_SENT,
            title=f"Запрос на добавление на новое знакомство отправлен  {target_user.username or target_user.first_name}",
            message=msg.strip(),
            request_id=request_id,
        )

    @staticmethod
    def get_user_recommended_profiles_url():
        return "https://coffee-code.ru/recommended_profile"

    @staticmethod
    def get_user_recommended_profile_url(user_id: UUID):
        return f"https://coffee-code.ru/profile/{user_id}"

    @staticmethod
    def get_user_full_profile(user_id: UUID):
        return f"https://coffee-code.ru/profile/{user_id}"

    @staticmethod
    def get_user_profile_url_accept(user_id: UUID):
        return f"https://coffee-code.ru/profile/{user_id}/accept"

    @staticmethod
    def get_user_profile_url_reject(user_id: UUID):
        return f"https://coffee-code.ru/profile/{user_id}/reject"

    def send_match_not_found(self, user: User, manual_result: list[UUID]):
        email = self._get_user_email(user.contacts)
        msg = f"""
                Привет, {user.first_name}!
                Не удалось подобрать точную пару на время которое ты указал!😔
                Однако мы подобрали список наболее подходящих для тебя пользователей в другой время.

                👉Попробуй посмотреть рекомендации:
                {self.get_user_recommended_profile_url(user_id=user.id)}
                """
        self.mail_service.send_mail(
            to=email,
            subject=f"Coffee & Code: Знакомство для встречи онлайн {user.first_name} {user.last_name}",
            body=msg,
        )

        # Create notification in lk
        self._create_notification(
            user_id=user.id,
            notification_type=NotificationType.MATCH_NOT_FOUND,
            title="Не удалось подобрать пару",
            message=msg.strip(),
        )

    def _create_notification(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str | None = None,
        message: str | None = None,
        match_id: UUID | None = None,
        request_id: UUID | None = None,
    ):
        """Helper to create a notification."""
        try:
            self.notification_repo.create(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                match_id=match_id,
                request_id=request_id,
            )
        except Exception as e:
            logger.exception("Failed to create notification: %s", e)

    def list_notifications(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
        unread_only: bool = False,
    ) -> NotificationList:
        notifications = self.notification_repo.list_notifications(
            user_id=user_id,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
        )
        total = len(
            self.notification_repo.list_notifications(
                user_id=user_id, limit=1000, offset=0
            )
        )
        unread_count = self.notification_repo.count_unread(user_id=user_id)

        # Convert to schema
        notification_schemas = [Notification.from_dao(n) for n in notifications]
        notification_list = NotificationList(
            notifications=notification_schemas,
            total=total,
            unread_count=unread_count,
        )

        return notification_list

    def get_notification(self, notification_id: UUID, user_id: UUID) -> Notification:
        dao_notification = self._check_and_get_notification(
            notification_id=notification_id, user_id=user_id
        )

        return Notification.from_dao(dao_notification)

    def mark_notification_as_read(self, notification_id: UUID, user_id: UUID) -> None:
        self._check_and_get_notification(
            notification_id=notification_id, user_id=user_id
        )

        self.notification_repo.mark_as_read(notification_id)

    def mark_all_notifications_as_read(self, user_id: UUID) -> int:
        return self.notification_repo.mark_all_as_read(user_id)

    def delete_notification(self, user_id: UUID, notification_id: UUID) -> None:
        self._check_and_get_notification(
            notification_id=notification_id, user_id=user_id
        )

        self.notification_repo.delete(notification_id=notification_id)

    def _check_and_get_notification(self, notification_id: UUID, user_id: UUID):
        dao_notification = self.notification_repo.get_notification_by_id(
            notification_id
        )

        if not dao_notification or dao_notification.user_id != user_id:
            raise NotificationForbidden()

        return dao_notification
