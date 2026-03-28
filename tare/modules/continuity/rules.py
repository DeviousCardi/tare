"""Which runs of employment join up, and how long the whole comes to."""

from tare.common.dates import compare_dates, days_inclusive
from tare.common.types import ServiceRecord

#: A break no longer than this leaves continuous service unbroken.
BREAK_DAYS = 7


def sort_by_start(rows: list[ServiceRecord]) -> list[ServiceRecord]:
    return sorted(rows, key=lambda row: (row.started_on, row.id))


def gap_between(earlier: ServiceRecord, later: ServiceRecord) -> int:
    """Days between the end of one run and the start of the next."""
    if earlier.ended_on is None:
        return 0
    if compare_dates(later.started_on, earlier.ended_on) <= 0:
        return 0
    return days_inclusive(earlier.ended_on, later.started_on) - 2


def joins_up(earlier: ServiceRecord, later: ServiceRecord) -> bool:
    """Whether the break between two runs is short enough to be no break at all."""
    return gap_between(earlier, later) < BREAK_DAYS


def continuous_from(rows: list[ServiceRecord], employee_id: str) -> str | None:
    """The day continuous service began, walking back through the joins."""
    theirs = sort_by_start([row for row in rows if row.employee_id == employee_id])
    if not theirs:
        return None
    started = theirs[-1].started_on
    for earlier, later in zip(reversed(theirs[:-1]), reversed(theirs[1:])):
        if not joins_up(earlier, later):
            break
        started = earlier.started_on
    return started


def service_days(rows: list[ServiceRecord], employee_id: str, upto: str) -> int:
    """How many days of continuous service somebody has, counting both ends."""
    started = continuous_from(rows, employee_id)
    if started is None or compare_dates(upto, started) < 0:
        return 0
    return days_inclusive(started, upto)


def service_years(rows: list[ServiceRecord], employee_id: str, upto: str) -> int:
    return service_days(rows, employee_id, upto) // 365
