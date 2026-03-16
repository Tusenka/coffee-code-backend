from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import StrEnum, auto
from typing import Any, Callable
from uuid import UUID

from pydantic import BaseModel as PydanticBaseModel

from db.constants import ContactType
from db.enums import MatchRequestStatus as DaoMatchRequestStatus, NotificationType
from db.model import Goal as DaoGoal, TimeQuant

from db.model import UserContact as DaoUserContact
from db.model import MatchCriteria as DaoMatchCriteria

from db.model import Match as DaoMatch
from db.model import Notification as DaoNotification
from db.model import Skill as DaoSkill
from db.model import Timezone as DaoTimezone
from db.model import User as DaoUser
from db.model import MatchScore as DaoMeetScore
from db.model import UserSubscription as DaoUserSubscription
from service.timequant_models import UserInterval


# ============================================================================
# Base Modelst b
# ============================================================================


class BaseModel(PydanticBaseModel):
    def __hash__(self):
        return hash(
            (type(self),) + tuple(getattr(self, f) for f in self.model_fields.keys())
        )


# ============================================================================
# User Models
# ============================================================================


class UserBase(BaseModel):
    """Общие поля для всех классов пользователя."""

    id: UUID | None = None
    first_name: str | None = None
    last_name: str | None = None
    bio: str | None = None
    photos: dict[str, str] | None = None
    experience: int | None = None
    education: str | None = None


class User(UserBase):
    email: str | None = None
    phone: str | None = None
    workplace: str | None = None
    birthday: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    telegram_username: str | None = None

    @property
    def complete(self):
        return bool(self.telegram_username and self.bio and self.email)


class UserL2Access(UserBase):
    email: str | None
    education: str | None = None
    workplace: str | None = None
    birthday: date | None = None
    telegram_username: str | None
    phone: str | None
    is_active: bool = True


class UserL1Access(UserBase):
    """Информация о пользователе для превью."""

    pass


# ============================================================================
# Skill, Goal, Match, Timezone
# ============================================================================


class Skill(BaseModel):
    id: UUID
    name: str
    weight: float = 0

    @staticmethod
    def from_dao(skill: DaoSkill):
        return Skill(id=skill.id, name=skill.name, weight=skill.weight)


class Goal(BaseModel):
    id: UUID
    name: str

    @staticmethod
    def from_dao(goal: DaoGoal):
        return Goal(id=goal.id, name=goal.name)


class MeetScore(BaseModel):
    score: int
    review: str

    @staticmethod
    def from_dao(scores: list[DaoMeetScore], user_id: UUID):
        score = [s for s in scores if s.user_id == user_id] if scores else None

        if not score:
            return None

        return MeetScore(score=score[0].score, review=score[0].review)


class MatchCriteria(BaseModel):
    common_skills: list[str]
    common_goals: list[str]

    mentor_role: list[str]
    mentee_role: list[str]

    rate: float

    @staticmethod
    def from_dao(match_criterias: list[DaoMatchCriteria] | None, user_id: UUID):
        match_criteria = (
            [c for c in match_criterias if c.user_id == user_id]
            if match_criterias
            else None
        )
        if not match_criteria:
            return None

        match_criteria = match_criteria[0]

        return MatchCriteria(
            common_skills=match_criteria.common_skills,
            common_goals=match_criteria.common_goals,
            mentor_role=match_criteria.mentor_role,
            mentee_role=match_criteria.mentee_role,
            rate=1 - match_criteria.cosine_distance,
        )


class Match(BaseModel):
    id: UUID
    user_id: UUID
    target_user: UserProfile
    status: MatchStatus
    date_at: datetime
    match_score: MeetScore | None
    match_criteria: MatchCriteria | None

    @staticmethod
    def from_dao(
        match: DaoMatch,
        original_user_id: UUID,
        target_user: DaoUser,
        to_user_intervals_with_offset=Callable[
            [list[TimeQuant], str], list[UserInterval]
        ],
    ):
        return Match(
            user_id=original_user_id,
            target_user=UserProfile.from_dao(
                target_user, to_user_intervals_with_offset=to_user_intervals_with_offset
            ),
            match_score=MeetScore.from_dao(
                scores=match.match_scores, user_id=original_user_id
            ),
            status=MatchStatus[match.status],
            match_criteria=MatchCriteria.from_dao(
                match_criterias=match.match_criteria, user_id=original_user_id
            ),
            date_at=match.date_at,
            id=match.id,
        )


class Notification(BaseModel):
    id: UUID
    type: NotificationType
    title: str | None = None
    message: str | None = None
    created_at: datetime
    read_at: datetime | None = None

    @staticmethod
    def from_dao(notification: DaoNotification) -> "Notification":
        return Notification(
            id=notification.id,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            created_at=notification.created_at,
            read_at=notification.read_at,
        )


class Timezone(BaseModel):
    id: int
    timezone_name: str

    @staticmethod
    def from_dao(timezone: DaoTimezone):
        return Timezone(id=timezone.id, timezone_name=timezone.name)


