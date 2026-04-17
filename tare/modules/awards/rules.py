"""What an award comes to, and what it leaves somebody on."""

from decimal import Decimal

from tare.common.types import PayAward

#: How an award is quoted.
FLAT = "flat"
SHARE = "share"
BASES = (FLAT, SHARE)


def sort_by_employee(rows: list[PayAward]) -> list[PayAward]:
    return sorted(rows, key=lambda row: (row.employee_id, row.id))


def uplift_of(old_salary: int, basis: str, amount: int) -> int:
    """What the award adds to somebody's salary."""
    if old_salary <= 0 or amount <= 0:
        return 0
    if basis == SHARE:
        return int(Decimal(old_salary) * Decimal(amount) / Decimal(10000))
    return amount


def new_salary(old_salary: int, basis: str, amount: int) -> int:
    """What somebody is on after the award."""
    return old_salary + uplift_of(old_salary, basis, amount)


def cost_of(rows: list[PayAward]) -> int:
    """What a run of awards adds to the annual wage bill."""
    return sum(row.new_salary - row.old_salary for row in rows)


def average_share(rows: list[PayAward]) -> int:
    """The average uplift across a run of awards, in basis points."""
    old = sum(row.old_salary for row in rows)
    if old <= 0:
        return 0
    return round(cost_of(rows) * 10000 / old)
