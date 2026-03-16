import uuid
from typing import TYPE_CHECKING

from alembic_postgresql_enum import ColumnType
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Column,
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    DateTime,
    Index,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

from db.enums import (
    MatchRequestStatus,
    UserMatchStatus,
    MatchStatus,
    NotificationType,
)

if TYPE_CHECKING:
    pass
else:

    def dataclass_sql(cls):
        return cls


Base = declarative_base()


class UUIDMixin:
    """Идентификатор типа UUID, первичный ключ."""

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )


# =============== Association Tables ===============
class UserGoal(Base):
    """Отношение типа «многие ко многим» между пользователем и его целями."""

    __tablename__ = "user_goals"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    goal_id = Column(
        UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), primary_key=True
    )


class UserSkill(Base):
    """Отношение типа «многие ко многим» между пользователем и его общими компетенциями."""

    __tablename__ = "user_skills"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )


class UserMentorSkill(Base):
    """Отношение типа «многие ко многим» между пользователем и его компетенциями обучающего."""

    __tablename__ = "user_mentor_skills"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )


class UserMenteeSkill(Base):
    """Отношение типа «многие ко многим» между пользователем и его компетенциями обучаемого."""

    __tablename__ = "user_mentee_skills"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )


class UserQuant(Base):
    """Кванты календаря, свободные от встреч пользователя."""

    __tablename__ = "user_quants"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    quant_id = Column(
        SmallInteger, ForeignKey("time_quants.id", ondelete="CASCADE"), primary_key=True
    )


