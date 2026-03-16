from typing import Callable

import schedule


class Scheduler:
    @staticmethod
    def every_day_at(f: Callable, time: str):
        schedule.every().day.at(time).do(f)

    @staticmethod
    def every_hour_at(f: Callable, time: str):
        schedule.every().hour.at(time).do(f)
