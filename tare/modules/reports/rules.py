"""Gathering figures that cut across the areas."""

from tare.common.types import Payslip


def cost_of_employment(slips: list[Payslip]) -> int:
    """What the people actually cost: what they earned, gross."""
    return sum(row.gross for row in slips)


def owed_to_revenue(slips: list[Payslip]) -> int:
    return sum(row.levy + row.contributions for row in slips)


def paid_out(slips: list[Payslip]) -> int:
    return sum(row.net for row in slips)


def by_period(slips: list[Payslip]) -> dict[int, int]:
    """What each period came to, in period order."""
    found: dict[int, int] = {}
    for row in slips:
        found[row.period] = found.get(row.period, 0) + row.gross
    return dict(sorted(found.items()))


def headcount_by_period(slips: list[Payslip]) -> dict[int, int]:
    found: dict[int, set] = {}
    for row in slips:
        found.setdefault(row.period, set()).add(row.employee_id)
    return {period: len(people) for period, people in sorted(found.items())}
