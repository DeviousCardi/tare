"""Which periods a suspension covers."""

from tare.common.types import Suspension

#: Why a deduction stops being taken.
NO_PAY = "no pay to take it from"
OUTRANKED = "an order takes priority"
ASKED = "the employee asked"
REASONS = (NO_PAY, OUTRANKED, ASKED)


def sort_by_period(rows: list[Suspension]) -> list[Suspension]:
    return sorted(rows, key=lambda row: (row.year_starts_on, row.from_period, row.id))


def covers(row: Suspension, period: int, year_starts_on: str) -> bool:
    """Whether the suspension was in force for one period of one year."""
    if row.year_starts_on != year_starts_on:
        return False
    if period < row.from_period:
        return False
    return row.to_period is None or period <= row.to_period


def is_open(row: Suspension) -> bool:
    """A suspension nobody has lifted yet."""
    return row.to_period is None


def periods_covered(row: Suspension, periods_in_year: int) -> int:
    """How many periods the suspension ran for."""
    last = row.to_period if row.to_period is not None else periods_in_year
    return max(0, last - row.from_period + 1)


def suspended_elements(
    rows: list[Suspension], employee_id: str, period: int, year_starts_on: str,
) -> list[str]:
    """Every element held off one person's pay for one period, in a settled order."""
    return sorted({row.element_id for row in rows
                   if row.employee_id == employee_id
                   and covers(row, period, year_starts_on)})
