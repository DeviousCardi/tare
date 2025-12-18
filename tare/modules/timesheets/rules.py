"""What a run of timesheet lines comes to."""

from tare.common.dates import within_window
from tare.common.types import TimesheetLine


def sort_by_day(rows: list[TimesheetLine]) -> list[TimesheetLine]:
    return sorted(rows, key=lambda row: (row.worked_on, row.id))


def approved_only(rows: list[TimesheetLine]) -> list[TimesheetLine]:
    """Only approved hours reach a payroll run. Nothing else is paid."""
    return [row for row in rows if row.approved]


def between(rows: list[TimesheetLine], start: str, end: str) -> list[TimesheetLine]:
    """Lines falling in a window. Both ends count."""
    return sort_by_day([row for row in rows if within_window(row.worked_on, start, end)])


def hours_between(rows: list[TimesheetLine], start: str, end: str) -> int:
    """Approved hours across a window."""
    return sum(row.hours for row in approved_only(between(rows, start, end)))


def hours_by_element(rows: list[TimesheetLine], start: str, end: str) -> dict[str, int]:
    """Approved hours across a window, split by what they are paid as."""
    found: dict[str, int] = {}
    for row in approved_only(between(rows, start, end)):
        found[row.element_id] = found.get(row.element_id, 0) + row.hours
    return dict(sorted(found.items()))


def days_worked(rows: list[TimesheetLine], start: str, end: str) -> int:
    """How many separate days carried approved hours."""
    return len({row.worked_on for row in approved_only(between(rows, start, end))
                if row.hours > 0})
