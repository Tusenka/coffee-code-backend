from typing import NamedTuple
from uuid import UUID

from pydantic import BaseModel


class UserScoreSchema(NamedTuple):
    user_id: UUID
    score: int
    cosine_distance: int


class MeetScoreDBSchema(NamedTuple):
    meet_id: UUID
    score: int | None = None
    review: str | None = None
