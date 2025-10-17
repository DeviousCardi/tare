"""What is true about an employer regardless of who is asking."""

from tare.common.dates import compare_dates, within_window
from tare.common.types import Employer

#: A reference reads E-0001. Four digits is more employers than we will ever run.
REFERENCE_WIDTH = 4


def sort_by_reference(rows: list[Employer]) -> list[Employer]:
    """Employers in reference order, which is the order they were taken on."""
    return sorted(rows, key=lambda row: row.reference)


def next_reference(rows: list[Employer]) -> str:
    """The reference the next employer taken on will carry.

    Counted from the highest already issued rather than from how many there
    are, so closing an employer never lets a later one reuse its reference.
    """
    issued = [int(row.reference.split("-")[1]) for row in rows if "-" in row.reference]
    return f"E-{(max(issued) + 1 if issued else 1):0{REFERENCE_WIDTH}d}"


def is_open_on(row: Employer, day: str) -> bool:
    """Whether we were running this employer's payroll on that day.

    Open from the day they were taken on until the day they closed, and the day
    they closed counts — a payroll run dated the closing day is the final one
    and has to be allowed to happen.
    """
    if compare_dates(day, row.opened_on) < 0:
        return False
    return row.closed_on is None or within_window(day, row.opened_on, row.closed_on)


def pay_day_of(row: Employer, month_start: str) -> str:
    """The day of that month this employer's people are paid.

    A pay day past the end of a short month falls on its last day rather than
    spilling into the next one.
    """
    from calendar import monthrange
    from tare.common.dates import parse, show
    from datetime import date

    first = parse(month_start)
    last = monthrange(first.year, first.month)[1]
    return show(date(first.year, first.month, min(row.pay_day, last)))
