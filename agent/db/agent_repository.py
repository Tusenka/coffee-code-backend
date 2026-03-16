import datetime
import logging
from contextlib import contextmanager
from typing import Any, Generator

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session

from agent.db.schema import UserScoreSchema
from agent.metrics.utils import perf
from db.enums import UserMatchStatus
from db.constants import PureGoalResult, PureGoalResultType
from db.model import (
    User,
    UserMatchState,
    UserEmbedding,
    TimeQuant,
)
from db.user_repository import UserRepository


logger = logging.getLogger(__name__)


class UserAgentRepository(UserRepository):
    @contextmanager
    def block_and_get_user_session_by_user_id(
        self, user_id: UUID
    ) -> Generator[Session, Any, None]:
        """Блокировка пользователя в БД с его атрибутами (всей строки) и возвращает связанную сессию.

        Выбрасывает `ValueError`, если данного пользователя нет.
        """
        with self.db.get_session() as session:
            smt = select(User).where(User.id == user_id)
            user = session.execute(smt).unique().one_or_none()
            if user is None:
                logger.exception("Пользователь %s не найден в базе данных.", user_id)
                raise ValueError()
            yield session

    # TODO:: Add tests

    @contextmanager
    def block_user_by_id(self, user_id: UUID, session: Session) -> None:
        smt = select(User).where(User.id == user_id).with_for_update()
        return session.execute(smt).unique().one_or_none()

    @staticmethod
    def get_user_match_state(user_id: UUID, session: Session) -> UserMatchState:
        """Получение состояния паросочетания по пользователю.

        Выбрасывает `ValueError`, если данного паросочетания нет.
        """
        result = session.execute(
            select(UserMatchState).where(UserMatchState.user_id == user_id)
        ).one_or_none()
        if result is None:
            logger.exception(
                "Паросочетание (объект UserMatchState) для пользователя %s не найдено в базе данных.",
                user_id,
            )
            raise ValueError()
        return result[0]

    def finish_meets(self, end_date: datetime.datetime) -> None:
        with self.db.get_session() as session:
            self._finish_meets(end_date=end_date, session=session)

    def _finish_meets(self, end_date, session: Session):
        end_date = end_date.replace(minute=0, second=0, microsecond=0)
        start_date = end_date - datetime.timedelta(hours=1)
        self._execute(
            session=session,
            statement="UPDATE matches SET status='COMPLETED' WHERE status in ('UNCOMPLETED','ONGOING') AND date_at < :start_date",
            params={"start_date": start_date},
        )

    def start_meets(self, start_date: datetime.datetime) -> None:
        with self.db.get_session() as session:
            self._start_meets(session=session, start_date=start_date)

    def _start_meets(self, session: Session, start_date: datetime.datetime):
        start_date = start_date.replace(minute=0, second=0, microsecond=0)
        self._execute(
            session=session,
            statement="UPDATE matches SET status='ONGOING' WHERE status in ('UNCOMPLETED') AND date_at = :start_date",
            params={"start_date": start_date},
        )

    @perf("repo_generate_agent_matches")
    def generate_agent_matches(
        self, user_id: UUID, session: Session, strict: bool = True, max_cos: float = 0.2
    ) -> list[UserScoreSchema]:
        """Предварительная оценка паросочетаний для пользователя на основе его эмбединга, его целей и навыков.

        Args:
            user_id: Пользователь, для которого будет сгенерированы оценки паросочетний.
            session: Сессия базы данных.
            strict: Включить строгий поиск? Строгий поиск исключает из подбора тех, у кого `UserMatchStatus.EVALUATION` или `UserMatchStatus.FILLED`.
            max_cos: Пороговое значение косинусного расстояния между двумя векторными представлениями участников пары.

        Returns:
            Список оценок UserMatchScore в порядке возрастания.
        """

        # Условие строгого поиск для WHERE
        pured_goals_result = self._pure_goal_ids(
            user_goals=self._get_user_goal_ids(user_id=user_id, session=session),
        )
        skill_filter_based_on_goals = (
            self._skill_filter_for_goals(pure_goal_result=pured_goals_result)
            if strict
            else ""
        )
        goal_filter = (
            self._goal_filter(pure_goal_result=pured_goals_result) if strict else ""
        )
        strict_condition = self._get_strict_match_condition(strict)

        sql = f"""
            SELECT id, score, cosine_distance
            FROM (
                SELECT
                    av.embedding <=> uoe.embedding AS cosine_distance,
                    av.id AS id,
                    (skill_count + mentee_role + mentor_role) * goal_count AS score,
                    skill_count,
                    goal_count,
                    mentor_role,
                    mentee_role
                FROM (
                    SELECT
                        ue.user_id AS id,
                        ue.embedding,
                        (
                            SELECT COUNT(*)
                            FROM user_skills ss
                            WHERE ss.user_id = us.id
                            AND ss.skill_id IN (
                                SELECT skill_id
                                FROM user_skills so
                                WHERE so.user_id = :user_id
                            )
                        ) AS skill_count,
                (SELECT count(*) FROM user_goals gs WHERE gs.user_id = us.id AND gs.goal_id IN ({",".join("'" + str(p) + "'" for p in pured_goals_result.goal_ids)}
                )) as goal_count,
                        (
                            SELECT COUNT(*)
                            FROM user_mentee_skills ums
                            WHERE ums.user_id = us.id
                            AND ums.skill_id IN (
                                SELECT skill_id
                                FROM user_mentor_skills umso
                                WHERE umso.user_id = :user_id
                            )
                        ) AS mentor_role,
                        (
                            SELECT COUNT(*)
                            FROM user_mentor_skills ums
                            WHERE ums.user_id = us.id
                            AND ums.skill_id IN (
                                SELECT skill_id
                                FROM user_mentee_skills usso
                                WHERE usso.user_id = :user_id
                            )
                        ) AS mentee_role
                    FROM user_embeddings ue
                    JOIN users us ON ue.user_id = us.id
                    JOIN user_quants q ON q.user_id = us.id
                    JOIN user_settings uss ON uss.user_id = us.id
                    WHERE
                        uss.is_active
                        AND q.quant_id IN (
                            SELECT q_o.quant_id
                            FROM user_quants q_o
                            WHERE q_o.user_id = :user_id
                        )
                          AND q.quant_id NOT IN (
                            SELECT quant_id
                            FROM matches mm
                            WHERE mm.status = 'UNCOMPLETED'
                            AND (mm.initiator_user_id =us.id OR mm.target_user_id=us.id)
                            )

                        {strict_condition}
                        AND us.id != :user_id
                ) AS av,
                user_embeddings AS uoe
                WHERE
                    uoe.user_id = :user_id
                    {goal_filter}
                    {skill_filter_based_on_goals}
                    AND ((skill_count >= :min_skill_count OR mentor_role > 0 OR mentee_role > 0) AND goal_count > 0)
            ) AS candidates
            WHERE cosine_distance <= :max_cos
            ORDER BY
                cosine_distance ASC,
                mentor_role DESC,
                mentee_role DESC,
                score DESC
            LIMIT :limit
        """

        params = {
            "user_id": user_id,
            "limit": 10,
            "max_cos": max_cos,
            "min_skill_count": 3 if strict else 1,
        }
        rows = self._execute(session=session, statement=sql, params=params).all()

        return [
            UserScoreSchema(user_id=row[0], score=row[1], cosine_distance=row[2])
            for row in rows
        ]

    @staticmethod
    def _get_strict_match_condition(strict: bool) -> str:
        return (
            "AND NOT EXISTS (SELECT 1 FROM user_match_state oms "
            "WHERE oms.user_id = uss.user_id AND oms.current_status <> 'UNFILLED') "
            if strict
            else ""
        )

    @staticmethod
    def add_user_embedding(
        user_id: UUID,
        session: Session,
        embedding: np.ndarray,
        archetype: str,
        primary_focus: str,
    ) -> None:
        """Добавление или вставка эмбединга пользователя."""

        sql = select(UserEmbedding).where(UserEmbedding.user_id == user_id)
        result = session.execute(sql).one_or_none()
        if result:
            user_embedding = result[0]
            user_embedding.embedding = embedding
            user_embedding.updated_at = datetime.datetime.now(datetime.UTC)
        else:
            user_embedding = UserEmbedding(
                user_id=user_id,
                embedding=embedding,
                archetype=archetype,
                primary_focus=primary_focus,
            )
            session.add(user_embedding)

    def list_users_without_embeddings(self, session) -> list[tuple[UUID, str]]:
        sql = (
            "SELECT u.id, u.bio "
            "FROM users u "
            "WHERE "
            "NOT EXISTS (SELECT user_id FROM user_embeddings ue WHERE user_id=u.id AND ue.updated_at>=u.updated_at)"
        )
        user_ids = self._execute(session=session, statement=sql).all()

        return user_ids

    def mark_user_match_state(
        self,
        user_id: UUID,
        session: Session,
        status: UserMatchStatus = UserMatchStatus.FILLED,
    ):
        logger.debug("Смена статуса пары пользователя %s...", user_id)
        match = self.get_user_match_state(user_id=user_id, session=session)
        logger.debug(
            "Текущий статус: %s.\nНовый статус: %s.", match.current_status, status
        )
        match.current_status = status
        session.merge(match)

    def reset_match_states(self):
        with self.db.get_session() as session:
            self._execute(
                session,
                "INSERT INTO user_match_state (current_status, user_id) SELECT :status,u.id FROM users u WHERE u.id NOT IN (SELECT user_id FROM user_match_state) ON CONFLICT DO NOTHING",
                params={"status": UserMatchStatus.UNFILLED},
            )
            self._execute(
                session,
                "UPDATE user_match_state us SET current_status='UNFILLED' "
                "WHERE NOT EXISTS (SELECT 1 FROM matches m WHERE status IN ('UNCOMPLETED', 'ONGOING') AND m.date_at>:date_at AND (m.initiator_user_id=us.user_id OR m.target_user_id=us.user_id))",
                params={
                    "date_at": datetime.datetime.now(datetime.UTC)
                    + datetime.timedelta(days=1),
                },
            )

    # Принудительная установка всех статусов паросочетаний. Для тестов.
    def _forced_reset_match_states(
        self, status: UserMatchStatus = UserMatchStatus.UNFILLED
    ):
        with self.db.get_session() as session:
            self._execute(
                session,
                "INSERT INTO user_match_state (current_status, user_id) SELECT :status,u.id FROM users u WHERE u.id NOT IN (SELECT user_id FROM user_match_state) ON CONFLICT DO NOTHING",
                params={"status": status},
            )
            self._execute(
                session,
                "UPDATE user_match_state SET current_status=:status WHERE 1=1",
                params={"status": status},
            )

    def list_unmatched_user_ids(self, strict=True):
        with self.db.get_session() as session:
            return (
                self._execute(
                    statement="SELECT us.user_id FROM user_settings us JOIN user_match_state pm ON pm.user_id=us.user_id "
                    "WHERE is_active"
                    " AND pm.current_status"
                    + ("='UNFILLED'" if strict else "<>'FILLED'"),
                    session=session,
                )
                .scalars()
                .all()
            )

    def list_busy_user_intervals(self, session: Session, user_id: UUID) -> list[int]:
        """Вернуть те кванты, на встречах которых есть данный пользователь."""
        rows = (
            self._execute(
                session=session,
                statement="SELECT m.quant_id FROM matches m WHERE m.initiator_user_id=:user_id OR m.target_user_id=:user_id",
                params={"user_id": user_id},
            )
            .unique()
            .all()
        )
        return [row[0] for row in rows]

    @staticmethod
    def _goal_filter(pure_goal_result: PureGoalResult):
        match pure_goal_result.result_type:
            case PureGoalResultType.MENTOR:
                return " AND mentor_role>0"
            case PureGoalResultType.MENTEE:
                return " AND mentee_role>0"
            case PureGoalResultType.MENTOR_MENTEE:
                return " AND (mentor_role>0 OR mentee_role>0)"
            case _:
                return ""
