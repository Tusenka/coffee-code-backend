from enum import StrEnum
from uuid import UUID

from db.model import User as DaoUser
from service.model import UserProfileL1Access
from utils.auth.schemes import UserTelegram

CORRECT_USER = UserTelegram(
    id=123233,
    first_name="Alex",
    last_name="Anonym",
    username="irina_tusenka",
    hash="a06a42f664dafe9062b13f7517db6334becc08c656d88a362f0e7104ef7df965",
    auth_date=10**42,
)

CORRECT_EMAIL = "taagcgaat@gmail.com"
CORRECT_PHOTO_PATH = "tests/data/preview.jpg"


class SkillRef(StrEnum):
    ALL_SKILLS = "ALL_SKILLS"
    MENTOR_SKILLS = "MENTOR_SKILLS"
    MENTEE_SKILLS = "MENTEE_SKILLS"
    MENTEE_MENTOR_SKILLS = "MENTEE_MENTOR_SKILLS"

    def get_skill_ids(self, p: UserProfileL1Access | DaoUser) -> list[UUID]:
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
