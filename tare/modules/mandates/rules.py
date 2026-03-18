"""Which mandate somebody's pay goes to."""

from tare.common.dates import compare_dates, within_window
from tare.common.types import Mandate


def sort_by_start(rows: list[Mandate]) -> list[Mandate]:
    return sorted(rows, key=lambda row: (row.starts_on, row.id))


def stands_on(row: Mandate, day: str) -> bool:
    """Whether the mandate stood on that day.

    A mandate stands from the day it starts until the day it ends.
    """
    if compare_dates(day, row.starts_on) < 0:
        return False
    return row.ends_on is None or within_window(day, row.starts_on, row.ends_on)


def standing_for(rows: list[Mandate], employee_id: str, day: str) -> Mandate | None:
    """The mandate one person's pay goes to on a day, latest start winning."""
    theirs = [row for row in sort_by_start(rows)
              if row.employee_id == employee_id and stands_on(row, day)]
    return theirs[-1] if theirs else None


def holders_of(rows: list[Mandate]) -> list[str]:
    """Every name a run of mandates is held in, in a settled order."""
    return sorted({row.holder for row in rows})
