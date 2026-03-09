from pydantic import BaseModel


class UserTelegram(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int | None = None
    hash: str | None = None


class JWTUser(BaseModel):
    id: str
