"""Which allowances somebody was on, and what they come to."""

from tare.common.dates import compare_dates, within_window
from tare.common.types import Allowance


def sort_by_start(rows: list[Allowance]) -> list[Allowance]:
    return sorted(rows, key=lambda row: (row.starts_on, row.id))


def stands_on(row: Allowance, day: str) -> bool:
    """Whether the allowance was being paid on that day. The last day counts."""
    if compare_dates(day, row.starts_on) < 0:
        return False
    return row.ends_on is None or within_window(day, row.starts_on, row.ends_on)


def standing_for(rows: list[Allowance], employee_id: str, day: str) -> list[Allowance]:
    """Every allowance one person was on for a day, earliest first."""
    return sort_by_start([row for row in rows
                          if row.employee_id == employee_id and stands_on(row, day)])


def comes_to(rows: list[Allowance]) -> int:
    return sum(row.amount for row in rows)


def by_element(rows: list[Allowance]) -> dict[str, int]:
    """What the allowances come to, split by what they are paid as."""
    found: dict[str, int] = {}
    for row in rows:
        found[row.element_id] = found.get(row.element_id, 0) + row.amount
    return dict(sorted(found.items()))
