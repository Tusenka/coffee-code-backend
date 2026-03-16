from abc import abstractmethod, ABCMeta


class IVideoService(metaclass=ABCMeta):
    @abstractmethod
    def get_video(self):
        pass
