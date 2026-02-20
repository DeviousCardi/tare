"""When a premium applies, and what it comes to."""

from tare.common.dates import is_weekend
from tare.common.money import apply_rate
from tare.common.types import Premium


def sort_by_code(rows: list[Premium]) -> list[Premium]:
    return sorted(rows, key=lambda row: row.code)


def covers_hour(row: Premium, hour: int) -> bool:
    """Whether the premium covers one hour of the clock.

    A window that wraps past midnight — ten at night to six in the morning —
    covers the hours either side of it rather than none of them.
    """
    if row.from_hour <= row.to_hour:
        return row.from_hour <= hour < row.to_hour
    return hour >= row.from_hour or hour < row.to_hour


def applies_on(row: Premium, day: str) -> bool:
    """Whether the premium applies at all on that day."""
    return is_weekend(day) if row.weekend_only else True


def premium_on(row: Premium, hourly_pay: int, hours: int) -> int:
    """What the uplift comes to for a run of hours at one hourly rate."""
    if hours <= 0 or hourly_pay <= 0:
        return 0
    return apply_rate(hourly_pay, row.rate_basis_points) * hours


def best_of(rows: list[Premium], hour: int, day: str) -> Premium | None:
    """The premium worth most of those covering an hour. Ties go to the code."""
    covering = [row for row in sort_by_code(rows)
                if covers_hour(row, hour) and applies_on(row, day)]
    if not covering:
        return None
    return max(covering, key=lambda row: (row.rate_basis_points, ))
