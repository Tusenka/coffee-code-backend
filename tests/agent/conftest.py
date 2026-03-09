import datetime
import random
from contextlib import _GeneratorContextManager
from typing import Callable, Any, Generator
from unittest.mock import Mock
from uuid import UUID

import pytest

from agent.db.agent_repository import UserAgentRepository
from agent.metrics.config import init_loki, init_metrics, init_tracing
from agent.scheduler.agent_match_status_updater import AgentMatchStatusUpdater
from agent.scheduler.agent_notification import AgentNotification
from agent.service.agent_recommendation_service import AgentRecommendationService
from agent.service.yandex_video_service import YandexVideoService
from db.model import Match
from db.user_helper_repository import UserHelperRepository
from db.user_repository import UserRepository
from service.model import User
from service.notification_service import NotificationService
from tests.helpers import HelperDataLoader


@pytest.fixture(scope="session")
def user_repo() -> UserRepository:
    return UserRepository()


@pytest.fixture(scope="session")
def user_helper_repo() -> UserHelperRepository:
    return UserHelperRepository()


@pytest.fixture(scope="session")
def yandex_video_service_mock():
    mock = Mock(spec=YandexVideoService)
    mock.get_video.return_value = "mock_video"

    return mock


@pytest.fixture(scope="session")
def notification_service_mock():
    return Mock(spec=NotificationService)


@pytest.fixture(scope="session")
def agent_notification_mock():
    return Mock(spec=AgentNotification)


@pytest.fixture(scope="session")
def agent_recommendation_service(
    agent_notification_mock: AgentNotification,
    yandex_video_service_mock: YandexVideoService,
):
    return AgentRecommendationService(
        agent_notification=agent_notification_mock,
        video_service=yandex_video_service_mock,
    )


@pytest.fixture(scope="session")
def agent_match_status_updater():
    return AgentMatchStatusUpdater()


@pytest.fixture(scope="session")
def agent_repo():
    return UserAgentRepository()


@pytest.fixture(scope="function")
def get_activated_user(
    agent_repo: UserAgentRepository, prepare_data
) -> Callable[[], User | None]:
    def func():
        user_id = HelperDataLoader.get_random_user(is_active=True, user_repo=agent_repo)
        user = agent_repo.get_user_by_id(user_id=user_id)

        return user

    return func


@pytest.fixture(scope="function")
def get_not_active_user(
    agent_repo: UserAgentRepository, prepare_data
) -> Callable[[], User | None]:
    def func():
        user_id = HelperDataLoader.get_random_user(
            user_repo=agent_repo, is_active=False
        )
        user = agent_repo.get_user_by_id(user_id=user_id)

        return user

    return func


@pytest.fixture(scope="function")
def get_skill(
    user_helper_repo: UserHelperRepository, prepare_data
) -> Callable[[], UUID]:
    def func():
        return user_helper_repo.get_random_skill().id

    return func


@pytest.fixture(scope="session")
def get_match(
    agent_recommendation_service: AgentRecommendationService,
    prepare_data,
    agent_repo: UserAgentRepository,
) -> Callable[[UUID, UUID], Match]:
    def func(
        initiator_user_id: UUID,
        target_user_id: UUID,
        quant_id: int = -1,
        start_date: datetime.datetime = None,
        distance: float = None,
    ):
        with agent_repo.get_user_session() as session:
            start_date = (
                datetime.datetime.now(datetime.UTC)
                if start_date is None
                else start_date
            )
            if quant_id == -1:
                quant_id = agent_repo.get_quant_id_by_hour_and_day(
                    hour=start_date.hour, day=start_date.weekday(), session=session
                )
            if distance is None:
                distance = random.random()

            match_id = agent_repo.create_match(
                initiator_user_id=initiator_user_id,
                target_user_id=target_user_id,
                quant_id=quant_id,
                start_date=start_date,
                session=session,
                video_link="mock",
            )

            agent_repo.create_match_criteria(
                initiator_user_id=initiator_user_id,
                target_user_id=target_user_id,
                match_id=match_id,
                distance=distance,
                session=session,
            )
            session.flush()
            return agent_repo.get_match_by_id_and_sesion(
                match_id=match_id, session=session
            )

    return func


@pytest.fixture(scope="function")
def session(
    agent_repo: UserAgentRepository,
) -> Generator[_GeneratorContextManager[Any, None, None] | Any, Any, None]:
    with agent_repo.db.get_session() as session:
        yield session


@pytest.fixture(scope="session", autouse=True)
def prepare_data(
    user_helper_repo: UserHelperRepository,
    agent_repo: UserAgentRepository,
    agent_recommendation_service: AgentRecommendationService,
    request,
) -> None:
    init_loki()

    init_metrics()
    init_tracing()

    if request.config.getoption("--skip-load"):
        return
    HelperDataLoader.load_helper_data(user_helper_repo=user_helper_repo)
    HelperDataLoader.generate_user_profiles(user_repo=agent_repo, count=1351)
    with agent_repo.get_user_session() as session:
        agent_recommendation_service.generate_and_update_embeddings(session)