# =============== Main Models ===============
class User(UUIDMixin, Base):
    """Пользователь."""

    __tablename__ = "users"

    username = Column(String(64))
    first_name = Column(String(64))
    last_name = Column(String(64))
    bio = Column(String(4096))
    rate = Column(SmallInteger, nullable=True, server_default="0")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    education = Column(String(256), nullable=True)
    experience = Column(SmallInteger, nullable=True)

    workplace = Column(String(256), nullable=True)
    birthday = Column(Date, nullable=True)
    location = Column(String, nullable=True, server_default="")
    timezone_id = Column(Integer, ForeignKey("timezones.id"), nullable=True)

    timezone = relationship("Timezone", back_populates="users")
    photos = relationship(
        "UserPhoto", back_populates="user", cascade="all, delete-orphan"
    )
    telegram = relationship(
        "UserTelegram",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    contacts = relationship(
        "UserContact", back_populates="user", cascade="all, delete-orphan"
    )

    settings = relationship(
        "UserSetting",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Skills & Goals
    goals = relationship("Goal", secondary=UserGoal.__table__, back_populates="users")
    skills = relationship(
        "Skill", secondary=UserSkill.__table__, back_populates="users"
    )
    mentor_skills = relationship(
        "Skill", secondary=UserMentorSkill.__table__, back_populates="mentor_users"
    )
    mentee_skills = relationship(
        "Skill", secondary=UserMenteeSkill.__table__, back_populates="mentee_users"
    )

    # Matches
    match_requests_sent = relationship(
        "MatchRequest",
        foreign_keys="MatchRequest.initiator_user_id",
        back_populates="initiator_user",
        cascade="all, delete-orphan",
    )
    match_requests_received = relationship(
        "MatchRequest",
        foreign_keys="MatchRequest.target_user_id",
        back_populates="target_user",
        cascade="all, delete-orphan",
    )
    matches_initiated = relationship(
        "Match",
        foreign_keys="Match.initiator_user_id",
        back_populates="initiator_user",
        cascade="all, delete-orphan",
    )
    matches_received = relationship(
        "Match",
        foreign_keys="Match.target_user_id",
        back_populates="target_user",
        cascade="all, delete-orphan",
    )

    # Subscriptions
    subscriptions = relationship(
        "UserSubscription",
        foreign_keys="UserSubscription.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    user_embedding = relationship(
        "UserEmbedding",
        foreign_keys="UserEmbedding.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    match_scores = relationship(
        "MatchScore",
        foreign_keys="MatchScore.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    # Availability intervals
    quants = relationship(
        "TimeQuant", secondary=UserQuant.__table__, back_populates="users"
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.username


class UserSetting(UUIDMixin, Base):
    """Предпочтения пользователя."""

    __tablename__ = "user_settings"

    is_active = Column(Boolean, nullable=False, server_default="True")

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    use_telegram_channel = Column(Boolean, nullable=False, server_default="True")
    use_email_channel = Column(Boolean, nullable=False, server_default="True")

    count_meets_in_week = Column(Integer, nullable=False, server_default="2")

    # Relationships
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, telegram={self.use_telegram_channel}, email={self.use_email_channel})>"


class UserSubscription(Base):
    """Пользовательская подписка."""

    __tablename__ = "user_subscriptions"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    subscription_type_id = Column(
        UUID(as_uuid=True), ForeignKey("subscription_types.id", ondelete="CASCADE")
    )

    subscription_until = Column(TIMESTAMP, nullable=True)
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    subscription_type = relationship("SubscriptionType")

    def __repr__(self):
        return (
            f"<UserSubscription(id={self.id}, user_id={self.user_id}, "
            f"subscription_type_id={self.subscription_type_id}, "
            f"subscription_until={self.subscription_until})>"
        )


class SubscriptionType(Base):
    """Тип подписки."""

    __tablename__ = "subscription_types"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name = Column(String, nullable=False, unique=True)
    max_requests_per_week = Column(SmallInteger, nullable=False, default=10)
    max_matches_per_week = Column(SmallInteger, nullable=False, default=3)
    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="subscription_type")


class MatchRequest(Base):
    """Запрос на создание паросочетания."""

    __tablename__ = "match_requests"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    initiator_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    target_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    initiator_user = relationship("User", foreign_keys=[initiator_user_id])
    target_user = relationship("User", foreign_keys=[target_user_id])
    status = Column(
        Enum(MatchRequestStatus), server_default=MatchRequestStatus.PENDING
    )  # PENDING/APPROVED/REJECTED


class UserPhoto(Base):
    """Фотография профиля пользователя (URL в Телеграм или S3-ключ)."""

    __tablename__ = "user_photos"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    photo_type = Column(String(20))  # icon/preview/big_picture
    photo_url = Column(String(256))  # photo url from telegram
    photo_s3_key = Column(String(128))  # photo s3 in s3 bucket

    # Relationships
    user = relationship("User", back_populates="photos")

    __table_args__ = (
        UniqueConstraint("user_id", "photo_type", name="uq_user_photo_type"),
    )

    def __repr__(self):
        return f"<UserPhoto(user_id={self.user_id}, type='{self.photo_type}')>"


class UserTelegram(Base):
    """Информация о пользователе из Телеграма: внутренний идентификатор и идентификатор и имя из Телеграма."""

    __tablename__ = "user_telegram"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    telegram_id = Column(BigInteger, primary_key=True)
    telegram_username = Column(String(64), nullable=False)

    # Relationships
    user = relationship("User", back_populates="telegram")

    def __repr__(self):
        return f"<UserTelegram(user_id={self.user_id}, username='{self.telegram_username}')>"


class UserContact(Base):
    """Контактная информация."""

    __tablename__ = "user_contacts"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    value = Column(String(100), nullable=False)
    contact_type = Column(String(10), primary_key=True)

    # Relationships
    user = relationship("User", back_populates="contacts")

    def __repr__(self):
        return f"<UserContact(user_id={self.user_id}, type='{self.contact_type}', value='{self.value}')>"


class Category(Base):
    """Категория компетенции или цели."""

    __tablename__ = "categories"

    id = Column(
        Integer,
        primary_key=True,
    )
    name = Column(String(100), unique=True, nullable=False)
    weight = Column(Float, nullable=False, default=0)

    # Relationships
    skills = relationship(
        "Skill", back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class Goal(Base):
    """Цель встречи (что пользователь хочет получить от встреч)."""

    __tablename__ = "goals"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name = Column(String(100), unique=True, nullable=False)

    # Relationships
    users = relationship("User", secondary=UserGoal.__table__, back_populates="goals")

    def __repr__(self):
        return f"<Goal(id={self.id}, name='{self.name}')>"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id


class Skill(Base):
    """Компетенция."""

    __tablename__ = "skills"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name = Column(String(100), unique=True, nullable=False)
    weight = Column(Float, nullable=True, default=1)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"))

    # Relationships
    category = relationship("Category", back_populates="skills")
    users = relationship("User", secondary=UserSkill.__table__, back_populates="skills")
    mentor_users = relationship(
        "User", secondary=UserMentorSkill.__table__, back_populates="mentor_skills"
    )
    mentee_users = relationship(
        "User", secondary=UserMenteeSkill.__table__, back_populates="mentee_skills"
    )

    def __repr__(self):
        return f"<Skill(id={self.id}, name='{self.name}', weight={self.weight})>"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id


class UserMatchState(Base):
    """Заблокированное состояние паросочетания пользователей."""

    __tablename__ = "user_match_state"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    current_status = Column(Enum(UserMatchStatus))
    next_status = Column(Enum(UserMatchStatus))


class Match(Base):
    """Паросочетание пользователей."""

    __tablename__ = "matches"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    initiator_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    target_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    quant_id = Column(
        SmallInteger, ForeignKey("time_quants.id", ondelete="CASCADE"), nullable=False
    )
    date_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    status = Column(
        Enum(MatchStatus), server_default=MatchStatus.UNCOMPLETED
    )  # UNCOMPLETED / CANCELED_BY_INITIATOR / CANCELED_BY_TARGET / COMPLETED / SKIPPED

    video_link = Column(String, nullable=True)

    # Rating given by initiator to target user
    # Unique constraint
    __table_args__ = (
        UniqueConstraint(
            "initiator_user_id",
            "target_user_id",
            "date_at",
            name="unique_user_target_date",
        ),
    )

    # Relationships
    initiator_user = relationship(
        "User", foreign_keys=[initiator_user_id], back_populates="matches_initiated"
    )
    target_user = relationship(
        "User", foreign_keys=[target_user_id], back_populates="matches_received"
    )
    # Relationships
    match_criteria = relationship(
        "MatchCriteria",
        foreign_keys="MatchCriteria.match_id",
        back_populates="match",
        cascade="all, delete-orphan",
    )

    match_scores = relationship(
        "MatchScore",
        foreign_keys="MatchScore.match_id",
        back_populates="match",
        cascade="all, delete-orphan",
    )

    quant = relationship("TimeQuant")

    def __repr__(self):
        return f"<Match(id={self.id}, initiator_user_id={self.initiator_user_id}, target_user_id={self.target_user_id}, status='{self.status}')>"


class MatchCriteria(Base):
    """Критерии подбора пар."""

    __tablename__ = "match_criterias"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False)
    common_skills = Column(ARRAY(String))
    common_goals = Column(ARRAY(String))

    mentor_role = Column(ARRAY(String))
    mentee_role = Column(ARRAY(String))

    cosine_distance = Column(Float, nullable=False)

    # Relationships
    match = relationship("Match", back_populates="match_criteria")


class MatchScore(Base):
    __tablename__ = "match_scores"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    score = Column(SmallInteger, nullable=True)
    review = Column(String, nullable=True)
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="match_scores")
    match = relationship(
        "Match", foreign_keys=[match_id], back_populates="match_scores"
    )


class MatchSnapshot(Base):
    # Таблица состояния пользователя. Используется в отладочных цел
    __tablename__ = "match_snapshots"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    skills = Column(ARRAY(String))
    goals = Column(ARRAY(String))

    bio = Column(String)


class TimeQuant(Base):
    """Единица бронирования встреч по календарю: номер дня недели с 0 до 6, час (от 0 до 23). 7 дней * 24 часа = 168 квантов."""

    __tablename__ = "time_quants"

    id = Column(SmallInteger, primary_key=True)
    hour = Column(SmallInteger, nullable=False)  # 0-23
    day = Column(SmallInteger, nullable=False)  # 0-6

    # Relationships
    users = relationship("User", secondary=UserQuant.__table__, back_populates="quants")

    def __repr__(self):
        return f"<TimeQuant(id={self.id}, day={self.day}, hour={self.hour})>"


class UserEmbedding(Base):
    __tablename__ = "user_embeddings"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    primary_focus = Column(String, nullable=False)
    archetype = Column(String, nullable=False)
    embedding = Column(Vector(768), nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index(
            "user_embedding_index",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={
                "m": 16,
                "ef_construction": 64,
            },  # tbd setup hyperparametsr
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
    user = relationship("User", foreign_keys=[user_id], back_populates="user_embedding")


class Timezone(Base):
    __tablename__ = "timezones"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    ian = Column(String, nullable=False, unique=True)

    users = relationship("User", back_populates="timezone")


class Notification(UUIDMixin, Base):
    """Уведомление для пользователя."""

    __tablename__ = "notifications"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(256), nullable=False)
    message = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    read_at = Column(TIMESTAMP, nullable=True)
    # Optional foreign keys to related entities
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=True)
    request_id = Column(
        UUID(as_uuid=True), ForeignKey("match_requests.id"), nullable=True
    )

    # Relationships
    user = relationship("User", backref="notifications")
    match = relationship("Match")
    request = relationship("MatchRequest")
