"""What an order still wants, and in what order orders are worked."""

from tare.common.types import EarningsOrder


def by_priority(rows: list[EarningsOrder]) -> list[EarningsOrder]:
    """Orders in the order they are worked: priority, then oldest first."""
    return sorted(rows, key=lambda row: (row.priority, row.made_on, row.id))


def is_live(row: EarningsOrder) -> bool:
    """An order nobody has discharged and that still wants something."""
    return row.discharged_on is None and row.collected < row.total


def remaining(row: EarningsOrder) -> int:
    """What is still to collect. It never goes below nothing."""
    return max(0, row.total - row.collected)


def due_now(row: EarningsOrder) -> int:
    """What the order asks for this period."""
    if not is_live(row):
        return 0
    return row.per_period


def periods_left(row: EarningsOrder) -> int:
    """How many more periods the order will run for, at its own rate."""
    if not is_live(row) or row.per_period <= 0:
        return 0
    left = remaining(row)
    whole, over = divmod(left, row.per_period)
    return whole + (1 if over else 0)


def live_orders(rows: list[EarningsOrder], employee_id: str) -> list[EarningsOrder]:
    return by_priority([row for row in rows
                        if row.employee_id == employee_id and is_live(row)])
