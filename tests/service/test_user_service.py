import io
import uuid
from copy import copy
from typing import Callable

import pytest
from starlette.datastructures import UploadFile

from api.schemas import UserUpdate, LocationUpdate, ContactUpdate
from db.exceptions import UpdateUserActiveNotAllowed
from db.model import User
from db.user_repository import PHOTO_PREVIEW_TYPE, UserRepository, UserHelperRepository
from service.exceptions import SkillsValidationException, GoalsValidationException
from service.model import Timezone, UserProfile, Skill, Goal
from service.timequant_service import UserInterval
from service.user_service import UserService
from tests.api.constants import (
    CORRECT_PHOTO_PATH,
)
from tests.service.constants import CORRECT_EMAIL
from tests.service.cases.test_user_service_cases import IntervalCase, interval_cases
from utils.auth.schemes import UserTelegram


class TestUserService:
    @pytest.mark.positive
    def test_update_profile(
        self,
        random_timezone: Timezone,
        user_service: UserService,
        get_user_with_email: Callable[[str], User],
        correct_update_user_data: UserUpdate,
    ):
        user = get_user_with_email(CORRECT_EMAIL)

        user_service.update_user_data(
            user_id=user.id, user_data=correct_update_user_data
        )
        user_profile = user_service.get_user_profile(user.id)

        self._assert_profile_updated(
            expected=correct_update_user_data,
            actual=user_profile,
            expected_timezone=random_timezone,
        )

    @pytest.mark.positive
    def test_update_profile_bound_values(
        self,
        random_timezone: Timezone,
        user_service: UserService,
        get_user_with_email: Callable[[str], User],
        correct_update_user_data: UserUpdate,
        bound_update_user_data: UserUpdate,
    ):
        user = get_user_with_email(CORRECT_EMAIL)

        user_service.update_user_data(
            user_id=user.id, user_data=correct_update_user_data
        )
        user_service.update_user_data(user_id=user.id, user_data=bound_update_user_data)

        user_profile = user_service.get_user_profile(user.id)
        expected_user_date = self._extract_expected_bound_data(correct_update_user_data)

        self._assert_profile_updated(
            expected=expected_user_date,
            actual=user_profile,
            expected_timezone=random_timezone,
        )

    @staticmethod
    def _extract_expected_bound_data(
        correct_update_user_data: UserUpdate,
    ) -> UserUpdate:
        expected_user_date = copy(correct_update_user_data)
        expected_user_date.experience = 0
        expected_user_date.is_active = False
        expected_user_date.use_email_channel = False
        expected_user_date.count_meets_in_week = 0
        expected_user_date.max_requests_per_week = 0
        expected_user_date.use_email_channel = False
        expected_user_date.use_telegram_channel = False

        return expected_user_date

    @pytest.mark.positive
    def test_update_user_data_idempotency(
        self,
        random_timezone: Timezone,
        user_service: UserService,
        get_user_with_email: Callable[[str], User],
        correct_update_user_data: UserUpdate,
        empty_update_user_data: UserUpdate,
    ):
        user = get_user_with_email(CORRECT_EMAIL)

        user_service.update_user_data(
            user_id=user.id, user_data=correct_update_user_data
        )
        user_service.update_user_data(user_id=user.id, user_data=empty_update_user_data)
        user_profile = user_service.get_user_profile(user.id)

        self._assert_profile_updated(
            expected=correct_update_user_data,
            actual=user_profile,
            expected_timezone=random_timezone,
        )

    @pytest.mark.positive
    def test_update_user_active_does_not_allowed(
        self,
        random_timezone: Timezone,
        user_service: UserService,
        activate_update_user_data: UserUpdate,
        telegram_user_factory,
    ):
        tg_user = telegram_user_factory()

        # complete profile
        user = user_service.save_or_get_user_from_telegram(telegram_user=tg_user)

        with pytest.raises(UpdateUserActiveNotAllowed):
            user_service.update_user_data(
                user_id=user.id, user_data=activate_update_user_data
            )

        user_profile = user_service.get_user_profile(user.id)

        assert not user_profile.user_settings.is_active
        assert not user_profile.complete

    @pytest.mark.positive
    def test_update_user_attributes(
        self,
        user_service: UserService,
        get_user_with_email: Callable[[str], User],
        skill: Skill,
        goal: Goal,
        random_timezone: Timezone,
    ):
        user = get_user_with_email(CORRECT_EMAIL)
        location = str(uuid.uuid4())

        user_service.update_user_skills(user_id=user.id, skills=[skill.id])
        user_service.update_user_mentor_skills(user_id=user.id, skills=[skill.id])
        user_service.update_user_mentee_skills(user_id=user.id, skills=[skill.id])
        user_service.update_user_goals(goals=[goal.id], user_id=user.id)
        user_service.update_user_location(
            LocationUpdate(timezone_id=random_timezone.id, location=location),
            user_id=user.id,
        )

        user_profile = user_service.get_user_profile(user.id)

        assert skill in set(user_profile.skills)
        assert skill in set(user_profile.mentor_skills)
        assert skill in set(user_profile.mentee_skills)
        assert goal in set(user_profile.goals)

        assert user_profile.timezone_name == random_timezone.timezone_name
        assert user_profile.location == location

    @pytest.mark.negative
    def test_update_user_tags_incorrect_length(
        self,
        user_service: UserService,
        get_user_with_email: Callable[[str], User],
    ):
        user = get_user_with_email(CORRECT_EMAIL)

        with pytest.raises(SkillsValidationException):
            user_service.update_user_skills(user_id=user.id, skills=[])

        with pytest.raises(GoalsValidationException):
            user_service.update_user_goals(user_id=user.id, goals=[])

        user_service.update_user_mentor_skills(user_id=user.id, skills=[])
        user_service.update_user_mentee_skills(user_id=user.id, skills=[])

    @pytest.mark.positive
    def test_file_upload(
        self,
        user_service: UserService,
        get_user_with_email: Callable[[str], User],
    ):
        user = get_user_with_email(CORRECT_EMAIL)

        with open(CORRECT_PHOTO_PATH, "rb") as file:
            upload_file = UploadFile(
                file=io.BytesIO(file.read()), filename="big_picture.jpg"
            )
            user_service.update_user_photo(
                photo_type="big_picture", photo=upload_file, user_id=user.id
            )

        user_profile = user_service.get_user_profile(user_id=user.id)

        assert user_profile.user.photos["big_picture"]

    @pytest.mark.positive
    def test_update_contacts(
        self,
        user_service: UserService,
        user_repo,
        get_activated_user: Callable[[], User],
    ) -> None:
        user = get_activated_user()
        contact1 = ContactUpdate(name="name1", value=str(uuid.uuid4()))
        contact2 = ContactUpdate(name="name2", value=str(uuid.uuid4()))
        user_service.update_contacts(contact_data=[contact1, contact2], user_id=user.id)
        contacts = user_repo.get_user_contacts(user_id=user.id)
        assert [
            contact
            for contact in contacts
            if contact.contact_type == contact1.name and contact.value == contact1.value
        ]
        assert [
            contact
            for contact in contacts
            if contact.contact_type == contact2.name and contact.value == contact2.value
        ]

        contact3 = ContactUpdate(name="name2", value=str(uuid.uuid4()))
        user_service.update_contacts(contact_data=[contact3], user_id=user.id)
        contacts = user_repo.get_user_contacts(user_id=user.id)

        assert [
            contact
            for contact in contacts
            if contact.contact_type == contact1.name and contact.value == contact1.value
        ]
        assert [
            contact
            for contact in contacts
            if contact.contact_type == contact3.name and contact.value == contact3.value
        ]

    @pytest.mark.positive
    def test_save_new_user_profile_from_telegram(
        self,
        user_service: UserService,
        telegram_user_factory: Callable[[], UserTelegram],
    ) -> None:
        tg_user = telegram_user_factory()

        user = user_service.save_or_get_user_from_telegram(telegram_user=tg_user)

        user_profile = user_service.get_user_profile(user_id=user.id)

        assert not user_profile.user_settings.is_active

    @pytest.mark.positive
    def test_get_active_user_profile_from_telegram(
        self,
        user_service: UserService,
        telegram_user_factory: Callable[[], UserTelegram],
        correct_update_user_data: UserUpdate,
        skill: Skill,
        goal: Goal,
        user_local_intervals: list[UserInterval],
    ) -> None:
        tg_user = telegram_user_factory()

        # complete profile
        user = user_service.save_or_get_user_from_telegram(telegram_user=tg_user)
        user_service.update_user_skills(user_id=user.id, skills=[skill.id])
        user_service.update_user_goals(goals=[goal.id], user_id=user.id)
        user_service.update_user_quants(intervals=user_local_intervals, user_id=user.id)
        user_service.update_user_data(
            user_data=correct_update_user_data, user_id=user.id
        )

        user = user_service.save_or_get_user_from_telegram(telegram_user=tg_user)

        assert user.settings.is_active

        user_profile = user_service.get_user_profile(user_id=user.id)

        assert user_profile.user_settings.is_active

    @pytest.mark.positive
    @pytest.mark.parametrize("user_interval_case", interval_cases)
    def test_update_user_intervals(
        self,
        user_service: UserService,
        user_helper_repo: UserHelperRepository,
        user_repo: UserRepository,
        get_user_with_email: Callable[[str], User],
        user_interval_case: IntervalCase,
    ):
        user = get_user_with_email(CORRECT_EMAIL)
        timezone_id = user_helper_repo.get_timezone_id_by_ian(
            ian=user_interval_case.timezone_ian
        )

        user_service.update_user_location(
            location=LocationUpdate(timezone_id=timezone_id), user_id=user.id
        )
        user_service.update_user_quants(
            intervals=user_interval_case.local_user_intervals, user_id=user.id
        )
        expected_quant_ids = sum(
            [
                [
                    user_helper_repo.get_quant_by_hour_day(day=i.day - 1, hour=h).id
                    for h in range(i.startHour, i.endHour)
                ]
                for i in user_interval_case.utc_user_intervals
            ],
            [],
        )
        user = user_repo.get_user_by_id(user_id=user.id, extended=False)

        assert sorted([q.id for q in user.quants]) == sorted(expected_quant_ids)

        user_profile = user_service.get_user_profile(user_id=user.id)

        assert sorted(
            user_profile.intervals, key=lambda i: (i.day, i.startHour, i.endHour)
        ) == sorted(
            user_interval_case.expected_user_intervals,
            key=lambda i: (i.day, i.startHour, i.endHour),
        )

    @staticmethod
    def _assert_profile_updated(
        expected: UserUpdate,
        actual: UserProfile,
        expected_timezone: Timezone,
        is_complete: bool = True,
    ):
        assert actual.user.first_name == (
            expected.first_name or actual.user.first_name
        ), "first_name mismatch"
        assert actual.user.last_name == (expected.last_name or actual.user.last_name), (
            "last_name mismatch"
        )
        assert actual.user.telegram_username == (
            expected.telegram_username or actual.user.telegram_username
        ), "telegram_username mismatch"
        assert actual.user.phone == (expected.phone or actual.user.phone), (
            "phone mismatch"
        )
        assert actual.user.bio == (expected.bio or actual.user.bio), "bio mismatch"
        assert actual.user.education == (expected.education or actual.user.education), (
            "education mismatch"
        )
        assert actual.user.experience == (
            expected.experience or actual.user.experience
        ), "expierence mismatch"
        assert actual.user.workplace == (expected.workplace or actual.user.workplace), (
            "workplace mismatch"
        )
        assert actual.user.birthday == (expected.birthday or actual.user.birthday), (
            "birthday mismatch"
        )
        if expected.email:
            assert actual.user.email == expected.email, "email mismatch"

        assert actual.timezone_name == expected_timezone.timezone_name, (
            "timezone mismatch"
        )
        assert actual.location == expected.location, "location mismatch"

        if expected.telegram_photo_url:
            assert (
                actual.user.photos[PHOTO_PREVIEW_TYPE] == expected.telegram_photo_url
            ), "telegram_photo_url mismatch"

        assert actual.user.updated_at is not None, "updated_at is None"
        assert actual.user.updated_at > actual.user.created_at, (
            "updated_at not greater than created_at"
        )

        assert actual.user_settings.is_active == expected.is_active or False, (
            "is_active mismatch"
        )
        assert (
            actual.user_settings.count_meets_in_week == expected.count_meets_in_week
            or actual.user_settings.count_meets_in_week
        ), "count_meets_in_week mismatch"
        assert actual.user_settings.use_email_channel == expected.use_email_channel, (
            "use_email_channel mismatch"
        )
        assert (
            actual.user_settings.use_telegram_channel == expected.use_telegram_channel
        ), "use_telegram_channel mismatch"

        assert actual.user.complete == is_complete, "complete mismatch"
