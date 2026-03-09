import datetime
from uuid import UUID

from fastapi import HTTPException

from service.constants import (
    MIN_SKILL_COUNT,
    MAX_SKILL_COUNT,
    MAX_GOAL_COUNT,
    MIN_GOAL_COUNT,
)


class RequestAlreadySent(HTTPException):
    def __init__(
        self,
        user_id: UUID,
        target_user_id: UUID,
        detail="{user_id} уже отправлял запрос {target_user_id}!",
    ):
        super().__init__(
            status_code=400,
            detail=detail.format(user_id=user_id, target_user_id=target_user_id),
        )


class SubscriptionMatchRequests(HTTPException):
    def __init__(
        self,
        user_id: UUID,
        detail="{user_id} отправил слишком много запросов на этой неделе! Он может перейти на более высокого уровня.",
    ):
        super().__init__(
            status_code=403,
            detail=detail.format(user_id=user_id, day=datetime.date.today()),
        )


class EmailSendFail(HTTPException):
    def __init__(
        self,
        email: str,
        detail="Не удалось отправить письмо на {email}!",
    ):
        super().__init__(
            status_code=500,
            detail=detail.format(email=email),
        )


class ProfileAccessDenied(HTTPException):
    def __init__(
        self,
        target_user_id: UUID,
        initiator_user_id: str,
        detail="Доступ к профилю {target_user_id} для {initiator_user_id} запрещён!",
    ):
        super().__init__(
            status_code=403,
            detail=detail.format(
                initiator_user_id=initiator_user_id, target_user_id=target_user_id
            ),
        )


class SkillsValidationException(HTTPException):
    def __init__(
        self,
        user_id: UUID,
        skill_count,
        detail="Не удалось изменить навыки пользователя {user_id}. Количество навыков должно быть от {min_skill_count} до {max_skill_count}. Сейчас их {skill_count}.",
    ):
        super().__init__(
            status_code=400,
            detail=detail.format(
                user_id=user_id,
                min_skill_count=MIN_SKILL_COUNT,
                max_skill_count=MAX_SKILL_COUNT,
                skill_count=skill_count,
            ),
        )


class GoalsValidationException(HTTPException):
    def __init__(
        self,
        user_id: UUID,
        goal_count,
        detail="Не удалось изменить цели пользователя {user_id}. Количество целей должно быть от {min_goal_count} до {max_goal_count}. Сейчас их {goal_count}.",
    ):
        super().__init__(
            status_code=400,
            detail=detail.format(
                user_id=user_id,
                min_goal_count=MIN_GOAL_COUNT,
                max_goal_count=MAX_GOAL_COUNT,
                goal_count=goal_count,
            ),
        )
