"""What a contract says, worked out without reference to who is asking."""

from tare.common.dates import compare_dates, days_inclusive, within_window
from tare.common.money import round_half_up
from tare.common.types import Contract

#: Pay is quoted for the year and worked out per week off it.
WEEKS_IN_YEAR = 52

#: What the bureau treats as a full working week when a contract is part time.
FULL_WEEK_HOURS = 37


def sort_by_start(rows: list[Contract]) -> list[Contract]:
    """Contracts oldest first, which is the order a person held them."""
    return sorted(rows, key=lambda row: (row.started_on, row.id))


def in_force_on(row: Contract, day: str) -> bool:
    """Whether the contract governed that day. The last day counts."""
    if compare_dates(day, row.started_on) < 0:
        return False
    return row.ended_on is None or within_window(day, row.started_on, row.ended_on)


def in_force_for(rows: list[Contract], employee_id: str, day: str) -> Contract | None:
    """The one contract governing a person on a day, latest start winning."""
    theirs = [row for row in sort_by_start(rows)
              if row.employee_id == employee_id and in_force_on(row, day)]
    return theirs[-1] if theirs else None


def weekly_pay(row: Contract) -> int:
    """What a week of this contract comes to, in whole minor units."""
    return round_half_up(row.annual_salary / WEEKS_IN_YEAR)


def daily_pay(row: Contract) -> int:
    """What a day of this contract comes to, over a seven-day week."""
    return round_half_up(weekly_pay(row) / 7)


def hourly_pay(row: Contract) -> int:
    """What an hour of this contract comes to, off its own contracted hours."""
    if row.hours_per_week <= 0:
        return 0
    return round_half_up(weekly_pay(row) / row.hours_per_week)


def full_time_part(row: Contract) -> int:
    """How much of a full week this contract is, in basis points.

    A contract of 37 hours is 10000. Anything longer is capped there: somebody
    contracted over the full week is still one person, not more than one.
    """
    part = round_half_up(row.hours_per_week * 10000 / FULL_WEEK_HOURS)
    return min(part, 10000)


def service_days(row: Contract, upto: str) -> int:
    """How long this person has been in service, counting both ends.

    Counted from the day the contract started. A contract that has already
    ended stops counting on the day it ended.
    """
    end = row.ended_on if row.ended_on and compare_dates(row.ended_on, upto) < 0 else upto
    if compare_dates(end, row.started_on) < 0:
        return 0
    return days_inclusive(row.started_on, end)


def service_years(row: Contract, upto: str) -> int:
    """Whole years of service, at 365 days to the year."""
    return service_days(row, upto) // 365