# ============================================================================
# User Settings & Profile
# ============================================================================


class UserSettings(BaseModel):
    is_active: bool
    use_telegram_channel: bool
    use_email_channel: bool
    count_meets_in_week: int | None = 3


class MeetList(BaseModel):
    meet: list[Match]


class UserProfileL1Access(BaseModel):
    user: UserL1Access
    timezone: str
    location: str
    skills: list[Skill] = []
    mentor_skills: list[Skill] = []
    mentee_skills: list[Skill] = []
    goals: list[Goal] = []
    match_request_status: MatchRequestStatus

    @staticmethod
    def from_dao(target_user: DaoUser, initiator_user: DaoUser):
        photos = {p.photo_type: p.photo_url for p in target_user.photos}
        user_ = UserL1Access(
            id=target_user.id,
            first_name=target_user.first_name,
            last_name=target_user.last_name,
            bio=target_user.bio,
            photos=photos,
            experience=target_user.experience,
            education=target_user.education,
        )
        timezone_ = target_user.timezone.name if target_user.timezone else "UTC"
        mach_request_status = _get_match_request_status(initiator_user, target_user)

        return UserProfileL1Access(
            user=user_,
            timezone=timezone_,
            location=target_user.location,
            skills=[Skill.from_dao(skill) for skill in target_user.skills],
            mentee_skills=[
                Skill.from_dao(skill) for skill in target_user.mentee_skills
            ],
            mentor_skills=[
                Skill.from_dao(skill) for skill in target_user.mentor_skills
            ],
            goals=[Goal.from_dao(goal) for goal in target_user.goals],
            match_request_status=mach_request_status,
        )


def _get_match_request_status(initiator_user: DaoUser, target_user: DaoUser):
    match_request_status = MatchRequestStatus.UNSENT

    requests = [
        r.status
        for r in initiator_user.match_requests_sent
        if r.target_user_id == target_user.id
    ]
    request_sent_to_target_user = requests[-1] if requests else None

    match request_sent_to_target_user:
        case DaoMatchRequestStatus.APPROVED:
            match_request_status = MatchRequestStatus.SENT_AND_ACCEPTED
        case DaoMatchRequestStatus.REJECTED:
            match_request_status = MatchRequestStatus.SENT_AND_REJECTED
        case DaoMatchRequestStatus.PENDING:
            match_request_status = MatchRequestStatus.ALREADY_SENT

    requests = [
        r.status
        for r in initiator_user.match_requests_received
        if r.initiator_user_id == target_user.id
    ]
    request_received_by_target_user = requests[-1] if requests else None

    match request_received_by_target_user:
        case DaoMatchRequestStatus.APPROVED:
            match_request_status = MatchRequestStatus.RECEIVED_AND_ACCEPTED
        case DaoMatchRequestStatus.REJECTED:
            match_request_status = MatchRequestStatus.RECEIVED_AND_REJECTED
        case DaoMatchRequestStatus.PENDING:
            match_request_status = MatchRequestStatus.RECEIVED

    return match_request_status


class UserProfileL2Access(BaseModel):
    user: UserL2Access
    timezone: str
    location: str
    skills: list[Skill] = []
    mentor_skills: list[Skill] = []
    mentee_skills: list[Skill] = []
    goals: list[Goal] = []

    @staticmethod
    def from_dao(user: DaoUser):
        email = get_user_email(user)
        phone = get_phone_number(user)

        photos = {p.photo_type: p.photo_url for p in user.photos}
        user_ = UserL2Access(
            id=user.id,
            email=email,
            first_name=user.first_name,
            last_name=user.last_name,
            bio=user.bio,
            education=user.education,
            workplace=user.workplace,
            birthday=user.birthday,
            phone=phone,
            photos=photos,
            telegram_username=user.telegram.telegram_username,
            experience=user.experience,
        )
        timezone_ = user.timezone.name if user.timezone else "UTC"

        return UserProfileL2Access(
            user=user_,
            timezone=timezone_,
            location=user.location,
            skills=[Skill.from_dao(skill) for skill in user.skills],
            mentee_skills=[Skill.from_dao(skill) for skill in user.mentee_skills],
            mentor_skills=[Skill.from_dao(skill) for skill in user.mentor_skills],
            goals=[Goal.from_dao(goal) for goal in user.goals],
        )


def get_phone_number(user: DaoUser) -> Any | None:
    phone = [c.value for c in user.contacts if c.contact_type == ContactType.PHONE]
    phone = phone[0] if phone else None
    return phone


def get_user_email(user: DaoUser) -> Any | None:
    email = [c.value for c in user.contacts if c.contact_type == ContactType.EMAIL]
    email = email[0] if email else None
    return email


class UserContact(BaseModel):
    name: str
    value: str

    @staticmethod
    def from_dao(dao_user_contact: DaoUserContact) -> UserContact:
        return UserContact(
            name=dao_user_contact.contact_type, value=dao_user_contact.value
        )


