from pathlib import PurePath


class PathUtils:
    @staticmethod
    def test_root() -> PurePath:
        return PurePath(__file__).parent

    @classmethod
    def sample_bios(cls) -> PurePath:
        return cls.test_root() / "data" / "bios.json"

    @classmethod
    def sample_img(cls) -> PurePath:
        return cls.test_root() / "data" / "preview.jpg"
