import pytest

from service.exceptions import EmailSendFail
from service.mail_service import MailService
from tests.service.constants import CORRECT_EMAIL


class TestUserService:
    def test_send_mail(self):
        mail_service = MailService()
        mail_service.send_mail(
            to=CORRECT_EMAIL,
            subject="Coffee & Code: Sent test request",
            body="Hi! Coder Roast! Lets fest the our coffee time!",
        )

    def test_send_mail_fail(self):
        mail_service = MailService()

        with pytest.raises(EmailSendFail):
            mail_service.send_mail(
                to="not existing email",
                subject="Coffee & Code: Sent test request",
                body="Hi! Coder Roast! Lets fest the our coffee time!",
            )
