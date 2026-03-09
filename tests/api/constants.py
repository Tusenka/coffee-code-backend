import datetime
import pathlib

from api.schemas import UserUpdate
from utils.auth.schemes import UserTelegram

API_VERSION = "/api/v1"

CORRECT_TIMEZONE_ID = -1

CORRECT_USER = UserTelegram(
    id=123233,
    first_name="Alex",
    last_name="Anonym",
    username="irina_tusenka",
    hash="2a81c6128eee5337f84943ed80cfd553c0ccd4fd804f31c33de34a259bcfc828",
    auth_date=10**42,
)

USER_UPDATE_DATA = UserUpdate(
    first_name="Alex updated",
    last_name="Anonym updated",
    telegram_username="irina_tusenka_new",
    telegram_photo_url="https://disk.yandex.com/i/zG-QsvhbDfXOPA",
    phone="+79269693374",
    email="admin@coffee-code.ru",
    education="MEPHI",
    workplace="OZON.tech",
    birthday=datetime.date(year=2000, month=1, day=1),
    use_email_channel=True,
    use_telegram_channel=True,
)

CORRECT_PHOTO_PATH = pathlib.PurePath(__file__).parent.parent.joinpath(
    "data/preview.jpg"
)
CORRECT_EMAIL = "taagcgaat@gmail.com"
