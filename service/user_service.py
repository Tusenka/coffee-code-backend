import dataclasses
from dataclasses import field
from uuid import UUID

from fastapi import UploadFile

from api.schemas import UserUpdate, LocationUpdate, ContactUpdate
from db.constants import ContactType
from db.model import User
from db.user_repository import UserRepository
from db.user_helper_repository import UserHelperRepository
from service.cloudinary import CloudinaryService
from service.constants import MIN_SKILL_COUNT, MAX_SKILL_COUNT
from service.exceptions import SkillsValidationException, GoalsValidationException
from service.model import UserProfile
from service.timequant_service import UserInterval, TimeQuantService
from utils.auth.schemes import UserTelegram


@dataclasses.dataclass
class UserService:
    user_repo: UserRepository = UserRepository()
    photo_storage: CloudinaryService = CloudinaryService()
    helper_repo: UserHelperRepository = UserHelperRepository()
    timezone_service: TimeQuantService = field(default_factory=TimeQuantService)

    def update_user_data(self, user_data: UserUpdate, user_id: UUID) -> None:
        self.user_repo.update_user_data(user_data=user_data, user_id=user_id)

    def update_contacts(self, contact_data: list[ContactUpdate], user_id: UUID) -> None:
        for contact in contact_data:
            self.user_repo.upset_contact(
                name=contact.name, value=contact.value, user_id=user_id
            )

    def delete_contact(self, contact_name: str, user_id: UUID):
        if contact_name != ContactType.EMAIL:
            self.user_repo.delete_contact(contact_name=contact_name, user_id=user_id)

    def update_user_photo(
        self, photo_type: str, photo: UploadFile, user_id: UUID
    ) -> None:
        user_photo_url = self.photo_storage.upload_image(photo)
        self.user_repo.update_user_photo(
            photo_type=photo_type, photo_url=user_photo_url, user_id=user_id
        )

    def get_user_profile(self, user_id: UUID) -> UserProfile:
        return UserProfile.from_dao(
            self.user_repo.get_user_by_id(user_id=user_id),
            to_user_intervals_with_offset=TimeQuantService.to_user_intervals_with_offset,
        )

    def update_user_skills(self, skills: list[UUID], user_id: UUID) -> None:
        if not skills or len(skills) < MIN_SKILL_COUNT or len(skills) > MAX_SKILL_COUNT:
            raise SkillsValidationException(
                user_id=user_id, skill_count=len(skills) if skills else 0
            )

        self.user_repo.update_user_skills(skills=skills, user_id=user_id)

    def update_user_mentor_skills(self, skills: list[UUID], user_id: UUID) -> None:
        self.user_repo.update_user_mentor_skills(skills=skills, user_id=user_id)

    def update_user_mentee_skills(self, skills: list[UUID], user_id: UUID) -> None:
        self.user_repo.update_user_mentee_skills(skills=skills, user_id=user_id)

    def update_user_goals(self, goals: list[UUID], user_id: UUID) -> None:
        if not goals or len(goals) < MIN_SKILL_COUNT or len(goals) > MAX_SKILL_COUNT:
            raise GoalsValidationException(
                user_id=user_id, goal_count=len(goals) if goals else 0
            )

        self.user_repo.update_user_goals(goals=goals, user_id=user_id)

    def update_user_quants(self, intervals: list[UserInterval], user_id: UUID) -> None:
        user = self.user_repo.get_user_by_id(user_id=user_id)
        timezone_ = user.timezone.ian if user.timezone else "UTC"
        tz_quants = sum(
            [
                [
                    self.timezone_service.to_quant_from_offset(
                        timezone_ian=timezone_, day=i.day - 1, hour=x
                    ).id
                    for x in range(i.startHour, i.endHour)
                ]
                for i in intervals
            ],
            [],
        )

        self.user_repo.update_user_quants(quants=tz_quants, user_id=user_id)

    def list_users(self, limit: int = 100) -> None:
        return self.user_repo.list_users(limit=limit)

    def update_user_location(self, location: LocationUpdate, user_id: UUID) -> None:
        if location.timezone_id:
            self.user_repo.update_user_timezone(
                timezone_id=location.timezone_id, user_id=user_id
            )
        if location.location:
            self.user_repo.update_user_location(
                location=location.location, user_id=user_id
            )

    def _save_user_profile_from_telegram(self, telegram_user: UserTelegram) -> UUID:
        return self.user_repo.save_user_profile_from_telegram(
            telegram_user=telegram_user, photo_s3_key=None
        )

    def save_or_get_user_from_telegram(self, telegram_user: UserTelegram) -> User:
        user = self.user_repo.get_user_by_telegram_id(telegram_user_id=telegram_user.id)

        if user is None:
            user_id = self._save_user_profile_from_telegram(telegram_user=telegram_user)
            user = self.user_repo.get_user_by_id(user_id=user_id)

        return user
