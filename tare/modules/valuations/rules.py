"""What a kind of benefit is worth over part of a year."""

from tare.common.dates import days_inclusive
from tare.common.types import BenefitClass

#: How a class is valued.
FLAT = "flat"
SHARED = "shared"
BASES = (FLAT, SHARED)

#: The year a benefit is quoted over.
DAYS_IN_YEAR = 365


def sort_by_code(rows: list[BenefitClass]) -> list[BenefitClass]:
    return sorted(rows, key=lambda row: row.code)


def for_days(row: BenefitClass, days: int) -> int:
    """What the class is worth over a run of days."""
    if days <= 0:
        return 0
    if days >= DAYS_IN_YEAR:
        return row.annual_value
    return row.annual_value * days // DAYS_IN_YEAR


def for_window(row: BenefitClass, start: str, end: str) -> int:
    """What the class is worth over a window, counting both ends."""
    return for_days(row, days_inclusive(start, end))


def shared_between(row: BenefitClass, people: int) -> int:
    """What each person is worth of a benefit several of them share."""
    if row.basis != SHARED or people <= 0:
        return row.annual_value
    return row.annual_value // people
