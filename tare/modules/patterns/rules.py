"""What a working pattern expects, day by day and week by week."""

from tare.common.dates import add_days, compare_dates, days_inclusive, parse, within_window
from tare.common.errors import refuse
from tare.common.types import WorkingPattern

#: A pattern carries one figure for each day, Monday first.
DAYS_IN_WEEK = 7

#: Which of those are the ordinary working week.
WEEKDAYS = range(0, 5)


def sort_by_start(rows: list[WorkingPattern]) -> list[WorkingPattern]:
    return sorted(rows, key=lambda row: (row.starts_on, row.id))


def stands_on(row: WorkingPattern, day: str) -> bool:
    """Whether the pattern stood on that day. The last day counts."""
    if compare_dates(day, row.starts_on) < 0:
        return False
    return row.ends_on is None or within_window(day, row.starts_on, row.ends_on)


def standing_for(
    rows: list[WorkingPattern], employee_id: str, day: str,
) -> WorkingPattern | None:
    """The pattern one person was on for a day, latest start winning."""
    theirs = [row for row in sort_by_start(rows)
              if row.employee_id == employee_id and stands_on(row, day)]
    return theirs[-1] if theirs else None


def hours_on(row: WorkingPattern, day: str) -> int:
    """What the pattern expects on one named day."""
    return row.hours[parse(day).weekday()]


def weekly_hours(row: WorkingPattern) -> int:
    """What a whole week of the pattern comes to."""
    return sum(row.hours[index] for index in WEEKDAYS)


def expected_between(row: WorkingPattern, start: str, end: str) -> int:
    """What the pattern expects across a window, counting both ends."""
    cursor, total = start, 0
    for _ in range(days_inclusive(start, end)):
        if stands_on(row, cursor):
            total += hours_on(row, cursor)
        cursor = add_days(cursor, 1)
    return total


def overtime_above(row: WorkingPattern, worked: int) -> int:
    """How many hours of a week were worked beyond what the pattern expects."""
    if worked < 0:
        raise refuse("hours worked cannot be negative")
    return max(0, worked - weekly_hours(row))
