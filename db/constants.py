from enum import StrEnum
from typing import NamedTuple

from sqlalchemy import UUID

DEFAULT_TIMEZONE_ID = 83


class ContactType(StrEnum):
    EMAIL = "email"
    PHONE = "phone"


PHOTO_PREVIEW_TYPE = "preview"


class GoalName(StrEnum):
    MENTOR_GOAL = "Стать ментором"
    MENTEE_GOAL = "Поиск ментора"
    EXPERIENCE_EXCHANGE = "Обмен опытом"
    BRAINSTORM = "Творческие коллаборации"


class PureGoalResultType(StrEnum):
    MENTOR_MENTEE = "mentor_mentee"
    MENTOR = "MENTOR"
    MENTEE = "MENTEE"
    MIX = "MIX"


class PureGoalResult(NamedTuple):
    result_type: PureGoalResultType
    goal_ids: set[UUID]
