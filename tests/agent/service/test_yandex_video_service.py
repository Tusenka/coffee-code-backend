import pytest

from agent.service.yandex_video_service import YandexVideoService


@pytest.mark.skip("We don't need to test yandex service, as the third part library")
class TestYandexVideoService:
    def test_get_video_id(self, yandex_video_service: YandexVideoService):
        assert yandex_video_service.get_video()
