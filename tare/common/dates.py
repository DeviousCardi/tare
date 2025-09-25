"""Calendar dates, inclusive windows and working days.

Dates are `YYYY-MM-DD` strings everywhere, never `date` objects on a row and
never a timestamp. Nothing here reads the wall clock: a caller that means today
passes the day it means, which is what makes the suite give the same answer on
any machine at any hour.

Windows include **both** ends. That is the rule the whole service is built on
and the one place a reader is most likely to assume otherwise.
"""

from datetime import date, timedelta

from tare.common.errors import refuse


def is_calendar_date(value: str) -> bool:
    """Whether the string is a real day. `2025-02-30` is not."""
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def parse(value: str) -> date:
    if not is_calendar_date(value):
        raise refuse(f"{value} is not a calendar date")
    return date.fromisoformat(value)


def show(value: date) -> str:
    return value.isoformat()


def compare_dates(left: str, right: str) -> int:
    """-1, 0 or 1, so a sort key reads the same as everywhere else."""
    a, b = parse(left), parse(right)
    return (a > b) - (a < b)


def add_days(value: str, days: int) -> str:
    return show(parse(value) + timedelta(days=days))


def days_inclusive(start: str, end: str) -> int:
    """How many days the window covers, counting both ends.

    A window that ends before it starts is refused rather than counted as
    empty: a caller that wrote the ends the wrong way round meant something
    else, and quietly returning nothing hides it until the money is wrong.
    """
    a, b = parse(start), parse(end)
    if b < a:
        raise refuse(f"window {start}..{end} ends before it starts")
    return (b - a).days + 1


def within_window(value: str, start: str, end: str) -> bool:
    """Whether the day falls in the window. Both ends count."""
    return compare_dates(value, start) >= 0 and compare_dates(value, end) <= 0


def overlaps(start: str, end: str, other_start: str, other_end: str) -> bool:
    """Whether two inclusive windows share any day at all."""
    return compare_dates(start, other_end) <= 0 and compare_dates(other_start, end) <= 0


def is_weekend(value: str) -> bool:
    return parse(value).weekday() >= 5


def is_working_day(value: str, holidays: list[str]) -> bool:
    """A weekday the Revenue's calendar does not hold as a holiday."""
    return not is_weekend(value) and value not in holidays


def on_or_after_working_day(value: str, holidays: list[str]) -> str:
    """The day itself if it is a working day, otherwise the next one that is."""
    cursor = value
    for _ in range(400):
        if is_working_day(cursor, holidays):
            return cursor
        cursor = add_days(cursor, 1)
    raise refuse(f"found no working day on or after {value}")


def add_working_days(value: str, count: int, holidays: list[str]) -> str:
    """Step `count` working days on from `value`.

    The starting day is not counted whether or not it is itself a working day,
    so three working days on from a Friday is the following Wednesday.
    """
    if count < 0:
        raise refuse("cannot step a negative number of working days")
    cursor = value
    stepped = 0
    while stepped < count:
        cursor = add_days(cursor, 1)
        if is_working_day(cursor, holidays):
            stepped += 1
    return cursor


def working_days_inclusive(start: str, end: str, holidays: list[str]) -> int:
    """How many working days the window covers, counting both ends."""
    days = days_inclusive(start, end)
    cursor = start
    count = 0
    for _ in range(days):
        if is_working_day(cursor, holidays):
            count += 1
        cursor = add_days(cursor, 1)
    return count
