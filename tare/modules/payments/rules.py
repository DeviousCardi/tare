"""What a payment run still owes, and what came back."""

from tare.common.types import PaymentInstruction

#: Where an instruction has got to.
ISSUED = "issued"
SETTLED = "settled"
FAILED = "failed"
CANCELLED = "cancelled"
STATUSES = (ISSUED, SETTLED, FAILED, CANCELLED)

#: The states an instruction can still move on from.
LIVE = (ISSUED,)


def sort_by_issue(rows: list[PaymentInstruction]) -> list[PaymentInstruction]:
    return sorted(rows, key=lambda row: (row.issued_on, row.id))


def is_live(row: PaymentInstruction) -> bool:
    """An instruction still on its way."""
    return row.status in LIVE


def outstanding(rows: list[PaymentInstruction]) -> list[PaymentInstruction]:
    """Everything the run has not yet got money out of the door for."""
    return sort_by_issue([row for row in rows
                          if row.status not in (SETTLED, FAILED, CANCELLED)])


def settled_total(rows: list[PaymentInstruction]) -> int:
    return sum(row.amount for row in rows if row.status == SETTLED)


def failed_total(rows: list[PaymentInstruction]) -> int:
    return sum(row.amount for row in rows if row.status == FAILED)


def outstanding_total(rows: list[PaymentInstruction]) -> int:
    return sum(row.amount for row in outstanding(rows))
