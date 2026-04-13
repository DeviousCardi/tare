"""What is owed to whom, and when it has to go."""

from tare.common.dates import add_days, compare_dates, days_inclusive
from tare.common.types import Remittance

#: A remittance is due this many days after the run it belongs to.
DUE_IN_DAYS = 19


def sort_by_due(rows: list[Remittance]) -> list[Remittance]:
    return sorted(rows, key=lambda row: (row.due_on, row.id))


def due_on_for(committed_on: str) -> str:
    """The day a run's remittances have to be with the provider."""
    return add_days(committed_on, DUE_IN_DAYS)


def is_waiting(row: Remittance) -> bool:
    return row.sent_on is None


def waiting(rows: list[Remittance]) -> list[Remittance]:
    return sort_by_due([row for row in rows if is_waiting(row)])


def is_overdue(row: Remittance, on: str) -> bool:
    """Whether it should have gone by now."""
    return is_waiting(row) and compare_dates(on, row.due_on) > 0


def owed_to(rows: list[Remittance], provider_id: str) -> int:
    """What is still owed to one provider across everything waiting."""
    return sum(row.amount for row in waiting(rows) if row.provider_id == provider_id)


def days_to_go(row: Remittance, on: str) -> int:
    """How long there is left, counting both ends. Nothing once it is past."""
    if compare_dates(on, row.due_on) > 0:
        return 0
    return days_inclusive(on, row.due_on)
