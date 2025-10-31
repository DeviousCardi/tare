"""What a levy code means, worked out on its own."""

from tare.common.effective import all_in_force_on, in_force_on
from tare.common.money import allocate
from tare.common.types import LevyCode

#: How the free pay a code carries is spent across the year.
CUMULATIVE = "cumulative"
PERIOD = "period"
BASES = (CUMULATIVE, PERIOD)

#: How many times a year each kind of payroll runs.
PERIODS_A_YEAR = {"monthly": 12, "fortnightly": 26, "weekly": 52}


def for_code(rows: list[LevyCode], code: str, day: str) -> LevyCode | None:
    """The version of one code in force on a day."""
    return in_force_on([row for row in rows if row.code == code], day)


def every_code_on(rows: list[LevyCode], day: str) -> list[LevyCode]:
    return all_in_force_on(rows, day, lambda row: row.code)


def is_cumulative(row: LevyCode) -> bool:
    return row.basis == CUMULATIVE


def free_pay_for_period(row: LevyCode, frequency: str, period: int) -> int:
    """The free pay this code gives by the end of period `period`.

    A cumulative code has given a share of the year's allowance for every
    period so far, so the free pay grows through the year and an unused part of
    it is still there next time. A period code gives one period's worth and
    forgets what went before.

    The year's allowance is split into whole minor units that sum back to it,
    so twelve months of a cumulative code come to the allowance exactly and
    never a penny over or under.
    """
    count = PERIODS_A_YEAR[frequency]
    shares = allocate(row.annual_allowance, count)
    if period < 1 or period > count:
        return 0
    if is_cumulative(row):
        return sum(shares[:period])
    return shares[period - 1]
