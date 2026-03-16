import os

import requests
from dotenv import load_dotenv

from agent.service.ivideo_service import IVideoService

load_dotenv()


class YandexVideoService(IVideoService):
    def __init__(self):
        self.token = os.getenv("YANDEX_OAUTH_TOKEN")

    def get_video(self) -> str:
        body = {
            "waiting_room_level": "PUBLIC",
        }
        headers = {
            "Authorization": f"OAuth {self.token}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            url="https://cloud-api.yandex.net/v1/telemost-api/conferences",
            headers=headers,
            json=body,
        )

        return response.json()["join_url"]
