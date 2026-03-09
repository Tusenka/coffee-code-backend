from __future__ import annotations

import hashlib
import hmac
import logging
import os

from utils.auth.exceptions import TelegramDataError
from utils.auth.schemes import UserTelegram
from utils.auth.token import get_correct_admin_token

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
logger = logging.getLogger(__name__)


def validate_telegram_user(data: UserTelegram):
    data = data.model_dump()
    logger.debug("Учётная запись пользователя Телеграма.", extra=data)
    received_hash = data.pop("hash")

    generated_hash = _generate_hash(data=data, token=TELEGRAM_TOKEN)

    if generated_hash != received_hash:
        logger.error(
            "Не удалось подтвердить учётную запись пользователя Телеграма %s. Хеш телеграм-сессии не идентичен вычисленному по токену.",
            data["id"],
        )
        raise TelegramDataError()
    else:
        logger.info(
            "Учётная запись пользователя Телеграма %s успешна подтверждена.", data["id"]
        )


def _generate_hash(data: dict, token: str) -> str:
    data_check_arr = []
    for key in sorted(data.keys()):
        value = data[key]
        if value is not None:
            data_check_arr.append(f"{key}={value}")

    data_check_string = "\n".join(data_check_arr)

    secret_key = hashlib.sha256(token.encode("utf-8")).digest()

    hash_value = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return hash_value


def is_admin_token_correct(token: str):
    return token == get_correct_admin_token()
