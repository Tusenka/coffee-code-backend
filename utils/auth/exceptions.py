from fastapi import HTTPException


class TelegramDataError(HTTPException):
    def __init__(self):
        super().__init__(400)


class TelegramDataIsOutdated(HTTPException):
    def __init__(self):
        super().__init__(400)
