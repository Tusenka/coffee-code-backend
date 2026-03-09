import pytest

from utils.auth.exceptions import TelegramDataError
from utils.auth.schemes import UserTelegram
from utils.auth.validator import validate_telegram_user

CORRECT_USER = UserTelegram(
    id=123233,
    first_name="Alex",
    last_name="Anonym",
    username="irina_tusenka",
    hash="2a81c6128eee5337f84943ed80cfd553c0ccd4fd804f31c33de34a259bcfc828",
    auth_date=10**42,
)

INCORRECT_USER_HASH = UserTelegram(
    id=123234, first_name="correct user", hash="incorrect_hash", auth_date=10**42
)


class TestValidators:
    @pytest.mark.positive
    def test_validate_success(self):
        validate_telegram_user(data=CORRECT_USER)

    @pytest.mark.negative
    def test_validate_failed(self):
        with pytest.raises(TelegramDataError):
            validate_telegram_user(data=INCORRECT_USER_HASH)
