"""How much of somebody's pay an order may actually reach."""

from tare.common.dates import compare_dates, within_window
from tare.common.types import ProtectedEarnings


def sort_by_start(rows: list[ProtectedEarnings]) -> list[ProtectedEarnings]:
    return sorted(rows, key=lambda row: (row.starts_on, row.id))


def stands_on(row: ProtectedEarnings, day: str) -> bool:
    """Whether the floor stood on that day. The last day counts."""
    if compare_dates(day, row.starts_on) < 0:
        return False
    return row.ends_on is None or within_window(day, row.starts_on, row.ends_on)


def standing_for(
    rows: list[ProtectedEarnings], employee_id: str, day: str,
) -> ProtectedEarnings | None:
    """The floor one person was on for a day, latest start winning."""
    theirs = [row for row in sort_by_start(rows)
              if row.employee_id == employee_id and stands_on(row, day)]
    return theirs[-1] if theirs else None


def available_for_orders(pay: int, floor: int) -> int:
    """How much of a figure of pay an order may reach.

    Everything above the protected floor is fair game; everything at or below
    it is not.
    """
    return pay - floor


def breaches(pay: int, floor: int, taken: int) -> bool:
    """Whether taking that much would take the pay below the floor."""
    return pay - taken < floor


def most_takeable(pay: int, floor: int, asked: int) -> int:
    """The largest part of what an order asked for that may actually be taken."""
    return max(0, min(asked, available_for_orders(pay, floor)))
