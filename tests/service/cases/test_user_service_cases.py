import dataclasses

from service.timequant_models import UserInterval


@dataclasses.dataclass
class IntervalCase:
    local_user_intervals: list[UserInterval]
    timezone_ian: str
    utc_user_intervals: list[UserInterval]
    expected_user_intervals: list[UserInterval]


interval_cases = [
    # #left bound
    IntervalCase(
        [UserInterval(day=1, startHour=0, endHour=24)],
        "Etc/GMT+12",  # GMT -12,
        [
            UserInterval(day=7, startHour=12, endHour=24),
            UserInterval(day=1, startHour=0, endHour=12),
        ],
        [UserInterval(day=1, startHour=0, endHour=24)],
    ),
    # right bound
    IntervalCase(
        [
            UserInterval(day=7, startHour=0, endHour=24),
        ],
        "Pacific/Fakaofo",  # GMT +13:00,
        [
            UserInterval(day=7, startHour=13, endHour=24),
            UserInterval(day=1, startHour=0, endHour=13),
        ],
        [
            UserInterval(day=7, startHour=0, endHour=24),
        ],
    ),
    # few merged intervals for UTC cases
    IntervalCase(
        [
            UserInterval(day=3, startHour=0, endHour=12),
            UserInterval(day=3, startHour=12, endHour=24),
            UserInterval(day=4, startHour=1, endHour=2),
            UserInterval(day=4, startHour=3, endHour=4),
        ],
        "UTC",
        [
            UserInterval(day=3, startHour=0, endHour=24),
            UserInterval(day=4, startHour=1, endHour=2),
            UserInterval(day=4, startHour=3, endHour=4),
        ],
        [
            UserInterval(day=3, startHour=0, endHour=24),
            UserInterval(day=4, startHour=1, endHour=4),
        ],
    ),
    # median interval for middle cases
    IntervalCase(
        [
            UserInterval(day=1, startHour=17, endHour=23),
        ],
        "Europe/Zurich",
        [
            UserInterval(day=1, startHour=18, endHour=24),
        ],
        [
            UserInterval(day=1, startHour=17, endHour=23),
        ],
    ),
]
