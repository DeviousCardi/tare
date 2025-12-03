"""Which post somebody held on a day."""

from tare.common.dates import compare_dates, within_window
from tare.common.types import Position


def sort_by_held_from(rows: list[Position]) -> list[Position]:
    return sorted(rows, key=lambda row: (row.held_from, row.id))


def held_on(row: Position, day: str) -> bool:
    """Whether the post was held on that day. The last day counts."""
    if compare_dates(day, row.held_from) < 0:
        return False
    return row.held_to is None or within_window(day, row.held_from, row.held_to)


def held_by(rows: list[Position], employee_id: str, day: str) -> Position | None:
    """The post one person held on a day, latest appointment winning."""
    theirs = [row for row in sort_by_held_from(rows)
              if row.employee_id == employee_id and held_on(row, day)]
    return theirs[-1] if theirs else None


def in_cost_centre(rows: list[Position], cost_centre_id: str, day: str) -> list[Position]:
    """Every post booked to one centre on a day."""
    return [row for row in sort_by_held_from(rows)
            if row.cost_centre_id == cost_centre_id and held_on(row, day)]


def headcount(rows: list[Position], department_id: str, day: str) -> int:
    """How many people a department had on a day, counting each once."""
    return len({row.employee_id for row in rows
                if row.department_id == department_id and held_on(row, day)})
