"""What a scale point is worth, and what a change to it leaves owing."""

from tare.common.effective import all_in_force_on, in_force_on
from tare.common.types import ScalePoint

#: A pay year is quoted at this many days when a part of one is worked out.
DAYS_IN_YEAR = 365


def sort_by_point(rows: list[ScalePoint]) -> list[ScalePoint]:
    return sorted(rows, key=lambda row: row.point)


def points_of(rows: list[ScalePoint], scale_code: str, day: str) -> list[ScalePoint]:
    """Every point of one scale, as it stood on a day."""
    mine = [row for row in rows if row.scale_code == scale_code]
    return sort_by_point(all_in_force_on(mine, day, lambda row: row.point))


def value_at(rows: list[ScalePoint], scale_code: str, point: int, day: str) -> int | None:
    """What a year at one point of one scale was worth on a day."""
    mine = [row for row in rows if row.scale_code == scale_code and row.point == point]
    found = in_force_on(mine, day)
    return found.annual_salary if found else None


def step_up(rows: list[ScalePoint], scale_code: str, point: int, day: str) -> int | None:
    """The next point up the scale, or nothing if this is the top of it."""
    points = [row.point for row in points_of(rows, scale_code, day) if row.point > point]
    return min(points) if points else None


def arrears_for(old_value: int, new_value: int, days: int) -> int:
    """What a run of days is owed when a point is worth more than it was.

    A backdated award pays the difference for every day it reaches back over,
    at a year of 365 days.
    """
    if days <= 0 or new_value <= old_value:
        return 0
    return (new_value - old_value) * days // DAYS_IN_YEAR
