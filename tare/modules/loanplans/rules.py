"""What a loan plan takes out of a period's pay."""

from tare.common.money import apply_rate
from tare.common.types import LoanPlan

#: The kinds of plan the Revenue publishes.
PLAN_TYPES = ("one", "two", "postgraduate")


def sort_by_started(rows: list[LoanPlan]) -> list[LoanPlan]:
    return sorted(rows, key=lambda row: (row.started_on, row.id))


def settled(row: LoanPlan) -> bool:
    """Whether the plan has been repaid in full."""
    return row.settled_on is not None or row.collected >= row.total


def remaining(row: LoanPlan) -> int:
    """What is still to repay. It never goes below nothing."""
    return max(0, row.total - row.collected)


def above_threshold(row: LoanPlan, pay: int) -> int:
    """The part of a period's pay the contribution is worked out on."""
    return max(0, pay - row.period_threshold)


def due_now(row: LoanPlan, pay: int) -> int:
    """What comes out of this period's pay.

    A share of everything above the threshold, and never more than the plan is
    still owed.
    """
    asked = apply_rate(above_threshold(row, pay), row.rate_basis_points)
    return min(asked, remaining(row))


def live_plans(rows: list[LoanPlan], employee_id: str) -> list[LoanPlan]:
    return sort_by_started([row for row in rows
                            if row.employee_id == employee_id and not settled(row)])
