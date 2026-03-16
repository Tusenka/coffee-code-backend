from fastapi import HTTPException


class Unauthorized(HTTPException):
    def __init__(self):
        super().__init__(401)


class NotificationForbidden(HTTPException):
    def __init__(self, detail="Уведомление не найдено или доступ запрещен!"):
        super().__init__(
            detail=detail,
            status_code=404,
        )
