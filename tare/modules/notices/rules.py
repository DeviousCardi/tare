"""Which notices are still waiting to go out."""

from tare.common.dates import compare_dates, days_inclusive
from tare.common.types import Notice

#: What the bureau writes to people about.
KINDS = ("payslip", "year end", "underpayment", "order served", "scheme joined")

#: A notice not out of the door in this many days is late.
PROMPT_DAYS = 5


def sort_by_raised(rows: list[Notice]) -> list[Notice]:
    return sorted(rows, key=lambda row: (row.raised_on, row.id))


def is_waiting(row: Notice) -> bool:
    return row.sent_on is None


def waiting(rows: list[Notice]) -> list[Notice]:
    return sort_by_raised([row for row in rows if is_waiting(row)])


def days_waiting(row: Notice, upto: str) -> int:
    """How long the notice has been sitting there, counting both ends."""
    if not is_waiting(row) or compare_dates(upto, row.raised_on) < 0:
        return 0
    return days_inclusive(row.raised_on, upto)


def is_late(row: Notice, upto: str) -> bool:
    return days_waiting(row, upto) > PROMPT_DAYS
