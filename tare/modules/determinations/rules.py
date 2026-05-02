"""Working out what a caught engagement is deemed to pay."""

from decimal import Decimal

from tare.common.types import Determination

#: The share of the fee the Revenue allows for running the intermediary.
RUNNING_ALLOWANCE = 500


def sort_by_decided(rows: list[Determination]) -> list[Determination]:
    return sorted(rows, key=lambda row: (row.decided_on, row.id), reverse=True)


def running_allowance(fee: int) -> int:
    """What comes off the fee for the cost of running the intermediary."""
    if fee <= 0:
        return 0
    return int(Decimal(fee) * Decimal(RUNNING_ALLOWANCE) / Decimal(10000))


def deemed_payment(fee: int, allowable_expenses: int) -> int:
    """What a caught engagement is treated as having paid.

    The fee, less the running allowance and anything properly claimed. It never
    goes below nothing.
    """
    return max(0, fee - running_allowance(fee) - max(0, allowable_expenses))


def total_deemed(rows: list[Determination]) -> int:
    return sum(row.deemed_payment for row in rows if row.inside)
