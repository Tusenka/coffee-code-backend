import dataclasses
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from db.constants import ContactType
from db.model import User, Match
from service.mail_service import MailService


@dataclasses.dataclass
class NotificationService:
    mail_service: MailService = MailService()

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

    def accept_request(self, initiator_user: User, target_user: User):
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

    def reject_request(self, initiator_user: User, target_user: User):
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

    @staticmethod
    def _get_user_email(contacts) -> Any | None:
        email = [c.value for c in contacts if c.contact_type == ContactType.EMAIL]
        email = email[0] if email else None
        return email

    def send_request(self, initiator_user: User, target_user: User):
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
