import dataclasses
from uuid import UUID


@dataclasses.dataclass
class TestUserData:
    id: int
    telegram_id: int
    skills: list[UUID]
    mentee_skills: list[UUID]
    mentor_skills: list[UUID]
    goals: list[UUID]
    quants: list[UUID]
