import json
import random
from pathlib import Path
from uuid import UUID

from db.constants import ContactType
from db.model import User
from db.user_helper_repository import UserHelperRepository
from db.user_repository import UserRepository
from tests.path_utils import PathUtils
from tests.service.constants import CORRECT_EMAIL


class HelperDataLoader:
    @staticmethod
    def generate_user_profiles(user_repo: UserRepository, count: int = 1000) -> None:
        bios = HelperDataLoader.load_bios()
        for i in range(count):
            user_repo.generate_and_save_random_user(bio=random.choice(bios))

    @staticmethod
    def load_helper_data(user_helper_repo: UserHelperRepository) -> None:
        user_helper_repo.data_upgrade(
            path=Path(__file__).parent.parent / "db" / "data" / "timezones.sql"
        )
        user_helper_repo.data_upgrade(
            path=Path(__file__).parent.parent
            / "db"
            / "data"
            / "categories_and_skills.sql"
        )
        user_helper_repo.data_upgrade(
            path=Path(__file__).parent.parent / "db" / "data" / "goals.sql"
        )
        user_helper_repo.data_upgrade(
            path=Path(__file__).parent.parent
            / "db"
            / "data"
            / "categories_and_skills.sql"
        )
        user_helper_repo.data_upgrade(
            path=Path(__file__).parent.parent / "db" / "data" / "time_quants.sql"
        )

    @staticmethod
    def load_bios() -> list[str]:
        with open(PathUtils.sample_bios()) as fp:
            return json.load(fp=fp)

    @classmethod
    def get_random_user(cls, user_repo: UserRepository, is_active: bool = True) -> UUID:
        return user_repo.get_random_user(is_active=is_active)


def _set_email(user: User):
    contact = next(
        (c for c in user.contacts if c.contact_type == ContactType.EMAIL), None
    )
    contact.value = CORRECT_EMAIL
