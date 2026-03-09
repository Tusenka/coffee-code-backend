import datetime
from enum import StrEnum
from uuid import UUID

from db.model import User as DaoUser

CORRECT_DATETIME = datetime.datetime(
    year=2018, month=1, day=4, hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc
)


class SkillRef(StrEnum):
    ALL_SKILLS = "ALL_SKILLS"
    MENTOR_SKILLS = "MENTOR_SKILLS"
    MENTEE_SKILLS = "MENTEE_SKILLS"
    MENTEE_MENTOR_SKILLS = "MENTEE_MENTOR_SKILLS"

    def get_skill_ids(self, p: DaoUser) -> list[UUID]:
        match self:
            case SkillRef.ALL_SKILLS:
                return [
                    skill.id for skill in p.skills + p.mentee_skills + p.mentor_skills
                ]
            case SkillRef.MENTOR_SKILLS:
                return [skill.id for skill in p.mentor_skills]
            case SkillRef.MENTEE_SKILLS:
                return [skill.id for skill in p.mentee_skills]
            case SkillRef.MENTEE_MENTOR_SKILLS:
                return [skill.id for skill in p.mentor_skills + p.mentee_skills]
