import dataclasses
import datetime

import pytz

from db.model import TimeQuant
from db.user_helper_repository import UserHelperRepository
from service.timequant_models import UserInterval, DayHour


@dataclasses.dataclass
class TimeQuantService:
    helper_repo: UserHelperRepository = UserHelperRepository()

    @staticmethod
    def to_date_with_offset(timezone_ian: str, hour: int, day: int) -> DayHour:
        delta = (
            datetime.datetime.now(pytz.timezone(timezone_ian))
            .utcoffset()
            .total_seconds()
            / 60
            / 60
        )
        tz_day = day
        tz_hour = hour - int(delta)
        if tz_hour > 23:
            tz_hour -= 24
            tz_day = (tz_day + 1) if tz_day < 6 else 0

        if tz_hour < 0:
            tz_hour = tz_hour + 24
            tz_day = (tz_day - 1) if tz_day > 0 else 6

        return DayHour(day=tz_day, hour=tz_hour)

    @staticmethod
    def from_date_with_offset(timezone_ian: str, hour: int, day: int) -> DayHour:
        delta = (
            datetime.datetime.now(pytz.timezone(timezone_ian))
            .utcoffset()
            .total_seconds()
            / 60
            / 60
        )
        tz_day = day
        tz_hour = hour + int(delta)
        if tz_hour > 23:
            tz_hour -= 24
            tz_day = (tz_day + 1) if tz_day < 6 else 0

        if tz_hour < 0:
            tz_hour = tz_hour + 24
            tz_day = (tz_day - 1) if tz_day > 0 else 6

        return DayHour(day=tz_day, hour=tz_hour)

    @staticmethod
    def to_user_intervals_with_offset(
        time_quants: list[TimeQuant], timezone_ian: str
    ) -> list[UserInterval]:
        if not time_quants:
            return []

        tq_intervals = [
            TimeQuantService.to_date_with_offset(
                day=i.day, hour=i.hour, timezone_ian=timezone_ian
            )
            for i in time_quants
        ]
        tq_intervals.sort(key=lambda x: x.day * 24 + x.hour)

        merged_intervals = []

        cday = tq_intervals[0].day
        cstart = tq_intervals[0].hour
        cend = tq_intervals[0].hour + 1

        for i in range(1, len(tq_intervals)):
            if tq_intervals[i].day == cday and tq_intervals:
                cend = tq_intervals[i].hour + 1
            else:
                merged_intervals.append(
                    UserInterval(day=cday + 1, startHour=cstart, endHour=cend)
                )
                cday = tq_intervals[i].day
                cstart = tq_intervals[i].hour
                cend = tq_intervals[i].hour + 1

        merged_intervals.append(
            UserInterval(day=cday + 1, startHour=cstart, endHour=cend)
        )

        return merged_intervals

    def to_quant_from_offset(self, timezone_ian: str, hour: int, day: int) -> TimeQuant:
        day_hour = TimeQuantService.from_date_with_offset(
            timezone_ian=timezone_ian, hour=hour, day=day
        )

        return self.helper_repo.get_quant_by_hour_day(
            day=day_hour.day, hour=day_hour.hour
        )
