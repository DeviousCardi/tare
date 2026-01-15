"""What a rate comes to when it is applied."""

from tare.common.effective import in_force_on
from tare.common.money import apply_rate
from tare.common.types import PayRate

#: How the amount on a rate reads.
FIXED = "fixed"
HOURLY = "hourly"
MULTIPLE = "multiple"
BASES = (FIXED, HOURLY, MULTIPLE)


def for_element(
    rows: list[PayRate], employee_id: str, element_id: str, day: str,
) -> PayRate | None:
    """The rate one person was on for one element on a day."""
    theirs = [row for row in rows
              if row.employee_id == employee_id and row.element_id == element_id]
    return in_force_on(theirs, day)


def amount_for(row: PayRate, hours: int, hourly_pay: int) -> int:
    """What the rate comes to for a run of hours.

    A fixed rate ignores the hours entirely — it is a sum for the period. An
    hourly rate is its own amount for each hour. A multiple is a share of the
    contract's own hourly rate, which is how time and a half is held.
    """
    if row.basis == FIXED:
        return row.amount
    if row.basis == HOURLY:
        return row.amount * max(0, hours)
    return apply_rate(hourly_pay, row.amount) * max(0, hours)


def is_hours_based(row: PayRate) -> bool:
    """Whether the rate needs hours before it comes to anything."""
    return row.basis in (HOURLY, MULTIPLE)
