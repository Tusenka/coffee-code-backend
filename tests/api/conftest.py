import datetime
import random
from typing import Callable
from uuid import UUID

import pytest
from httpx import Cookies
from pydantic import TypeAdapter
from starlette.testclient import TestClient

from api.app import app
from db.constants import ContactType
from db.model import UserContact, Match
from db.user_helper_repository import UserHelperRepository
from db.user_repository import UserRepository
from service.model import Timezone, Goal, Skill, User, UserProfile
from service.recommendation_service import RecommendationService
from service.subsciption import SubscriptionService
from service.timequant_models import UserInterval
from service.user_service import UserService
from tests.api.constants import (
    CORRECT_TIMEZONE_ID,
    CORRECT_USER,
    USER_UPDATE_DATA,
    CORRECT_EMAIL,
    API_VERSION,
)
from tests.helpers import HelperDataLoader


@pytest.fixture(scope="session")
def user_repo() -> UserRepository:
    return UserRepository()


@pytest.fixture(scope="session")
def user_helper_repo() -> UserHelperRepository:
    return UserHelperRepository()


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)  # Assuming 'app' is your FastAPI application instance


@pytest.fixture(scope="session")
def user_service() -> UserService:
    return UserService()  # Assuming 'app' is your FastAPI application instance


@pytest.fixture
def jwt_cookies(client) -> Cookies:
    return client.post(f"{API_VERSION}/login", json=CORRECT_USER.model_dump()).cookies


@pytest.fixture
def skill(user_helper_repo: UserHelperRepository, prepare_data) -> Skill:
    return Skill.from_dao(user_helper_repo.get_random_skill())


@pytest.fixture
def goal(user_helper_repo: UserHelperRepository, prepare_data) -> Goal:
    return Goal.from_dao(user_helper_repo.get_random_goal())


@pytest.fixture(scope="session")
def timezone(user_helper_repo: UserHelperRepository, prepare_data) -> Timezone:
    return Timezone.from_dao(user_helper_repo.get_random_timezone())


@pytest.fixture
def intervals(
    user_helper_repo: UserHelperRepository, prepare_data
) -> list[UserInterval]:
    random_intervals = []
    for i in range(random.randint(1, 3)):
        day = random.randint(1, 7)
        start_hour = random.randint(0, 22)
        end_hour = random.randint(start_hour + 1, 24)
        random_intervals.append(
            UserInterval(day=day, startHour=start_hour, endHour=end_hour)
        )

    return random_intervals


@pytest.fixture(scope="session", autouse=True)
def prepare_data(
    user_helper_repo: UserHelperRepository, user_repo: UserRepository
) -> None:
    pass
    HelperDataLoader.load_helper_data(user_helper_repo=user_helper_repo)
    HelperDataLoader.generate_user_profiles(user_repo=user_repo)


@pytest.fixture
def get_user_profile(
    client: TestClient, jwt_cookies: Cookies
) -> Callable[[], UserProfile]:
    def ans():
        response = client.get(url=f"{API_VERSION}/profile", cookies=jwt_cookies)
        return TypeAdapter(UserProfile).validate_json(response.json())

    return ans


@pytest.fixture(scope="function")
def get_current_user(
    user_repo: UserRepository,
):
    def ans():
        user = user_repo.get_user_by_telegram_id(CORRECT_USER.id)
        contact = UserContact(
            value=CORRECT_EMAIL, contact_type=ContactType.EMAIL, user_id=user.id
        )

        user.contacts = [contact]
        return user

    return ans


@pytest.fixture()
def subscription_service() -> SubscriptionService:
    return SubscriptionService()


@pytest.fixture()
def correct_user(user_repo: UserRepository) -> User:
    user = user_repo.get_user_by_telegram_id(CORRECT_USER.id)

    return user


@pytest.fixture(scope="function")
def enrich_user_tags(
    user_repo: UserRepository,
    user_helper_repo: UserHelperRepository,
    subscription_service: SubscriptionService,
) -> None:
    user = user_repo.get_user_by_telegram_id(CORRECT_USER.id)
    quant_ids = random.choices(
        population=[x.id for x in user_helper_repo.list_quants()], k=20
    )
    goals = random.choices(
        population=[x.id for x in user_helper_repo.list_goals()], k=3
    )
    skills_ids = random.choices(
        population=[x.id for x in user_helper_repo.list_skills()], k=5
    )
    mentor_skills_ids = random.choices(
        population=[x.id for x in user_helper_repo.list_skills()], k=3
    )
    mentee_skill_ids = random.choices(
        population=[x.id for x in user_helper_repo.list_skills()], k=3
    )

    user_repo.update_user_skills(skills=skills_ids, user_id=user.id)
    user_repo.update_user_mentor_skills(skills=mentor_skills_ids, user_id=user.id)
    user_repo.update_user_mentee_skills(skills=mentee_skill_ids, user_id=user.id)
    user_repo.update_user_goals(goals=goals, user_id=user.id)
    user_repo.update_user_quants(quants=quant_ids, user_id=user.id)
    subscription_service.upsert_user_subscriptions(
        user_id=user.id,
        name="Test",
        max_requests_per_week=1000,
        max_matches_per_week=10000,
        valid_until=datetime.datetime.now() + datetime.timedelta(days=10),
    )


@pytest.fixture(scope="session", autouse=True)
def upgrade_user_data(
    user_repo: UserRepository,
    user_helper_repo: UserHelperRepository,
    timezone: Timezone,
) -> None:
    for user_data in (USER_UPDATE_DATA,):
        if user_data.timezone_id == CORRECT_TIMEZONE_ID:
            user_data.timezone_id = timezone.id


@pytest.fixture(scope="session", autouse=True)
def recommendation_service() -> RecommendationService:
    return RecommendationService()


@pytest.fixture(scope="function")
def get_user_with_email(
    user_repo: UserRepository, subscription_service: SubscriptionService
) -> Callable[[str], User]:
    def func(email: str):
        user_id = HelperDataLoader.get_random_user(user_repo=user_repo)
        user = user_repo.get_user_by_id(user_id=user_id, extended=True)
        contact = next(
            (c for c in user.contacts if c.contact_type == ContactType.EMAIL), None
        )
        contact.value = email

        return user

    return func


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
