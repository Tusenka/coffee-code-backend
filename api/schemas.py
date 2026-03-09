from datetime import date
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from service.model import MatchStatus


class UserUpdate(BaseModel):
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    bio: str | None = None
    telegram_username: str | None = None
    telegram_photo_url: str | None = None
    phone: str | None = None
    education: str | None = None
    experience: int | None = None
    workplace: str | None = None
    birthday: date | None = None

    max_requests_per_week: int = 2
    timezone_id: int | None = None
    location: str | None = None
    use_telegram_channel: bool | None = None
    use_email_channel: bool | None = None
    count_meets_in_week: int = 3
    is_active: bool | None = None


class ContactUpdate(BaseModel):
    name: str
    value: str


class LocationUpdate(BaseModel):
    timezone_id: int | None = None
    location: str | None = None


class MeetScoreSchema(BaseModel):
    meet_id: UUID
    score: int | None = None
    review: str | None = None


class CreateAdminMeetSchema(BaseModel):
    initiator_user_id: UUID
    target_user_id: UUID
    quant_id: int
    video_link: str
    cosine_distance: Annotated[float, Field(gt=0, le=1)]


class TransferAdminMeetSchema(BaseModel):
    meet_id: UUID
    new_status: MatchStatus = MatchStatus.COMPLETED


class CreateAdminMeetScoreSchema(BaseModel):
    user_id: UUID
    meet_score: MeetScoreSchema
