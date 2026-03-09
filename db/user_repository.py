import datetime
import logging
import random
import uuid
from contextlib import contextmanager
from copy import deepcopy
from functools import cache
from typing import Any, LiteralString

from sqlalchemy import func, select, text, insert, UUID
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql.operators import or_

from agent.db.schema import UserScoreSchema, MeetScoreDBSchema
from api.schemas import UserUpdate
from db.constants import (
    DEFAULT_TIMEZONE_ID,
    PHOTO_PREVIEW_TYPE,
    ContactType,
    GoalName,
    PureGoalResultType,
    PureGoalResult,
)
from db.engineer import DbEngine
from db.enums import UserMatchStatus, MatchStatus
from db.exceptions import (
    RequestAlreadySent,
    RequestNotFound,
    UpdateUserActiveNotAllowed,
)
from db.model import (
    Category,
    Goal,
    MatchRequest,
    MatchRequestStatus,
    Skill,
    TimeQuant,
    User,
    UserContact,
    UserPhoto,
    UserSubscription,
    SubscriptionType,
    UserSetting,
    UserMatchState,
    Match,
    Timezone,
    MatchScore,
    MatchCriteria,
)
from db.model import UserTelegram as UserTelegramDB
from db.user_helper_repository import UserHelperRepository
from utils.auth.schemes import UserTelegram as UserTelegramScheme

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self):
        self.db = DbEngine()
        self.helper_repo = UserHelperRepository()

    @contextmanager
    def get_user_session(self):
        with self.db.get_session() as session:
            yield session

    def upset_contact(self, name: str, value: str, user_id: UUID) -> None:
        with self.db.get_session() as session:
            contact = (
                session.query(UserContact)
                .filter(
                    UserContact.user_id == user_id,
                    UserContact.contact_type == name,
                )
                .first()
            )

            if contact:
                contact.value = value
            else:
                contact = UserContact(user_id=user_id, contact_type=name, value=value)
                session.add(contact)

    def get_user_by_telegram_id(self, telegram_user_id: int) -> User | None:
        logger.debug(
            "Поиск пользователя c телеграм-идентификатором %d в базе данных...",
            telegram_user_id,
        )

        with self.db.get_session() as session:
            smt = (
                select(User)
                .join(UserTelegramDB)
                .where(UserTelegramDB.telegram_id == telegram_user_id)
                .options(
                    joinedload(User.contacts),
                    joinedload(User.skills),
                    joinedload(User.subscriptions).subqueryload(
                        UserSubscription.subscription_type
                    ),
                    joinedload(User.mentee_skills),
                    joinedload(User.mentor_skills),
                    joinedload(User.match_scores),
                    joinedload(User.telegram),
                    joinedload(User.settings),
                    joinedload(User.subscriptions),
                    joinedload(User.matches_received),
                    joinedload(User.matches_initiated),
                    joinedload(User.photos),
                    joinedload(User.goals),
                    joinedload(User.quants),
                    joinedload(User.timezone),
                )
                .limit(1)
            )
            result = session.execute(smt).unique().one_or_none()

        if result is not None:
            logger.info(
                "Пользователь c телеграм-идентификатором %d найден в базе данных.",
                telegram_user_id,
            )
            return result[0]
        else:
            logger.error(
                "Пользователь c телеграм-идентификатором %d не найден в базе данных.",
                telegram_user_id,
            )
            return None

    def list_user_matches(self, user_id: UUID) -> list[Match]:
        with self.db.get_session() as session:
            smt = (
                select(Match)
                .where(
                    or_(
                        Match.initiator_user_id == user_id,
                        Match.target_user_id == user_id,
                    )
                )
                .options(
                    joinedload(Match.match_criteria), joinedload(Match.match_scores)
                )
            )
            result = [m[0] for m in session.execute(smt).unique().all()]

        return result

    def get_user_profile_access(
        self, initiator_user_id: UUID, target_user_id: UUID
    ) -> bool:
        with self.db.get_session() as session:
            smt = (
                "SELECT 1 FROM users as u "
                "WHERE "
                "EXISTS (SELECT 1 FROM matches um WHERE um.target_user_id = :target_user_id AND um.initiator_user_id = :initiator_user_id) "
                "OR EXISTS (SELECT 1 FROM matches um WHERE um.target_user_id = :initiator_user_id AND um.initiator_user_id = :target_user_id) "
                "OR EXISTS (SELECT 1 FROM match_requests mr WHERE mr.target_user_id = :initiator_user_id AND mr.initiator_user_id = :target_user_id AND mr.status='APPROVED') "
                "OR EXISTS (SELECT 1 FROM match_requests mr WHERE mr.target_user_id = :target_user_id AND mr.initiator_user_id = :initiator_user_id AND mr.status='APPROVED') "
                "LIMIT 1 "
            )

            result = self._execute(
                session=session,
                statement=smt,
                params={
                    "initiator_user_id": initiator_user_id,
                    "target_user_id": target_user_id,
                },
            )

        return len(result.scalars().all()) > 0

    def get_user_by_id(self, user_id: UUID, extended: bool = False) -> User | None:
        logger.info(
            "Поиск пользователя c собственным идентификатором %s в базе данных...",
            user_id,
        )
        option_loads = [
            joinedload(User.contacts),
            joinedload(User.skills),
            joinedload(User.mentee_skills),
            joinedload(User.mentor_skills),
            joinedload(User.subscriptions).subqueryload(
                UserSubscription.subscription_type
            ),
            joinedload(User.match_scores),
            joinedload(User.settings),
            joinedload(User.telegram),
            joinedload(User.photos),
            joinedload(User.goals),
            joinedload(User.quants),
            joinedload(User.timezone),
        ]

        if extended:
            option_loads.append(joinedload(User.match_requests_sent))
            option_loads.append(joinedload(User.match_requests_received))

        with self.db.get_session() as session:
            smt = select(User).where(User.id == user_id).options(*option_loads).limit(1)
            result = session.execute(smt).unique().one_or_none()

        if result is not None:
            logger.info(
                "Пользователь c собственным идентификатором %s найден в базе данных.",
                user_id,
            )
            return result[0]
        else:
            logger.error(
                "Пользователь c собственным идентификатором %s не найден в базе данных.",
                user_id,
            )
            return None

    def list_users(self, limit: int) -> list[UUID] | None:
        logger.info("Список %s пользователей", limit)
        with self.db.get_session() as session:
            return [u[0] for u in session.query(User.id).limit(limit=limit).all()]

    def upsert_review(self, score: MeetScoreDBSchema, user_id: UUID):
        logger.debug(
            "Добавление отзыва в базу данных..., id встречи %s, id пользователя %s, оценка встречи %s, само ревью %s",
            score.meet_id,
            user_id,
            score.score,
            score.review,
        )
        with self.db.get_session() as session:
            smt = (
                select(MatchScore)
                .where(
                    MatchScore.match_id == score.meet_id, MatchScore.user_id == user_id
                )
                .limit(1)
            )
            review = session.execute(smt).unique().one_or_none()
            if review:
                review = review[0]
                review.score = score.score or review.score
                review.review = score.review or review.review
                session.execute(smt)
            else:
                session.add(
                    MatchScore(
                        match_id=score.meet_id,
                        user_id=user_id,
                        score=score.score,
                        review=score.review,
                    )
                )

    def get_active_user_subscription(
        self, user_id: UUID, session: Session | None = None
    ) -> UserSubscription | None:
        logger.debug(
            "Поиск подписки у пользователя c собственным идентификатором %s в базе данных...",
            user_id,
        )
        if session is None:
            with self.db.get_session() as session:
                return self._get_active_user_subscription(
                    user_id=user_id, session=session
                )
        else:
            return self._get_active_user_subscription(user_id=user_id, session=session)

    @staticmethod
    def _get_active_user_subscription(
        user_id: UUID, session: Session
    ) -> UserSubscription | None:
        logger.debug(
            "Поиск подписки у пользователя c собственным идентификатором %s в базе данных...",
            user_id,
        )
        smt = (
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .options(
                joinedload(UserSubscription.subscription_type),
            )
        )
        result = session.execute(smt).unique().one_or_none()

        if result is not None:
            logger.info("Подписка у пользователя %s найдена в базе данных.", user_id)
            return result[0]
        else:
            logger.debug(
                "Подписка у пользователя %s не найдена в базе данных.", user_id
            )
            return None

    @staticmethod
    def get_user_by_id_and_session(user_id: UUID, session: Session) -> User:
        smt = select(User).where(User.id == user_id)
        return session.execute(smt).unique().one_or_none()[0]

    def update_user_quants(self, user_id: UUID, quants: list[int]) -> User | None:
        logger.debug(
            "Изменение квантов календаря пользователя %s...\nНовые кванты: %s.",
            user_id,
            quants,
        )

        with self.db.get_session() as session:
            user = self.get_user_by_id_and_session(user_id=user_id, session=session)
            old_quants = deepcopy(user.quants)
            quants = (
                session.execute(select(TimeQuant).where(TimeQuant.id.in_(quants)))
                .unique()
                .all()
            )
            user.quants = [quant[0] for quant in quants]
            user.updated_at = datetime.datetime.now(datetime.UTC)
            session.add(user)

        logger.info(
            """Изменены кванты календаря пользователя %s.
            Старые кванты: %s.
            Новые кванты: %s.""",
            user_id,
            old_quants,
            user.quants,
        )

    def update_user_skills(self, user_id: UUID, skills: list[UUID]) -> User | None:
        logger.debug(
            "Изменение общих компетенций у пользователя %s...\nНовые общие компетенции: %s.",
            user_id,
            skills,
        )

        with self.db.get_session() as session:
            user = self.get_user_by_id_and_session(user_id=user_id, session=session)
            old_skills = deepcopy(user.skills)
            skills = (
                session.execute(select(Skill).where(Skill.id.in_(skills)))
                .unique()
                .all()
            )
            user.skills = [skill[0] for skill in skills]
            user.updated_at = datetime.datetime.now(datetime.UTC)
            session.add(user)

        logger.info(
            """Изменены общие компетенции у пользователя %s.
            Старые общие компетенции: %s.
            Новые общие компетенции: %s.""",
            user_id,
            old_skills,
            user.skills,
        )

    def update_user_mentor_skills(
        self, user_id: UUID, skills: list[UUID]
    ) -> User | None:
        logger.debug(
            """Изменение компетенций обучающего (mentor) у пользователя %s...
            Новые компетенции: %s.""",
            user_id,
            skills,
        )

        with self.db.get_session() as session:
            user = self.get_user_by_id_and_session(user_id=user_id, session=session)
            old_skills = deepcopy(user.mentor_skills)
            skills = (
                session.execute(select(Skill).where(Skill.id.in_(skills)))
                .unique()
                .all()
            )
            user.mentor_skills = [skill[0] for skill in skills]
            user.updated_at = datetime.datetime.now(datetime.UTC)
            session.add(user)

        logger.info(
            """Изменены компетенции обучающего (mentor) у пользователя %s.
            Старые компетенции обучаемого: %s.
            Новые компетенции обучаемого: %s.""",
            user_id,
            old_skills,
            user.mentor_skills,
        )

    def update_user_mentee_skills(
        self, user_id: UUID, skills: list[UUID]
    ) -> User | None:
        logger.debug(
            """Изменение компетенций обучаемого (mentee) у пользователя %s...
            Новые компетенции: %s.""",
            user_id,
            skills,
        )

        with self.db.get_session() as session:
            user = self.get_user_by_id_and_session(user_id=user_id, session=session)
            old_skills = deepcopy(user.mentee_skills)
            skills = (
                session.execute(select(Skill).where(Skill.id.in_(skills)))
                .unique()
                .all()
            )
            user.mentee_skills = [skill[0] for skill in skills]
            user.updated_at = datetime.datetime.now(datetime.UTC)
            session.add(user)

        logger.info(
            """Изменены компетенции обучаемого (mentee) у пользователя %s.
            Старые компетенции обучаемого: %s.
            Новые компетенции обучаемого: %s.""",
            user_id,
            old_skills,
            user.mentee_skills,
        )

    def update_user_goals(self, user_id: UUID, goals: list[UUID]) -> User | None:
        logger.debug(
            "Изменение целей пользователя %s...\nНовые цели: %s.", user_id, goals
        )

        with self.db.get_session() as session:
            user = self.get_user_by_id_and_session(user_id=user_id, session=session)
            old_goals = deepcopy(user.goals)
            goals = (
                session.execute(select(Goal).where(Goal.id.in_(goals))).unique().all()
            )
            user.goals = [val[0] for val in goals]
            user.updated_at = datetime.datetime.now(datetime.UTC)
            session.add(user)

        logger.info(
            """Изменены цели пользователя %s.
            Старые цели: %s.
            Новые цели: %s.
            """,
            user_id,
            old_goals,
            user.goals,
        )

    def update_user_data(self, user_data: UserUpdate, user_id: UUID) -> User | None:
        logger.debug(
            "Изменение личной информации пользователя %s...\nНовая информация: %s.",
            user_id,
            user_data,
        )

        with self.db.get_session() as session:
            smt = select(User).where(User.id == user_id).limit(1)
            user: User = session.execute(smt).one_or_none()[0]
            user.first_name = user_data.first_name or user.first_name
            user.last_name = user_data.last_name or user.last_name
            user.bio = user_data.bio or user.bio

            user.education = user_data.education or user.education
            user.experience= user_data.experience or user.education
            user.workplace = user_data.workplace or user.workplace
            user.birthday = user_data.birthday or user.birthday
            user.updated_at = datetime.datetime.now(datetime.UTC)

            if user_data.email:
                self._upsert_contact(
                    session=session,
                    user=user,
                    contact_type=ContactType.EMAIL,
                    value=user_data.email,
                )

            if user_data.phone:
                self._upsert_contact(
                    session=session,
                    user=user,
                    contact_type=ContactType.PHONE,
                    value=user_data.phone,
                )

            if user_data.telegram_username:
                smt = (
                    select(UserTelegramDB)
                    .where(UserTelegramDB.user_id == user_id)
                    .limit(1)
                )
                telegram_user = session.execute(smt).unique().one_or_none()[0]
                old_telegram_username: str = deepcopy(telegram_user.telegram_username)
                telegram_user.telegram_username = user_data.telegram_username
                session.add(telegram_user)
                logger.info(
                    """Изменена информация из Телеграма пользователя %s.
                    Старая информация: %s.
                    Новая информация: %s.""",
                    user_id,
                    old_telegram_username,
                    user_data.telegram_username,
                )

            if user_data.telegram_photo_url:
                smt = (
                    select(UserPhoto)
                    .where(UserPhoto.user_id == user_id)
                    .where(UserPhoto.photo_type == PHOTO_PREVIEW_TYPE)
                    .limit(1)
                )
                photo = session.execute(smt).unique().one_or_none()

                if photo is None:
                    photo = UserPhoto(
                        user_id=user.id,
                        photo_type=PHOTO_PREVIEW_TYPE,
                        photo_url=user_data.telegram_photo_url,
                        photo_s3_key="",
                    )
                    session.add(photo)
                    logger.info(
                        "Фотография пользователя %s отсутствует в базе данных. Новая фотография установлена.",
                        user_id,
                    )
                else:
                    photo[0].photo_url = user_data.telegram_photo_url
                    session.add(photo[0])
                    logger.info(
                        "Фотография пользователя %s найдена в базе данных и изменена.",
                        user_id,
                    )

            if user_data.timezone_id:
                user.timezone_id = user_data.timezone_id
            if user_data.location:
                user.location = user_data.location

            old_settings: UserSetting = user.settings
            if user_data.use_email_channel is not None:
                user.settings.use_email_channel = user_data.use_email_channel
            if user_data.use_telegram_channel is not None:
                user.settings.use_telegram_channel = user_data.use_telegram_channel
            if user_data.count_meets_in_week:
                user.settings.count_meets_in_week = user_data.count_meets_in_week
            if user_data.is_active:
                self._activate_user(session=session, user=user)
            if user_data.is_active == False:
                self._deactivate_user(user=user, session=session)

            session.add(user.settings)
            logger.info(
                """Изменены предпочтения пользователя %s.
                Старые предпочтения: %s.
                Новые предпочтения: %s.
                """,
                user,
                old_settings,
                user.settings,
            )
            session.add(user)
            session.flush()

        return user

    @staticmethod
    def _activate_user(user: User, session: Session):
        logger.debug("Активация пользователя %s...", user)

        email = [c for c in user.contacts if c.contact_type == ContactType.EMAIL]

        if not email or not email[0]:
            logger.error(
                "У пользователя %s в базе данных отсутствует адрес электронной почты.",
                user,
            )
            raise UpdateUserActiveNotAllowed(user_id=user.id)

        if not user.timezone:
            logger.error("У пользователя %s не установлен часовой пояс.", user)
            raise UpdateUserActiveNotAllowed(user_id=user.id)

        if not user.skills:
            logger.error("У пользователя %s отсутствуют общие компетенции.", user)
            raise UpdateUserActiveNotAllowed(user_id=user.id)

        if not user.goals:
            logger.error("У пользователя %s отсутствуют цели.", user)
            raise UpdateUserActiveNotAllowed(user_id=user.id)

        if not user.telegram:
            logger.error("У пользователя %s отсутствует Телеграм.", user)
            raise UpdateUserActiveNotAllowed(user_id=user.id)

        if not user.bio:
            logger.error(
                "У пользователя %s в базе данных отсутствует информация о себе.", user
            )
            raise UpdateUserActiveNotAllowed(user_id=user.id)

        if not user.quants:
            logger.error("У пользователя %s отсутствуют встречи.", user)
            raise UpdateUserActiveNotAllowed(user_id=user.id)

        user.settings.is_active = True
        session.add(user.settings)

        logger.info("Активирован пользователь %s.", user)

    @staticmethod
    def _deactivate_user(user: User, session: Session):
        user.settings.is_active = False
        session.add(user.settings)
        logger.info("Деактивирован пользователь %s.", user)

    @staticmethod
    def _upsert_contact(
        session: Session, user: User, contact_type: ContactType, value: str
    ):
        """Изменяет или добавляет значение контакта типа `contact_type` новым значением `value`."""

        logger.debug(
            """Изменение или добавление контакта типа %s у пользователя %s...
            Новое значение контакта: %s.""",
            contact_type,
            user,
            value,
        )

        contact = next(
            (c for c in user.contacts if c.contact_type == contact_type), None
        )
        if contact:
            old_value = deepcopy(contact.value)
            contact.value = value
            session.add(contact)

            logger.info(
                """Изменён контакт типа %s у пользователя %s.
                Старое значение контакта: %s.
                Новое значение контакта: %s.""",
                contact_type,
                user.id,
                old_value,
                value,
            )
        else:
            new_contact = UserContact(
                user_id=user.id,
                contact_type=contact_type,
                value=value,
            )
            session.add(new_contact)
            user.contacts.append(new_contact)

            logger.info(
                """Добавлен контакт типа %s у пользователя %s.
                Значение контакта: %s.""",
                contact_type,
                user.id,
                value,
            )

        session.flush()

    def save_user_profile_from_telegram(
        self, telegram_user: UserTelegramScheme, photo_s3_key
    ) -> UUID | None:
        logger.debug(
            "Добавление пользователя %s из Телеграма в базу данных...", telegram_user
        )

        with self.db.get_session() as session:
            user = User(
                first_name=telegram_user.first_name or "",
                last_name=telegram_user.last_name or "",
            )

            default_timezone = self._get_default_timezone(session)
            user.timezone = default_timezone
            session.add(user)
            session.flush()
            logger.info("Пользователь %s из Телеграма добавлен в базу данных.", user)

            photo = UserPhoto(
                photo_url=telegram_user.photo_url or "",
                photo_s3_key=photo_s3_key or "",
                photo_type=PHOTO_PREVIEW_TYPE,
                user_id=user.id,
            )
            telegram_user_ = UserTelegramDB(
                user_id=user.id,
                telegram_id=telegram_user.id,
                telegram_username=telegram_user.username,
            )
            settings = UserSetting(
                user_id=user.id,
                is_active=False,
                use_telegram_channel=True,
                use_email_channel=True,
            )

            session.add(settings)
            logger.info(
                "Предпочтение пользователя %s добавлены в базу данных.", settings
            )

            session.add(photo)
            logger.info("Фотография %s добавлена в базу данных.", photo)

            session.add(telegram_user_)
            logger.info(
                "Информация из Телеграма %s добавлена в базу данных.", telegram_user_
            )

            logger.info("Пользователь %s добавлен в базу данных.", telegram_user)

        return user.id

    @staticmethod
    def _get_default_timezone(session: Session) -> Any:
        smt = select(Timezone).where(Timezone.id == DEFAULT_TIMEZONE_ID)
        default_timezone = session.execute(smt).first()[0]

        return default_timezone

    def update_user_photo(self, photo_type: str, photo_url: str, user_id: UUID):
        logger.debug("Изменение фотографии пользователя %s в базе данных...", user_id)

        with self.db.get_session() as session:
            smt = (
                select(UserPhoto)
                .where(UserPhoto.user_id == user_id)
                .where(UserPhoto.photo_type == photo_type)
                .limit(1)
            )
            photo = session.execute(smt).one_or_none()
            if not photo:
                logger.debug(
                    "Фотография пользователя %s отсутствует в базе данных. Добавление...",
                    user_id,
                )
                photo = UserPhoto(
                    user_id=user_id,
                    photo_type=photo_type,
                    photo_url=photo_url,
                    photo_s3_key="",
                )
            else:
                logger.info(
                    "Фотография пользователя %s найдена в базе данных.", user_id
                )
                photo = photo[0]

            session.add(photo)
            logger.info("Фотография пользователя %s установлена.", user_id)

    def update_user_timezone(self, timezone_id: int, user_id: UUID):
        logger.debug(
            "Изменение часового пояса пользователя %s...\nНовый пояс: %s.",
            user_id,
            timezone_id,
        )

        with self.db.get_session() as session:
            user = self.get_user_by_id_and_session(user_id=user_id, session=session)
            old_timezone = deepcopy(user.timezone)
            new_timezone = session.execute(
                select(Timezone).where(Timezone.id == timezone_id)
            ).first()[0]
            user.timezone = new_timezone

        logger.info(
            """Изменён часовой пояс пользователя %s.
            Старый: %s.
            Новый: %s.""",
            user_id,
            old_timezone,
            new_timezone,
        )

    def update_user_location(self, location: str, user_id: UUID):
        with self.db.get_session() as session:
            user = self.get_user_by_id_and_session(user_id=user_id, session=session)
            user.location = location

    def _get_user_goal_ids(self, user_id: UUID, session: Session) -> set[UUID]:
        return set(
            g.id
            for g in self.get_user_by_id_and_session(
                user_id=user_id, session=session
            ).goals
        )

    def _pure_goals(self, user_goals: list[Goal]) -> list[Goal]:
        mentor_goal = self.helper_repo.get_goal_by_name(GoalName.MENTOR_GOAL)
        mentee_goal = self.helper_repo.get_goal_by_name(GoalName.MENTEE_GOAL)
        res = [None] * len(user_goals)
        for i, goal in enumerate(user_goals):
            if goal.id == mentor_goal.id:
                res[i] = mentee_goal
            elif goal.id == mentee_goal.id:
                res[i] = mentor_goal
            else:
                res[i] = goal

        return res

    def _pure_goal_ids(self, user_goals: set[UUID]) -> PureGoalResult:
        mentor_goal_id = self.helper_repo.get_goal_by_name(GoalName.MENTOR_GOAL).id
        mentee_goal_id = self.helper_repo.get_goal_by_name(GoalName.MENTEE_GOAL).id
        pured_goals = user_goals.difference([mentor_goal_id, mentee_goal_id])

        if len(pured_goals) == len(user_goals):
            return PureGoalResult(
                goal_ids=pured_goals,
                result_type=PureGoalResultType.MIX,
            )

        elif len(pured_goals):
            if mentor_goal_id in user_goals:
                pured_goals.add(mentee_goal_id)
            if mentee_goal_id in user_goals:
                pured_goals.add(mentor_goal_id)

            return PureGoalResult(
                goal_ids=pured_goals,
                result_type=PureGoalResultType.MIX,
            )
        else:
            if mentor_goal_id in user_goals and mentee_goal_id in user_goals:
                return PureGoalResult(
                    goal_ids={mentee_goal_id, mentor_goal_id},
                    result_type=PureGoalResultType.MENTOR_MENTEE,
                )
            if mentor_goal_id in user_goals:
                return PureGoalResult(
                    goal_ids={mentor_goal_id}, result_type=PureGoalResultType.MENTOR
                )

            return PureGoalResult(
                goal_ids={mentee_goal_id}, result_type=PureGoalResultType.MENTEE
            )

    def generate_manual_best_intersection_user_list(
        self,
        user_id: UUID,
        limit: int = 100,
    ) -> list[User]:
        with self.db.get_session() as session:
            user_goals = self._get_user_goal_ids(user_id=user_id, session=session)
            pure_goal_result = self._pure_goal_ids(
                user_goals=user_goals,
            )
            skill_filter_based_on_goal = self._skill_filter_for_goals(pure_goal_result)

            sql = (
                "SELECT *, skill_count*goal_count as score FROM ("
                "SELECT "
                "us.id as id, "
                "(SELECT count(*) FROM user_skills ss WHERE ss.user_id = us.id AND ss.skill_id IN (SELECT skill_id FROM user_mentor_skills so WHERE so.user_id=:user_id)) as skill_count, "
                "(SELECT count(*) FROM user_goals gs WHERE gs.user_id = us.id AND gs.goal_id IN ("
                + ",".join("'" + str(p) + "'" for p in pure_goal_result.goal_ids)
                + ")) as goal_count, "
                "(SELECT count(*) FROM user_mentee_skills uss WHERE uss.user_id = us.id AND uss.skill_id IN (SELECT skill_id FROM user_mentor_skills umso WHERE umso.user_id=:user_id)) as mentor_role, "
                "(SELECT count(*) FROM user_mentor_skills ums WHERE ums.user_id = us.id AND ums.skill_id IN (SELECT skill_id FROM user_mentee_skills usso WHERE usso.user_id=:user_id)) as mentee_role "
                "FROM users us "
                "JOIN user_quants q ON q.user_id = us.id "
                "JOIN user_settings uss ON uss.user_id = us.id "
                "WHERE "
                "q.quant_id IN (SELECT q_o.quant_id FROM user_quants q_o WHERE q_o.user_id=:user_id) "
                "AND NOT EXISTS (SELECT 1 FROM matches um WHERE um.initiator_user_id = us.id AND um.target_user_id = :user_id) "
                "AND NOT EXISTS (SELECT 1 FROM matches um WHERE um.target_user_id = us.id AND um.initiator_user_id = :user_id) "
                "AND uss.is_active "
                "AND us.id != :user_id) "
                "as ui "
                "WHERE goal_count>0 "
                + skill_filter_based_on_goal
                + "ORDER BY mentor_role, mentee_role, score, skill_count, goal_count DESC "
                "LIMIT :limit"
            )
            params = {"user_id": user_id, "limit": limit}
            user_ids = (
                self._execute(session=session, statement=sql, params=params)
                .scalars()
                .all()
            )
            user_ids = [u for u in user_ids]
            stm = (
                select(User)
                .where(User.id.in_(user_ids))
                .options(
                    joinedload(User.skills),
                    joinedload(User.mentee_skills),
                    joinedload(User.match_requests_received),
                    joinedload(User.match_requests_sent),
                    joinedload(User.mentor_skills),
                    joinedload(User.telegram),
                    joinedload(User.photos),
                    joinedload(User.goals),
                    joinedload(User.timezone),
                )
            )

            users = session.execute(stm).unique().all()
            if not users:
                logger.error("Не найдено рекоммендаций для пользователя: %s", user_id)

            return [u[0] for u in users]

    @staticmethod
    def _skill_filter_for_goals(pure_goal_result: PureGoalResult) -> str:
        match pure_goal_result.result_type:
            case PureGoalResultType.MENTOR:
                skill_filter_based_on_goal = " AND mentor_role>0 "
            case PureGoalResultType.MENTEE:
                skill_filter_based_on_goal = " AND mentee_role>0 "
            case PureGoalResultType.MENTOR_MENTEE:
                skill_filter_based_on_goal = " AND (mentor_role>0 OR mentee_role>0) "
            case _:
                skill_filter_based_on_goal = (
                    "AND (mentor_role>0 OR mentee_role>0 OR skill_count>0) "
                )
        return skill_filter_based_on_goal

    def create_match(
        self,
        initiator_user_id: UUID,
        target_user_id: UUID,
        quant_id: int,
        start_date: datetime.date,
        session: Session,
        video_link: str,
        match_status=MatchStatus.UNCOMPLETED,
    ) -> UUID:
        logger.debug(
            """%s создаёт встречу с %s...
            Желаемая дата: %s.
            Временной квант: %d.
            Ссылка: %s.""",
            initiator_user_id,
            target_user_id,
            start_date,
            quant_id,
            video_link,
        )

        match_date = self.create_match_datetime(
            quant_id=quant_id, session=session, start_date=start_date
        )
        match = Match(
            initiator_user_id=initiator_user_id,
            target_user_id=target_user_id,
            date_at=match_date,
            video_link=video_link,
            status=match_status,
            quant_id=quant_id,
        )
        session.add(match)
        session.flush()

        logger.info(
            "%s создал встречу %s с %s на %s.",
            initiator_user_id,
            match.id,
            target_user_id,
            match_date,
        )
        return match.id

    def cancel_match(self, match_id: UUID, user_id: UUID):
        logger.debug("%s отменяет встречу %s...", user_id, match_id)

        with self.db.get_session() as session:
            self.cancel_match_in_session(match_id, session, user_id)

    @staticmethod
    def cancel_match_in_session(match_id: UUID, session: Session, user_id: UUID):
        match = session.execute(select(Match).where(Match.id == match_id)).one_or_none()
        if match is None:
            logger.error("Встреча %s не найдена.", match_id)
            raise ValueError()
        match = match[0]
        if match.initiator_user_id == user_id:
            match.status = MatchStatus.CANCELED_BY_INITIATOR
            logger.info("Инициатор %s отменил встречу %s.", user_id, match_id)
        elif match.target_user_id == user_id:
            match.status = MatchStatus.CANCELED_BY_TARGET
            logger.info("Приглашённый %s отменил встречу %s.", user_id, match_id)
        else:
            logger.error(
                "Пользователь %s не назначен на встречу %s.", user_id, match_id
            )
            raise ValueError()
        session.add(match)

    def transfer_match_to_new_status(
        self,
        match_id: UUID,
        new_status=MatchStatus.COMPLETED,
        session: Session | None = None,
    ):
        if session:
            self._transfer_match_to_new_status(
                match_id=match_id, new_status=new_status, session=session
            )
        else:
            with self.db.get_session() as session:
                self._transfer_match_to_new_status(match_id, new_status, session)

    @staticmethod
    def _transfer_match_to_new_status(
        match_id: UUID, new_status: MatchStatus, session: Session
    ):
        logger.debug("Смена статуса встречи %s на %s...", match_id, new_status)

        match = session.execute(select(Match).where(Match.id == match_id)).one_or_none()
        if match is None:
            logger.error("Встреча %s не найдена.", match_id)
            raise ValueError()
        match = match[0]
        match.status = new_status
        session.add(match)

        logger.info("Статус встречи %s сменён на %s.", match_id, new_status)

    @staticmethod
    def create_match_datetime(
        quant_id: int, session: Session, start_date: datetime.date
    ) -> datetime.datetime:
        """Функция не учитывает, что дата встречи должна быть позже текущей хотя бы на 1 день."""

        quant = session.execute(
            select(TimeQuant).where(TimeQuant.id == quant_id)
        ).one_or_none()
        if quant is None:
            logger.error("Квант календаря %s не найден.", quant_id)
            raise ValueError()
        quant = quant[0]

        if not 0 <= quant.day <= 6:
            logger.error("Номер дня в кванте календаря должен быть от 0 до 6.")
            raise ValueError()
        if not 0 <= quant.hour <= 23:
            logger.error("Номер часа в кванте календаря должен быть от 0 до 23.")
            raise ValueError()

        week_day = start_date.weekday()

        if week_day <= quant.day:
            start_date = start_date + datetime.timedelta(quant.day - week_day)
        else:
            start_date = start_date + datetime.timedelta(7 + quant.day - week_day)

        return datetime.datetime(
            year=start_date.year,
            month=start_date.month,
            day=start_date.day,
            hour=quant.hour,
            minute=0,
            tzinfo=datetime.timezone.utc,
        )

    @staticmethod
    def get_or_create_match_state(user_id: UUID, session: Session) -> UserMatchState:
        user_state_match = session.execute(
            select(UserMatchState)
            .where(UserMatchState.user_id == user_id)
            .with_for_update()
        ).one_or_none()
        if user_state_match:
            return user_state_match[0]
        else:
            user_state_match = UserMatchState(
                user_id=user_id,
                current_status=UserMatchStatus.UNFILLED,
                next_status=UserMatchStatus.UNFILLED,
            )
            session.add(user_state_match)
            session.flush()

            return user_state_match

    @staticmethod
    def _execute(
        session: Session, statement: LiteralString, params: dict | None = None
    ):
        return session.execute(
            statement=text(statement), params=params if params else {}
        )

    def _get_random_timezone(self) -> Timezone:
        with self.db.get_session() as session:
            smt = select(Timezone).order_by(func.random()).limit(1)

            return session.execute(smt).first()[0]

    def generate_and_save_random_user(
        self, is_active: bool = None, bio: str = "Some Cool Bio"
    ) -> UUID:
        user_helper_repo = UserHelperRepository()

        with self.db.get_session() as session:
            user = User(
                first_name="Coder",
                last_name="Roast",
                id=uuid.uuid4(),
                bio=bio,
            )

            user.timezone = self._get_random_timezone()
            user.location = "Narnia"
            user.experience = random.randint(0, 10)
            session.add(user)
            session.flush()

            settings = UserSetting(
                user_id=user.id,
                is_active=random.choices([True, False], cum_weights=[0.9, 0.1])[0]
                if is_active is None
                else is_active,
                use_telegram_channel=True,
                use_email_channel=True,
            )
            session.add(settings)
            session.flush()

            self._upsert_contact(
                session=session,
                user=user,
                contact_type=ContactType.EMAIL,
                value=f"{user.id}@example.com",
            )
            user.quants = random.choices(
                population=user_helper_repo.list_quants(parent_session=session),
                k=random.randint(3, 10),
            )
            user.skills = random.choices(
                population=user_helper_repo.list_skills(parent_session=session),
                k=random.randint(1, 10),
            )

            session.add_all(user.skills)
            user.goals = random.choices(
                population=user_helper_repo.list_goals(parent_session=session),
                k=random.randint(1, 3),
            )

            user.mentor_skills = random.choices(
                population=user_helper_repo.list_skills(parent_session=session),
                k=random.randint(0, 3),
            )
            session.add_all(user.mentor_skills)

            user.mentee_skills = random.choices(
                population=user_helper_repo.list_skills(parent_session=session),
                k=random.randint(0, 3),
            )
            session.add_all(user.mentee_skills)

            photo = UserPhoto(
                photo_url="",
                photo_s3_key="",
                photo_type=PHOTO_PREVIEW_TYPE,
                user_id=user.id,
            )

            telegram_user_ = UserTelegramDB(
                user_id=user.id,
                telegram_id=hash(user.id) % 10**9,
                telegram_username="coder_roast",
            )
            session.add(photo)
            session.add(telegram_user_)

            session.merge(user)

            return user.id

    def accept_match(self, initiator_user_id: UUID, target_user_id: UUID):
        logger.debug("%s принимает запрос от %s...")

        with self.db.get_session() as session:
            smt = (
                select(MatchRequest)
                .where(
                    MatchRequest.initiator_user_id == target_user_id,
                    MatchRequest.target_user_id == initiator_user_id,
                )
                .limit(1)
            )
            match = session.execute(smt).unique().one_or_none()

            if not match:
                logger.error(
                    "Запрос на образование пары от %s к %s не найден.",
                    initiator_user_id,
                    target_user_id,
                )
                raise RequestNotFound(
                    user_id=target_user_id, target_user_id=initiator_user_id
                )

            match[0].status = MatchRequestStatus.APPROVED
            logger.info("%s принял запрос от %s.", initiator_user_id, target_user_id)

    def reject_match(self, initiator_user_id: UUID, target_user_id: UUID):
        logger.debug("%s отклоняет запрос от %s...")

        with self.db.get_session() as session:
            smt = (
                select(MatchRequest)
                .where(
                    MatchRequest.initiator_user_id == target_user_id,
                    MatchRequest.target_user_id == initiator_user_id,
                )
                .limit(1)
            )
            match = session.execute(smt).unique().one_or_none()

            if not match:
                logger.error(
                    "Запрос на образование пары от %s к %s не найден.",
                    initiator_user_id,
                    target_user_id,
                )
                raise RequestNotFound(
                    user_id=target_user_id, target_user_id=initiator_user_id
                )

            match[0].status = MatchRequestStatus.REJECTED
            logger.info("%s отклонил запрос от %s.", initiator_user_id, target_user_id)

    def send_match_request(self, initiator_user_id: UUID, target_user_id: UUID):
        logger.debug("%s отправляет запрос на образование пары к %s...")

        with self.db.get_session() as session:
            smt = (
                select(MatchRequest)
                .where(
                    MatchRequest.initiator_user_id == initiator_user_id,
                    MatchRequest.target_user_id == target_user_id,
                )
                .limit(1)
            )
            match = session.execute(smt).unique().one_or_none()
            if match is not None:
                logger.error(
                    "Запрос на образование пары от %s к %s уже есть в базе данных.",
                    initiator_user_id,
                    target_user_id,
                )
                raise RequestAlreadySent(
                    user_id=initiator_user_id, target_user_id=target_user_id
                )

            smt = (
                select(MatchRequest)
                .where(
                    MatchRequest.target_user_id == initiator_user_id,
                    MatchRequest.initiator_user_id == target_user_id,
                )
                .limit(1)
            )
            match = session.execute(smt).unique().one_or_none()

            if match is not None:
                logger.error(
                    "Запрос на образование пары от %s к %s уже есть в базе данных.",
                    target_user_id,
                    initiator_user_id,
                )
                raise RequestAlreadySent(
                    user_id=target_user_id, target_user_id=initiator_user_id
                )

            match = MatchRequest(
                initiator_user_id=initiator_user_id,
                target_user_id=target_user_id,
                status=MatchRequestStatus.PENDING,
            )

            session.add(match)
            logger.info(
                "%s отправил запрос на образование пары с %s.",
                initiator_user_id,
                target_user_id,
            )

    def get_match_request(
        self, initiator_user_id: UUID, target_user_id: UUID
    ) -> MatchRequest | None:
        logger.debug(
            "Поиск запроса на образование пары от %s к %s...",
            initiator_user_id,
            target_user_id,
        )

        with self.db.get_session() as session:
            smt = (
                select(MatchRequest)
                .where(
                    MatchRequest.initiator_user_id == initiator_user_id,
                    MatchRequest.target_user_id == target_user_id,
                )
                .limit(1)
            )
            match = session.execute(smt).unique().one_or_none()

        if match:
            logger.info(
                "Запрос на образование пары от %s к %s найден",
                initiator_user_id,
                target_user_id,
            )
            return match[0]
        else:
            logger.info(
                "Запрос на образование пары от %s к %s не найден",
                initiator_user_id,
                target_user_id,
            )
            return None

    def upgrade_user_subscription(
        self,
        user_id: UUID,
        subscription_type: SubscriptionType,
        valid_until: datetime.datetime,
    ):
        logger.debug(
            "Изменение подписки пользователя %s...\nНовая подписка: %s, действует до %s ",
            user_id,
            subscription_type,
            valid_until,
        )

        with self.db.get_session() as session:
            user = self.get_user_by_id_and_session(session=session, user_id=user_id)
            old_subs = deepcopy(user.subscriptions)
            user_sub = UserSubscription(
                user_id=user_id,
                subscription_type_id=subscription_type.id,
                subscription_until=valid_until,
            )
            session.add(user_sub)
            session.flush()

            user.subscriptions = [user_sub]
            session.add(user)

        logger.info(
            """Подписка пользователя %s сменена.
            Старая подписка: %s.
            Новая подписка: %s.""",
            user,
            old_subs,
            user.subscriptions,
        )

    def upsert_subscription_type(
        self,
        name: str,
        max_requests_per_week: int,
        max_matches_per_week: int,
    ):
        logger.debug(
            """Изменение или добавление типа подписки %s...
            Новое максимальное количество запросов на пары в неделю: %s.
            Новое максимальное количество пар в неделю: %s.""",
            name,
            max_requests_per_week,
            max_matches_per_week,
        )

        with self.db.get_session() as session:
            smpt = (
                select(SubscriptionType)
                .where(
                    SubscriptionType.name == name,
                )
                .limit(1)
            )
            found = session.execute(smpt).unique().one_or_none()

            if found:
                old_mm = deepcopy(found[0].max_matches_per_week)
                old_mr = deepcopy(found[0].max_requests_per_week)
                found[0].max_matches_per_week = max_matches_per_week
                found[0].max_requests_per_week = (max_requests_per_week,)
                session.add(found[0])
                session.flush()
                logger.info(
                    """Тип подписки %s изменён.
                    Старое максимальное количество запросов на пары в неделю: %s.
                    Старое максимальное количество пар в неделю: %s.
                    Новое максимальное количество запросов на пары в неделю: %s.
                    Новое максимальное количество пар в неделю: %s.""",
                    name,
                    old_mr,
                    old_mm,
                    max_requests_per_week,
                    max_matches_per_week,
                )

                return found[0]
            else:
                subscription_type = SubscriptionType(
                    name=name,
                    max_matches_per_week=max_matches_per_week,
                    max_requests_per_week=max_requests_per_week,
                )
                session.add(subscription_type)
                session.flush()
                logger.info(
                    """Добавлен тип подписки %s.
                    Новое максимальное количество запросов на пары в неделю: %s.
                    Новое максимальное количество пар в неделю: %s.""",
                    name,
                    max_requests_per_week,
                    max_matches_per_week,
                )

                return subscription_type

    def get_match_by_id(self, match_id) -> Match:
        with self.db.get_session() as session:
            return self._get_match_by_id_and_session(match_id, session)

    @staticmethod
    def _get_match_by_id_and_session(match_id, session: Session) -> Match:
        smtp = (
            select(Match)
            .where(Match.id == match_id)
            .options(joinedload(Match.match_scores), joinedload(Match.match_criteria))
        )
        return session.execute(smtp).unique().one_or_none()[0]

    def get_random_user(self, is_active: bool) -> UUID:
        # function for getting a random user for testing purpose only
        with self.db.get_session() as session:
            return (
                session.query(UserSetting.user_id)
                .where(UserSetting.is_active == is_active)
                .order_by(func.random())
                .limit(1)
                .one_or_none()[0]
            )

    def delete_contact(self, contact_name: str, user_id: UUID):
        with self.db.get_session() as session:
            session.query(UserContact).filter(
                UserContact.name == contact_name, UserContact.user_id == user_id
            ).delete()

    def get_user_contacts(self, user_id: UUID) -> list[UserContact]:
        with self.db.get_session() as session:
            return (
                session.query(UserContact).filter(UserContact.user_id == user_id).all()
            )

    def create_match_criteria(
        self,
        initiator_user_id: UUID,
        target_user_id: UUID,
        distance: float,
        session: Session,
        match_id: UUID,
    ):
        initiator_user = self.get_user_by_id_and_session(
            user_id=initiator_user_id, session=session
        )
        target_user = self.get_user_by_id_and_session(
            user_id=target_user_id, session=session
        )
        i_goals = self._pure_goals(user_goals=initiator_user.goals)
        i_match_criteria = MatchCriteria(
            common_skills=list(
                s.name
                for s in set(initiator_user.skills).intersection(target_user.skills)
            ),
            common_goals=list(
                g.name for g in set(i_goals).intersection(target_user.goals)
            ),
            mentor_role=list(
                s.name
                for s in set(initiator_user.mentor_skills).intersection(
                    target_user.mentee_skills
                )
            ),
            mentee_role=list(
                s.name
                for s in set(initiator_user.mentee_skills).intersection(
                    target_user.mentor_skills
                )
            ),
            user_id=initiator_user_id,
            match_id=match_id,
            cosine_distance=distance,
        )
        session.add(i_match_criteria)
        t_goals = self._pure_goals(user_goals=target_user.goals)
        t_match_criteria = MatchCriteria(
            common_skills=list(
                s.name
                for s in set(initiator_user.skills).intersection(target_user.skills)
            ),
            common_goals=list(
                g.name for g in set(t_goals).intersection(initiator_user.goals)
            ),
            mentor_role=list(
                s.name
                for s in set(initiator_user.mentee_skills).intersection(
                    target_user.mentor_skills
                )
            ),
            mentee_role=list(
                s.name
                for s in set(initiator_user.mentor_skills).intersection(
                    target_user.mentee_skills
                )
            ),
            user_id=target_user_id,
            match_id=match_id,
            cosine_distance=distance,
        )
        session.add(t_match_criteria)

    @staticmethod
    def get_quant_id_by_hour_and_day(hour: int, day: int, session: Session) -> int:
        return (
            session.query(TimeQuant)
            .filter(TimeQuant.hour == hour, TimeQuant.day == day)
            .first()
            .id
        )

    @staticmethod
    def get_match_by_id_and_sesion(match_id: UUID, session: Session):
        return session.query(Match).filter(Match.id == match_id).first()
