from fastapi import HTTPException


class Unauthorized(HTTPException):
    def __init__(self):
        super().__init__(401)
