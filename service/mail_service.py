import os
import smtplib
from email.message import EmailMessage

import dotenv

from service.exceptions import EmailSendFail
import logging

logger = logging.getLogger(__name__)

dotenv.load_dotenv()


class MailService:
    def __init__(self):
        self.login = os.getenv("EMAIL_LOGIN")
        self.password = os.getenv("EMAIL_PASSWORD")

    def send_mail(self, to: str, subject: str, body: str):
        server = smtplib.SMTP(os.getenv("EMAIL_SMTP"))
        server.starttls()

        try:
            msg = EmailMessage()
            server.login(self.login, self.password)
            msg["Subject"] = subject
            msg["From"] = self.login
            msg["To"] = to
            msg.set_content(body)

            server.send_message(msg)

        except Exception:
            logger.exception(
                """Почтовому SMTP-серверу не удалось отправить электронное письмо.
                Отправитель: %s.
                Получатель: %s.
                Тема письма: %s.
                Тело письма: %s""",
                self.login,
                to,
                subject,
                body,
            )
            raise EmailSendFail(email=to)
        finally:
            server.quit()
