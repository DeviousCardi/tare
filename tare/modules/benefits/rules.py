"""What a benefit is worth to the person who has it."""

from tare.common.dates import compare_dates, within_window
from tare.common.types import BenefitAward, BenefitClass


def sort_by_start(rows: list[BenefitAward]) -> list[BenefitAward]:
    return sorted(rows, key=lambda row: (row.starts_on, row.id))


def held_on(row: BenefitAward, day: str) -> bool:
    """Whether somebody had the use of it that day. The last day counts."""
    if compare_dates(day, row.starts_on) < 0:
        return False
    return row.ends_on is None or within_window(day, row.starts_on, row.ends_on)


def held_by(rows: list[BenefitAward], employee_id: str, day: str) -> list[BenefitAward]:
    return sort_by_start([row for row in rows
                          if row.employee_id == employee_id and held_on(row, day)])


def taxable_value(row: BenefitAward, worth: int) -> int:
    """What the benefit adds to what the levy is worked out on.

    A benefit is worth what it is worth; what the person puts toward it is
    theirs to settle with the employer.
    """
    return worth


def contribution_of(rows: list[BenefitAward]) -> int:
    return sum(row.contribution for row in rows)
