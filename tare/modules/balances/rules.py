"""What carries over to a later period, and what is still outstanding."""

from tare.common.types import CarriedBalance

#: The most that may be carried into any one later period.
CARRY_CEILING = 20000


def sort_by_period(rows: list[CarriedBalance]) -> list[CarriedBalance]:
    return sorted(rows, key=lambda row: (row.year_starts_on, row.period, row.id))


def is_open(row: CarriedBalance) -> bool:
    """A balance nobody has cleared yet."""
    return row.cleared_on is None


def to_carry(shortfall: int) -> int:
    """How much of a shortfall goes forward.

    No more than the ceiling reaches any one later period.
    """
    return min(max(0, shortfall), CARRY_CEILING)


def outstanding(rows: list[CarriedBalance], employee_id: str, element_id: str) -> int:
    """What is still held over against one person for one element."""
    return sum(row.carried for row in rows
               if row.employee_id == employee_id
               and row.element_id == element_id and is_open(row))


def open_balances(rows: list[CarriedBalance], employee_id: str) -> list[CarriedBalance]:
    return sort_by_period([row for row in rows
                           if row.employee_id == employee_id and is_open(row)])
