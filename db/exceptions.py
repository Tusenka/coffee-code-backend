from fastapi import HTTPException
from sqlalchemy import UUID


class RequestAlreadySent(HTTPException):
    def __init__(
        self,
        user_id: UUID,
        target_user_id: UUID,
        detail="Запрос от {user_id} к {target_user_id} уже есть в базе данных!",
    ):
        super().__init__(
            status_code=409,
            detail=detail.format(user_id=user_id, target_user_id=target_user_id),
        )


class RequestNotFound(HTTPException):
    def __init__(
        self,
        user_id: UUID,
        target_user_id: UUID,
        detail="Запрос от {user_id} к {target_user_id} не найден в базе данных!",
    ):
        super().__init__(
            status_code=404,
            detail=detail.format(user_id=user_id, target_user_id=target_user_id),
        )


class UpdateUserActiveNotAllowed(HTTPException):
    def __init__(
        self,
        user_id: UUID,
        detail="{user_id} не может быть активирован, так как не заполнил профиль!",
    ):
        super().__init__(
            status_code=400,
            detail=detail.format(user_id=user_id),
        )
