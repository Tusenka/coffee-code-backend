import datetime
import os
import random
import uuid
from typing import Callable
from unittest import mock
from uuid import UUID

import pytest

from api.schemas import UserUpdate
from db.constants import ContactType
from db.model import User, Match
from db.user_helper_repository import UserHelperRepository
from db.user_repository import UserRepository
from service.catalog_service import CatalogService
from service.model import Skill, Goal, Timezone
from service.notification_service import NotificationService
from service.recommendation_service import RecommendationService
from service.timequant_models import TimeQuant
from service.timequant_service import UserInterval, TimeQuantService
from service.user_service import UserService
from tests.helpers import HelperDataLoader
from utils.auth.schemes import UserTelegram
from utils.auth.validator import _generate_hash

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


@pytest.fixture(scope="session")
def user_repo() -> UserRepository:
    return UserRepository()


@pytest.fixture(scope="session")
def user_helper_repo() -> UserHelperRepository:
    return UserHelperRepository()


@pytest.fixture(scope="session")
def timezone_serivce() -> TimeQuantService:
    return TimeQuantService()


@pytest.fixture
def skill(user_helper_repo: UserHelperRepository, prepare_data) -> Skill:
    return Skill.from_dao(user_helper_repo.get_random_skill())


@pytest.fixture(scope="session")
def get_skill_id(
    user_helper_repo: UserHelperRepository, prepare_data
) -> Callable[[], UUID]:
    def func():
        return user_helper_repo.get_random_skill().id

    return func


@pytest.fixture
def goal(user_helper_repo: UserHelperRepository, prepare_data) -> Goal:
    return Goal.from_dao(user_helper_repo.get_random_goal())


@pytest.fixture(scope="session")
def random_timezone(user_helper_repo: UserHelperRepository, prepare_data) -> Timezone:
    return Timezone.from_dao(user_helper_repo.get_random_timezone())


@pytest.fixture
def quants(user_helper_repo: UserHelperRepository, prepare_data) -> list[TimeQuant]:
    return random.choices(population=user_helper_repo.list_quants(), k=3)


@pytest.fixture
def user_local_intervals(
    user_helper_repo: UserHelperRepository, prepare_data
) -> list[UserInterval]:
    return [_get_random_interval() for _ in range(random.randrange(3, 10))]


def _get_random_interval() -> UserInterval:
    start_hour = random.randrange(0, 23)
    end_hour = random.randrange(start_hour + 1, 24)
    day = random.randrange(1, 7)

    return UserInterval(day=day, startHour=start_hour, endHour=end_hour)


@pytest.fixture(scope="function")
def get_activated_user(
    user_repo: UserRepository, prepare_data
) -> Callable[[], User | None]:
    def func():
        user_id = HelperDataLoader.get_random_user(is_active=True, user_repo=user_repo)
        user = user_repo.get_user_by_id(user_id=user_id, extended=True)

        return user

    return func


@pytest.fixture(scope="session")
def get_match(
    prepare_data,
    user_repo: UserRepository,
) -> Callable[[UUID, UUID], Match]:
    def func(
        initiator_user_id: UUID,
        target_user_id: UUID,
        quant_id: int = -1,
        start_date: datetime.datetime = None,
        distance: float = None,
    ):
        with user_repo.get_user_session() as session:
            start_date = (
                datetime.datetime.now(datetime.UTC)
                if start_date is None
                else start_date
            )
            if quant_id == -1:
                quant_id = user_repo.get_quant_id_by_hour_and_day(
                    hour=start_date.hour, day=start_date.weekday(), session=session
                )
            if distance is None:
                distance = random.random()

            match_id = user_repo.create_match(
                initiator_user_id=initiator_user_id,
                target_user_id=target_user_id,
                quant_id=quant_id,
                start_date=start_date,
                session=session,
                video_link="mock",
            )

            user_repo.create_match_criteria(
                initiator_user_id=initiator_user_id,
                target_user_id=target_user_id,
                distance=distance,
                session=session,
                match_id=match_id,
            )
            session.flush()
            return user_repo.get_match_by_id_and_sesion(
                match_id=match_id, session=session
            )

    return func


@pytest.fixture(scope="function")
def get_user_with_email(
    user_repo: UserRepository, prepare_data
) -> Callable[[str], User | None]:
    def func(email: str):
        user_id = HelperDataLoader.get_random_user(user_repo)
        user = user_repo.get_user_by_id(user_id=user_id, extended=True)
        contact = next(
            (c for c in user.contacts if c.contact_type == ContactType.EMAIL), None
        )
        contact.value = email

        return user

    return func


@pytest.fixture(scope="session")
def recommendation_service(
    notification_service: NotificationService,
) -> RecommendationService:
    return RecommendationService(notification_service=notification_service)


@pytest.fixture(scope="session")
def notification_service() -> NotificationService:
    notification_service_ = NotificationService()
    return mock.Mock(wraps=notification_service_)


@pytest.fixture(scope="session")
def user_service() -> UserService:
    return UserService()


@pytest.fixture(scope="session")
def catalog_service() -> CatalogService:
    return CatalogService()


@pytest.fixture(scope="session")
def telegram_user_factory(prepare_data) -> Callable[[], UserTelegram]:
    def ans():
        result = UserTelegram(
            id=random.randint(0, 10**9),
            first_name="John",
            last_name="Doe",
            username="johndoe",
        )
        result.hash = _generate_hash(data=result.model_dump(), token=TELEGRAM_TOKEN)

        return result

    return ans


@pytest.fixture(scope="session")
def user() -> UserService:
    return UserService()


@pytest.fixture(scope="session")
def correct_update_user_data(random_timezone: Timezone):
    return UserUpdate(
        bio="some cool bio",
        first_name="Alex updated",
        last_name="Anonym updated",
        telegram_username="irina_tusenka_new",
        telegram_photo_url="https://disk.yandex.com/i/zG-QsvhbDfXOPA",
        phone="+79269693374",
        timezone_id=random_timezone.id,
        location=str(uuid.uuid4()),
        email="admin@coffee-code.ru",
        education="MEPHI",
        experience=10,
        workplace="OZON.tech",
        birthday=datetime.date(year=2000, month=1, day=1),
        is_active=True,
        use_email_channel=True,
        use_telegram_channel=True,
    )


@pytest.fixture(scope="session")
def empty_update_user_data(random_timezone: Timezone):
    return UserUpdate()


@pytest.fixture(scope="session")
def activate_update_user_data(random_timezone: Timezone):
    return UserUpdate(is_active=True)
