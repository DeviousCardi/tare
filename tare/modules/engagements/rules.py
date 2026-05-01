"""Whether an engagement falls inside the rules."""

from tare.common.dates import compare_dates, within_window
from tare.common.types import Engagement


def sort_by_started(rows: list[Engagement]) -> list[Engagement]:
    return sorted(rows, key=lambda row: (row.started_on, row.id))


def running_on(row: Engagement, day: str) -> bool:
    """Whether the engagement was running that day. The last day counts."""
    if compare_dates(day, row.started_on) < 0:
        return False
    return row.ended_on is None or within_window(day, row.started_on, row.ended_on)


def is_inside(row: Engagement) -> bool:
    """Whether the engagement is caught by the deemed payment rules.

    Somebody working under the employer's own supervision is caught.
    """
    return row.supervised


def running(rows: list[Engagement], employer_id: str, day: str) -> list[Engagement]:
    return sort_by_started([row for row in rows
                            if row.employer_id == employer_id and running_on(row, day)])