class UserProfile(BaseModel):
    user: User
    timezone_name: str
    timezone_id: int
    location: str = ""
    skills: list[Skill] = []
    mentor_skills: list[Skill] = []
    mentee_skills: list[Skill] = []
    goals: list[Goal] = []
    intervals: list[UserInterval] = []
    user_settings: UserSettings
    complete: bool = False

    contacts: list[UserContact] = []

    @staticmethod
    def from_dao(
        user: DaoUser,
        to_user_intervals_with_offset=Callable[
            [list[TimeQuant], str], list[UserInterval]
        ],
    ):
        email = get_user_email(user)
        phone = get_phone_number(user)

        photos = {p.photo_type: p.photo_url for p in user.photos}
        user_ = User(
            id=user.id,
            email=email,
            first_name=user.first_name,
            last_name=user.last_name,
            bio=user.bio,
            education=user.education,
            workplace=user.workplace,
            birthday=user.birthday,
            created_at=user.created_at,
            phone=phone,
            photos=photos,
            updated_at=user.updated_at,
            telegram_username=user.telegram.telegram_username,
            experience=user.experience,
        )
        timezone_ian = user.timezone.ian if user.timezone else "UTC"
        timezone_name = user.timezone.name if user.timezone else "UTC"
        timezone_id = user.timezone.id if user.timezone else 42

        return UserProfile(
            user=user_,
            timezone_name=timezone_name,
            timezone_id=timezone_id,
            location=user.location,
            skills=[Skill.from_dao(skill) for skill in user.skills],
            mentee_skills=[Skill.from_dao(skill) for skill in user.mentee_skills],
            mentor_skills=[Skill.from_dao(skill) for skill in user.mentor_skills],
            goals=[Goal.from_dao(goal) for goal in user.goals],
            intervals=to_user_intervals_with_offset(user.quants, timezone_ian),
            complete=bool(user_.complete and user.skills and user.goals),
            contacts=[
                UserContact.from_dao(contact)
                for contact in user.contacts
                if contact.contact_type not in (ContactType.EMAIL, ContactType.PHONE)
            ],
            user_settings=UserSettings(
                is_active=user.settings.is_active,
                use_telegram_channel=user.settings.use_telegram_channel,
                use_email_channel=user.settings.use_email_channel,
                count_meets_in_week=user.settings.count_meets_in_week,
            ),
        )


# ============================================================================
# List Models (SkillList, GoalList, TimezoneList, TimeQuantList)
# ============================================================================


class SkillList(BaseModel):
    skills: dict[str, list[Skill]]

    @staticmethod
    def from_dao(skills: list[DaoSkill]):
        tree = {}
        for s in skills:
            if s.category.name not in tree:
                tree[s.category.name] = []
            tree[s.category.name].append(Skill.from_dao(s))
        return SkillList(skills=dict(tree))


class GoalList(BaseModel):
    goals: list[Goal]

    @staticmethod
    def from_dao(goals: list[DaoGoal]):
        return GoalList(goals=[Goal(id=s.id, name=s.name) for s in goals])


class TimezoneList(BaseModel):
    timezones: list[Timezone]

    @staticmethod
    def from_dao(cities: list[DaoTimezone]):
        return TimezoneList(timezones=[Timezone.from_dao(timezone=i) for i in cities])


# ============================================================================
# Match Request Status Enum
# ============================================================================


class MatchRequestStatus(StrEnum):
    UNSENT = auto()
    RECEIVED = auto()
    RECEIVED_AND_REJECTED = auto()
    ALREADY_SENT = auto()
    SENT_AND_ACCEPTED = auto()
    RECEIVED_AND_ACCEPTED = auto()
    SENT_AND_REJECTED = auto()


class MatchStatus(StrEnum):
    FOLLOWING = auto()
    UNCOMPLETED = auto()
    CANCELED_BY_INITIATOR = auto()
    CANCELED_BY_TARGET = auto()
    COMPLETED = auto()
    SKIPPED = auto()
    ONGOING = auto()


# ============================================================================
# Matched User Profile
# ============================================================================


class UserProfileL1AccessList(BaseModel):
    profiles: list[UserProfileL1Access]

    @staticmethod
    def from_dao(users: list[DaoUser], target_user: DaoUser):
        return UserProfileL1AccessList(
            profiles=[
                UserProfileL1Access.from_dao(target_user=u, initiator_user=target_user)
                for u in users
            ]
        )


# ============================================================================
# Subscription
# ============================================================================


class UserSubscription(BaseModel):
    max_requests_per_week: int
    max_matches_per_week: int
    valid_until: datetime

    @staticmethod
    def from_dao(sub: DaoUserSubscription | None):
        if sub:
            return UserSubscription(
                max_requests_per_week=sub.subscription_type.max_requests_per_week,
                max_matches_per_week=sub.subscription_type.max_matches_per_week,
                valid_until=sub.subscription_until,
            )
        return UserSubscription(
            max_requests_per_week=100,
            max_matches_per_week=3,
            valid_until=datetime.now() + timedelta(days=10),
        )


class NotificationList(BaseModel):
    notifications: list[Notification]
    total: int
    unread_count: int
