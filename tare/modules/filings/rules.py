"""When a return is due, and what it owes."""

from tare.common.dates import add_days, compare_dates, days_inclusive
from tare.common.types import Filing

#: A return is due this many days after the period it covers ends.
DUE_IN_DAYS = 14


def sort_by_period(rows: list[Filing]) -> list[Filing]:
    return sorted(rows, key=lambda row: (row.period, row.id))


def due_on_for(period_end: str) -> str:
    """The day a return covering a period has to be with the Revenue."""
    return add_days(period_end, DUE_IN_DAYS)


def owed_by(row: Filing) -> int:
    """What the return says the employer owes."""
    return row.levy + row.contributions


def is_late(row: Filing, on: str) -> bool:
    """Whether the return should have been in by now."""
    return compare_dates(on, row.period_end) > 0


def days_to_go(row: Filing, on: str) -> int:
    """How long there is left, counting both ends. Nothing once it is past."""
    if compare_dates(on, row.due_on) > 0:
        return 0
    return days_inclusive(on, row.due_on)
