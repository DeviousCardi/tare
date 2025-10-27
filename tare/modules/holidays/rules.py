"""The calendar, read without reference to who is asking."""

from tare.common.dates import compare_dates, is_weekend, parse
from tare.common.types import Holiday


def sort_by_day(rows: list[Holiday]) -> list[Holiday]:
    return sorted(rows, key=lambda row: row.holiday_on)


def days_of(rows: list[Holiday]) -> list[str]:
    """Just the days, which is what every date rule in the service takes."""
    return [row.holiday_on for row in sort_by_day(rows)]


def in_year(rows: list[Holiday], year: int) -> list[Holiday]:
    return [row for row in sort_by_day(rows) if parse(row.holiday_on).year == year]


def between(rows: list[Holiday], start: str, end: str) -> list[Holiday]:
    return [row for row in sort_by_day(rows)
            if compare_dates(row.holiday_on, start) >= 0
            and compare_dates(row.holiday_on, end) <= 0]


def falls_on_a_weekend(row: Holiday) -> bool:
    """A holiday on a weekend adds nothing; the day was not a working day anyway."""
    return is_weekend(row.holiday_on)
