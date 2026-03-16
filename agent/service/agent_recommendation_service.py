import dataclasses
import datetime
import logging
import random
import time
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from agent.db.agent_repository import UserAgentRepository
from agent.db.schema import UserScoreSchema
from agent.metrics.instruments import (
    record_match_generated,
    record_error,
    record_user_processed,
)
from agent.metrics.utils import perf
from agent.ml.embedding_model import EmbeddingModel
from agent.scheduler.agent_notification import AgentNotification
from agent.service.ivideo_service import IVideoService
from agent.service.yandex_video_service import YandexVideoService
from db.enums import UserMatchStatus
from db.model import Match, User
from service.subsciption import SubscriptionService

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class AgentRecommendationService:
    agent_repo: UserAgentRepository = UserAgentRepository()
    agent_notification: AgentNotification = dataclasses.field(
        default_factory=AgentNotification
    )
    subscription_service: SubscriptionService = dataclasses.field(
        default_factory=SubscriptionService
    )
    model: EmbeddingModel = dataclasses.field(default_factory=EmbeddingModel)
    video_service: IVideoService = dataclasses.field(default_factory=YandexVideoService)

    @perf("generate_matches")
    def generate_matches(self):
        """Генерация эмбедингов и замеры времени генерации."""

        with self.agent_repo.get_user_session() as session:
            self.generate_and_update_embeddings(session=session)

        self.agent_repo.reset_match_states()

        # Строгий подбор пар.
        user_ids = self.agent_repo.list_unmatched_user_ids()
        logger.debug(
            "Начат строгий подбор паросочетаний для %d пользователей.", len(user_ids)
        )
        count_ = 0
        start_time = time.perf_counter()

        for user_id in user_ids:
            self._generate_match_for_user(user_id=user_id, strict=True)

            record_user_processed()
            count_ += 1
            if count_ % 100 == 0:  # Печать на каждую сотню обработанных пользователей.
                logger.debug(
                    "Создано %d пар. Прошло %d секунд...",
                    count_,
                    time.perf_counter() - start_time,
                )

        logger.debug(
            "Окончен строгий подбор паросочетаний для %d пользователей. Подбор %d занял секунд.",
            len(user_ids),
            time.perf_counter() - start_time,
        )

        # Нестрогий подбор пар.
        user_ids = self.agent_repo.list_unmatched_user_ids(strict=False)
        logger.debug(
            "Начат нестрогий подбор паросочетаний для %d пользователей.", len(user_ids)
        )
        count_ = 0
        start_time = time.perf_counter()

        for user_id in user_ids:
            self._generate_match_for_user(user_id=user_id, strict=False)

            record_user_processed()
            count_ += 1
            if count_ % 100 == 0:  # Печать на каждую сотню обработанных пользователей.
                logger.debug(
                    "Создано %d пар. Прошло %d секунд...",
                    count_,
                    time.perf_counter() - start_time,
                )

        logger.debug(
            "Окончен нестрогий подбор паросочетаний для %d пользователей. Подбор %d занял секунд.",
            len(user_ids),
            time.perf_counter() - start_time,
        )

        #
        logger.debug(
            "Начат нестрогий подбор паросочетаний для %d пользователей.", len(user_ids)
        )

        # Для пользователей для которых нет пар предлагается ручной поиск

        user_ids = self.agent_repo.list_unmatched_user_ids(strict=False)
        logger.debug(
            "Начат ручной поиск для %d пользователей для которых не найдено ни одного паросочетания.",
            len(user_ids),
        )
        for user_id in user_ids:
            manual_result = self.agent_repo.generate_manual_best_intersection_user_list(
                user_id, strict=True
            )
            if not manual_result:
                manual_result = (
                    self.agent_repo.generate_manual_best_intersection_user_list(
                        user_id=user_id,
                    )
                )
            logger.debug(
                " Ручной поиск для %d дал %d количество пользователей.",
                user_id,
                len(manual_result),
            )
            self.agent_notification.add_match_event(
                match=None,
                user=self.agent_repo.get_user_by_id(user_id=user_id),
                manual_result=manual_result,
                target_user=None,
            )

    def _generate_match_for_user(self, strict: bool, user_id: UUID):
        logger.debug("Агент начинает предлагать пару пользователю %s...", user_id)
        try:
            with self.agent_repo.block_and_get_user_session_by_user_id(
                user_id=user_id
            ) as session:
                self.agent_repo.mark_user_match_state(
                    user_id=user_id,
                    session=session,
                    status=UserMatchStatus.EVALUATION,
                )
                session.commit()
                selected = self._choose_pair(
                    user_id=user_id, session=session, strict=strict
                )
                target_user_id = selected.user_id if selected else None
                assert target_user_id, (
                    f"Агенту не удалось предложить пару пользователю {user_id}."
                )
                if (
                    self._is_already_matching(session=session, user_id=user_id)
                    or self._is_already_matching(
                        session=session, user_id=target_user_id
                    )
                ) and strict:
                    logger.error(
                        "Агент уже предложил пару для пользователя %s с %s.",
                        user_id,
                        target_user_id,
                    )
                    record_error(error_type="match_generation_already_exists")
                    return

                session.flush()
                initiator_user = self.agent_repo.get_user_by_id(user_id=user_id)
                target_user = self.agent_repo.get_user_by_id(user_id=target_user_id)
                excluded_intervals = []
                if not strict:
                    excluded_intervals = self.agent_repo.list_busy_user_intervals(
                        session=session, user_id=target_user.id
                    )
                quant_id = self._choose_interval(
                    initiator_user=initiator_user,
                    target_user=target_user,
                    excluded_intervals=excluded_intervals,
                )
                today = self._get_start_date()

                match_id = self._create_match(
                    initiator_user=initiator_user,
                    target_user=target_user,
                    session=session,
                    quant_id=quant_id,
                    today=today,
                )
                self.agent_repo.create_match_criteria(
                    initiator_user_id=initiator_user.id,
                    target_user_id=target_user.id,
                    match_id=match_id,
                    session=session,
                    distance=selected.cosine_distance,
                )
                logger.info(
                    "Агент предложил пару для пользователя %s с %s.",
                    user_id,
                    target_user_id,
                )
                record_match_generated(strict=strict)
        except Exception as e:
            logger.exception(
                "Агент столкнулся с ошибкой при предложении пары для %s. Пользователь проигнорирован.\n%s",
                user_id,
                e,
            )
            record_error(error_type="match_generation")

    @perf("create_for_already_choosen")
    def _create_match(
        self,
        initiator_user: User,
        target_user: User,
        session: Session,
        quant_id: int,
        today: date,
    ):
        logger.debug(
            """Агент начинает создание пары для пользователя %s с %s...
            Квант %d. Дата: %s.""",
            initiator_user.id,
            target_user.id,
            quant_id,
            today,
        )
        self._mark_user_match_state(
            session, UserMatchStatus.EVALUATION, initiator_user.id
        )
        self._mark_user_match_state(session, UserMatchStatus.EVALUATION, target_user.id)

        video_link = self.video_service.get_video()
        match_id = self.agent_repo.create_match(
            initiator_user_id=initiator_user.id,
            target_user_id=target_user.id,
            quant_id=quant_id,
            start_date=today,
            video_link=video_link,
            session=session,
        )

        session.flush()

        match = self.agent_repo.get_match_by_id(match_id=match_id)
        self.agent_notification.add_match_event(
            user=initiator_user, target_user=target_user, match=match
        )
        self._mark_user_match_state(session, UserMatchStatus.FILLED, initiator_user.id)
        self._mark_user_match_state(session, UserMatchStatus.FILLED, target_user.id)

        logger.debug(
            """Агент создал пару для пользователя %s с %s...
            Квант %d. Дата: %s.""",
            initiator_user.id,
            target_user.id,
            quant_id,
            today,
        )
        return match_id

    def _mark_user_match_state(
        self, session: Session, status: UserMatchStatus, target_user_id
    ):
        self.agent_repo.mark_user_match_state(
            user_id=target_user_id,
            status=status,
            session=session,
        )

    def _is_already_matching(self, session: Session, user_id: UUID) -> bool:
        return (
            self.agent_repo.get_user_match_state(
                session=session, user_id=user_id
            ).current_status
            != UserMatchStatus.UNFILLED
        )

    @perf("choose_agent_pair")
    def _choose_pair(
        self, user_id: UUID, session: Session, strict: bool = True
    ) -> UserScoreSchema | None:
        """Процесс выбора кандидата в пару к данному.

        Args:
            user_id: Идентификатор пользователя, кому нужна пара.
            session: Сессия базы данных.
            strict: Включить строгий поиск? Если `True`, то при учитываются только те, кто без пока пары.

        Returns:
            UUID выбранного пользователя.
        """
        logger.debug(
            "Агент начал выбор подходящего кандидата в пару к %s... Строгий поиск: %s.",
            user_id,
            strict,
        )

        candidate_scores = self.agent_repo.generate_agent_matches(
            user_id=user_id,
            session=session,
            strict=strict,
            max_cos=0.2 if strict else 0.5,
        )
        if not candidate_scores:
            logger.error("Агент не смог подобрать кандидата в пару к %s.", user_id)
            return None

        # Случайно-взвешенный выбор. Самая высокая оценка (самый низкий индекс) дают самый большой вес.
        weights = [(len(candidate_scores) - i) for i in range(len(candidate_scores))]
        selected = random.choices(candidate_scores, weights=weights, k=1)[0]

        logger.info(
            "Агент смог подобрать кандидата %s в пару к %s", selected.user_id, user_id
        )
        return selected

    @perf("choose_agent_pair")
    def _choose_interval(
        self,
        initiator_user: User,
        target_user: User,
        excluded_intervals: list[int] | None = None,
    ) -> int:
        """Выбор временного промежутка (кванта календаря), который подходит всем пользователям.

        Args:
            initiator_user: Инициатор пары.
            target_user: Приглашённый в пару.
            excluded_intervals: Список квантов, которые нужно исключить из процесса выбора (например, которые уже заняты).

        Returns:
            Идентификатор выбранного кванта.

        Raises:
            `AssertionError`, если подходящих квантов не найдено.
        """
        logger.debug(
            """Агент начал выбор подходящего времени (кванта календаря) для встречи...
            Инициатор пары: %s.
            Приглашённый в пару: %s.
            Не учитывать кванты: %s.""",
            initiator_user.id,
            target_user.id,
            excluded_intervals,
        )

        if excluded_intervals is None:
            excluded_intervals = []
        tquants = {quant.id: quant for quant in target_user.quants}
        iquants = {quant.id: quant for quant in initiator_user.quants}

        excluded_set = set(excluded_intervals)
        intervals = [
            tquants[i]
            for i in set(tquants.keys()).intersection(set(iquants.keys()))
            if i not in excluded_set
        ]

        assert intervals, (
            "Агент не смог найти пересекающиеся кванты у обоих пользователей."
        )

        today = self._get_start_date()
        week_day = today.weekday()

        quant_id = random.choices(
            intervals,
            [
                (8 - x.day + week_day) / 7 if x.day <= week_day else (x.day + 1) / 7
                for x in intervals
            ],
        )[0].id

        logger.info(
            "Агент нашёл квант календаря %s, подходящий и %s, и %s.",
            quant_id,
            initiator_user.id,
            target_user.id,
        )
        return quant_id

    @staticmethod
    def _get_start_date() -> date:
        return datetime.date.today() + datetime.timedelta(days=1)

    def get_match_raw(self, match_id: UUID) -> Match:
        return self.agent_repo.get_match_by_id(match_id=match_id)

    def generate_and_update_embeddings(self, session: Session) -> None:
        """Генерация эмбединга пользователя."""

        users = self.agent_repo.list_users_without_embeddings(session=session)
        for user in self.model.generate_embeddings(
            bios=[u[1] or " " for u in users], ids=[u[0] for u in users]
        ):
            self.agent_repo.add_user_embedding(
                user_id=user[0],
                session=session,
                embedding=user[1],
                archetype="mock archetype",
                primary_focus="mock primary focus",
            )
