import dataclasses

from pydantic_extra_types.timezone_name import TimeZoneName

from db.user_helper_repository import UserHelperRepository
from service.model import SkillList, TimezoneList, GoalList
from service.timequant_models import TimeQuantList
from service.timequant_service import TimeQuantService


@dataclasses.dataclass
class CatalogService:
    helper_repo: UserHelperRepository = UserHelperRepository()

    def list_skills(self) -> SkillList:
        """Возвращает все навыки, сгруппированые по категориям."""
        skills = self.helper_repo.list_skills()
        return SkillList.from_dao(skills)

    def list_timezones(self) -> TimezoneList:
        """Возвращает все часовые пояса."""
        timezones = self.helper_repo.list_timezones()
        return TimezoneList.from_dao(timezones)

    def list_goals(self) -> GoalList:
        """Возвращает все цели."""
        goals = self.helper_repo.list_goals()
        return GoalList.from_dao(goals)

    def list_quants(self, timezone: str = "UTC") -> TimeQuantList:
        """Возвращает все кванты календаря в данном часовом поясе."""
        quants = self.helper_repo.list_quants()
        return TimeQuantList.from_dao(
            intervals=quants,
            timezone_name=TimeZoneName(timezone),
            to_date_with_offset=TimeQuantService.to_date_with_offset,
        )

    def populate_cities(self) -> None:
        """Внесение городов, их стран и часовых поясов в базу данных."""
        self.helper_repo.populate_timezones()

    def populate_tags(self) -> None:
        """Внесение категорий (тегов) в базу данных, внесение и распределение компетенций по этим категориям в базе данных."""
        self.helper_repo.populate_skills_and_categories()

    def populate_goals(self) -> None:
        """Внесение целей в базу данных."""
        self.helper_repo.populate_goals()

    def reset_tags(self) -> None:
        """Удаление категорий и компетенций из базы данных."""
        self.helper_repo.reset_skills_and_categories()
