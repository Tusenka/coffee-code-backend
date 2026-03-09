import os

import jwt

from utils.auth.schemes import JWTUser
import logging

JWT_KEY = os.getenv("JWT_KEY", default=None)
JWT_ALGO = "HS256"
ADMIN_TOKEN = os.getenv("ADMIN_AUTH_TOKEN")
logger = logging.getLogger(__name__)


def generate_jwt_token(user: JWTUser) -> str:
    logger.info("JWT-токен сгенерирован.")
    return jwt.encode(payload=user.model_dump(), key=JWT_KEY, algorithm=JWT_ALGO)


def get_auth_user_data(token: str) -> dict:
    logger.info("JWT-токен расшифрован.")
    return jwt.decode(jwt=token, key=JWT_KEY, algorithms=[JWT_ALGO])


def get_correct_admin_token() -> str | None:
    logger.info("JWT-токен сгенерирован.")
    return ADMIN_TOKEN
