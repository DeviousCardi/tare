"""What a batch holds, and whether it is fit to apply."""

from tare.common.dates import within_window
from tare.common.money import apply_rate
from tare.common.types import ImportBatch

#: What an employer may push across.
KINDS = ("timesheets", "starters", "leavers", "absences", "expenses")

#: Where a batch has got to.
RECEIVED = "received"
ACCEPTED = "accepted"
REJECTED = "rejected"
STATUSES = (RECEIVED, ACCEPTED, REJECTED)

#: A batch the bureau could not read this much of is not fit to apply.
LEAST_READABLE = 9500


def sort_by_received(rows: list[ImportBatch]) -> list[ImportBatch]:
    return sorted(rows, key=lambda row: (row.received_on, row.id))


def is_open(row: ImportBatch) -> bool:
    """A batch still waiting on somebody."""
    return row.status == RECEIVED


def readable_share(row: ImportBatch) -> int:
    """How much of the batch the bureau could read, in basis points."""
    if row.rows_offered <= 0:
        return 0
    return round(row.rows_read * 10000 / row.rows_offered)


def rows_missed(row: ImportBatch) -> int:
    return max(0, row.rows_offered - row.rows_read)


def is_fit(row: ImportBatch) -> bool:
    """Whether enough of the batch came through to be worth applying."""
    return readable_share(row) >= LEAST_READABLE


def between(rows: list[ImportBatch], start: str, end: str) -> list[ImportBatch]:
    """Batches received in a window. Both ends count."""
    return sort_by_received([row for row in rows
                             if within_window(row.received_on, start, end)])


def share_of(rows_read: int, basis_points: int) -> int:
    """A share of a row count, for a caller sampling a batch."""
    return apply_rate(rows_read, basis_points)
