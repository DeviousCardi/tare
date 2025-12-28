"""What a run of leave costs somebody, and what state a request is in."""

from tare.common.dates import compare_dates, days_inclusive, overlaps, within_window
from tare.common.types import LeaveRequest

#: What can become of a request.
ASKED = "asked"
GRANTED = "granted"
REFUSED = "refused"
WITHDRAWN = "withdrawn"
STATUSES = (ASKED, GRANTED, REFUSED, WITHDRAWN)

#: The states that actually take days off somebody's entitlement.
COUNTS_AGAINST = (GRANTED,)


def sort_by_start(rows: list[LeaveRequest]) -> list[LeaveRequest]:
    return sorted(rows, key=lambda row: (row.starts_on, row.id))


def is_open(row: LeaveRequest) -> bool:
    """Whether the request is still waiting on somebody."""
    return row.status == ASKED


def counts_against_entitlement(row: LeaveRequest) -> bool:
    return row.status in COUNTS_AGAINST


def days_of(row: LeaveRequest, holidays: list[str]) -> int:
    """How many days of entitlement this run of leave uses up.

    Leave is counted in the days somebody would otherwise have been at work.
    """
    return days_inclusive(row.starts_on, row.ends_on)


def covers(row: LeaveRequest, day: str) -> bool:
    return within_window(day, row.starts_on, row.ends_on)


def clashes_with(row: LeaveRequest, other: LeaveRequest) -> bool:
    """Two runs of leave clash only when both are still live."""
    if row.status in (REFUSED, WITHDRAWN) or other.status in (REFUSED, WITHDRAWN):
        return False
    return overlaps(row.starts_on, row.ends_on, other.starts_on, other.ends_on)


def taken_between(
    rows: list[LeaveRequest], start: str, end: str, holidays: list[str],
) -> int:
    """Days of granted leave falling in a window, counting both ends."""
    total = 0
    for row in rows:
        if not counts_against_entitlement(row):
            continue
        if not overlaps(row.starts_on, row.ends_on, start, end):
            continue
        first = row.starts_on if compare_dates(row.starts_on, start) >= 0 else start
        last = row.ends_on if compare_dates(row.ends_on, end) <= 0 else end
        total += days_inclusive(first, last)
    return total
