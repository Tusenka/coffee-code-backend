from __future__ import annotations

from typing import Callable, NamedTuple

from pydantic import BaseModel, Field
from pydantic_extra_types.timezone_name import TimeZoneName

from db.model import TimeQuant as DaoTimeQuant


# [TimeQuant(day, hour, id), ]
class UserInterval(BaseModel):
    day: int
    startHour: int = Field(alias="startHour")
    endHour: int = Field(alias="endHour")

    def __hash__(self):
        return hash(
            (type(self),) + tuple(getattr(self, f) for f in self.model_fields.keys())
        )


class TimeQuantList(BaseModel):
    intervals: list[TimeQuant]

    @staticmethod
    def from_dao(
        intervals: list[DaoTimeQuant],
        timezone_name: TimeZoneName,
        to_date_with_offset: Callable[[str, int, int], DayHour],
    ):
        return TimeQuantList(
            intervals=[
                TimeQuant.from_dao(
                    tq=i,
                    timezone_name=timezone_name,
                    to_date_with_offset=to_date_with_offset,
                )
                for i in intervals
            ]
        )


class TimeQuant(BaseModel):
    id: int
    day: int
    hour: int

    @staticmethod
    def from_dao(
        tq: DaoTimeQuant,
        timezone_name: str,
        to_date_with_offset: Callable[[str, int, int], DayHour],
    ) -> TimeQuant:
        dh = to_date_with_offset(timezone_name, tq.hour, tq.day)

        return TimeQuant(id=tq.id, day=dh.day, hour=dh.hour)


class DayHour(NamedTuple):
    hour: int
    day: int
