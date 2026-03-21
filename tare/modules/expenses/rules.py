"""Which claims get paid, and what they come to."""

from tare.common.dates import within_window
from tare.common.types import ExpenseClaim

#: Where a claim has got to.
CLAIMED = "claimed"
APPROVED = "approved"
QUERIED = "queried"
REJECTED = "rejected"
STATUSES = (CLAIMED, APPROVED, QUERIED, REJECTED)


def sort_by_incurred(rows: list[ExpenseClaim]) -> list[ExpenseClaim]:
    return sorted(rows, key=lambda row: (row.incurred_on, row.id))


def is_open(row: ExpenseClaim) -> bool:
    """A claim still waiting on somebody."""
    return row.status in (CLAIMED, QUERIED)


def reimbursable(row: ExpenseClaim) -> bool:
    """Whether the claim gets paid with the next run."""
    return row.status != REJECTED


def payable(rows: list[ExpenseClaim]) -> list[ExpenseClaim]:
    return sort_by_incurred([row for row in rows if reimbursable(row)])


def comes_to(rows: list[ExpenseClaim]) -> int:
    return sum(row.amount for row in payable(rows))


def between(rows: list[ExpenseClaim], start: str, end: str) -> list[ExpenseClaim]:
    """Claims incurred in a window. Both ends count."""
    return sort_by_incurred([row for row in rows
                             if within_window(row.incurred_on, start, end)])


def by_kind(rows: list[ExpenseClaim]) -> dict[str, int]:
    found: dict[str, int] = {}
    for row in payable(rows):
        found[row.kind] = found.get(row.kind, 0) + row.amount
    return dict(sorted(found.items()))
