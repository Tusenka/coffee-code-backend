import logging
from functools import cache
from typing import Any

from sqlalchemy import select, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session, joinedload

from db.constants import GoalName
from db.engineer import DbEngine
from db.model import (
    Category,
    Goal,
    Skill,
    TimeQuant,
    Timezone,
)
from db.model import UserTelegram as UserTelegramDB

logger = logging.getLogger(__name__)


class UserHelperRepository:
    def __init__(self):
        self.db = DbEngine()

    # workaround https://www.mail-archive.com/sqlalchemy@googlegroups.com/msg45412.html
    def list_quants(
        self, parent_session: Session | None = None
    ) -> list[TimeQuant] | None:
        smt = select(TimeQuant)

        if parent_session:
            session = parent_session
            return [i[0] for i in session.execute(smt).all()]

        with self.db.get_session() as session:
            return [i[0] for i in session.execute(smt).all()]

    @cache
    def get_quant(self, quant_id: int) -> TimeQuant:
        """Только для тестов."""
        with self.db.get_session() as session:
            return session.query(TimeQuant).filter(TimeQuant.id == quant_id).one()

    @cache
    def get_quant_by_hour_day(self, hour: int, day: int) -> TimeQuant:
        """Только для тестов."""
        with self.db.get_session() as session:
            return (
                session.query(TimeQuant)
                .filter(TimeQuant.hour == hour, TimeQuant.day == day)
                .one()
            )

    def list_skills(self, parent_session: Session | None = None) -> list[Skill] | None:
        smt = (
            select(Skill)
            .order_by(Skill.weight.desc())
            .options(
                joinedload(Skill.category),
            )
        )

        if parent_session:
            session = parent_session
            return [i[0] for i in session.execute(smt).all()]

        with self.db.get_session() as session:
            return [i[0] for i in session.execute(smt).all()]

    def list_goals(self, parent_session: Session | None = None) -> list[Goal] | None:
        smt = select(Goal)

        if parent_session:
            session = parent_session
            return [i[0] for i in session.execute(smt).all()]

        with self.db.get_session() as session:
            return [i[0] for i in session.execute(smt).all()]

    def populate_skills_and_categories(self):
        """Внесение категорий в базу данных, внесение и распределение компетенций по этим категориям в базе данных."""
        self.data_upgrade("db/data/goals.sql")

    def reset_skills_and_categories(self):
        """Удаление категорий и компетенций из базы данных."""
        with self.db.get_session() as session:
            session.execute(text("TRUNCATE categories RESTART IDENTITY CASCADE"))

    def populate_goals(self):
        """Внесение целей в базу данных."""
        self.data_upgrade("db/data/goals.sql")

    def populate_timezones(self):
        """Внесение городов, их стран и часовых поясов в базу данных."""
        self.data_upgrade("db/data/timezones.sql")

    def upsert_category(self, category_id: int, name: str) -> int:
        logger.debug(
            """Добавление новой категории в базу данных или изменение уже существующей категории...
            Идентификатор категории: %d.
            Название категории: %s.
            """,
            category_id,
            name,
        )

        with self.db.get_session() as session:
            category = session.execute(
                select(Category).where(Category.id == category_id)
            ).one_or_none()

            if category is None:
                category = Category(id=category_id, name=name)
                logger.info(
                    "Категория %s не найдена в базе данных. Добавление...", category
                )
            else:
                category = category[0]
                category.name = name
                logger.info(
                    """Категория %d найдена в базе данных. Изменение названия...
                    Старое название: %s.
                    Новое название: %s.
                    """,
                    category.id,
                    category.name,
                    name,
                )

            session.add(category)

        logger.info("Категория %s добавлена в базу данных или изменена.", category)
        return category_id

    def upsert_skill(self, category_id: int, name: str) -> UUID:
        logger.debug(
            """Добавление новой компетенции в базу данных или изменение уже существующей компетенции по соответствующей категории...
            Идентификатор соответствующей категории: %d.
            Название компетенции: %s.
            """,
            category_id,
            name,
        )

        with self.db.get_session() as session:
            skill = session.execute(
                select(Skill).where(Skill.name == name)
            ).one_or_none()

            if skill is None:
                skill = Skill(category_id=category_id, name=name)
                logger.info(
                    "Компетенция %s не найдена в базе данных. Добавление...", skill
                )
            else:
                skill = skill[0]
                logger.info(
                    "Компетенция %s найдена в базе данных. Изменение на: %s...",
                    skill,
                    skill[0],
                )

            session.add(skill)
            session.flush()

        logger.info(
            "Компетенция %s добавлена в базу данных или изменена по категории %s.",
            skill,
            category_id,
        )
        return skill.id

    def upsert_goal(self, name: str) -> UUID:
        logger.debug(
            """Добавление новой цели в базу данных или изменение уже существующей...
            Название цели: %s.
            """,
            name,
        )

        with self.db.get_session() as session:
            goal = session.execute(select(Goal).where(Goal.name == name)).one_or_none()

            if goal is None:
                goal = Goal(name=name)
                logger.info("Цель %s не найдена в базе данных. Добавление...", goal)
            else:
                goal = goal[0]
                logger.info(
                    "Цель %s найдена в базе данных. Изменение на: %s...", goal, goal[0]
                )

            session.add(goal)
            session.flush()

        logger.info("Цель %s добавлена в базу данных или изменена.", goal)
        return goal.id

    def list_timezones(self) -> list[Timezone]:
        with self.db.get_session() as session:
            smt = select(Timezone)
            return [i[0] for i in session.execute(smt).all()]

    def get_random_skill(self) -> Skill:
        with self.db.get_session() as session:
            return session.execute(
                select(Skill).order_by(func.random()).limit(1)
            ).first()[0]

    def get_random_goal(self) -> Goal:
        with self.db.get_session() as session:
            return session.execute(
                select(Goal).order_by(func.random()).limit(1)
            ).first()[0]

    def get_random_timezone(self) -> Timezone:
        with self.db.get_session() as session:
            smt = select(Timezone).order_by(func.random()).limit(1)
            return session.execute(smt).first()[0]

    def data_upgrade(self, path: str):
        with (
            self.db.get_session() as session,
            open(path, "r") as f,
        ):
            session.execute(text(f.read()))

    @cache
    def get_goal_by_name(self, goal_name: GoalName) -> type[Goal] | None:
        with self.db.get_session() as session:
            return self._get_goal_by_name(goal_name, session)

    @staticmethod
    def _get_goal_by_name(goal_name: GoalName, session: Session) -> type[Goal] | None:
        return session.query(Goal).where(Goal.name == goal_name).first()

    def get_timezone_id_by_ian(self, ian: str):
        with self.db.get_session() as session:
            return session.query(Timezone).where(Timezone.ian == ian).first().id
