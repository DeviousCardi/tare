"""How much leave a run of hours earns."""

from tare.common.money import round_half_up
from tare.common.types import LeaveAccrual

#: Hours of leave earned for each hour worked, in basis points.
#: 12.07% is the share a year's statutory leave bears to the year's working
#: hours once the leave itself is taken out of the count.
ACCRUAL_RATE = 1207

#: What the bureau treats as a day, when hours are turned back into days.
HOURS_IN_A_DAY = 8


def sort_by_period(rows: list[LeaveAccrual]) -> list[LeaveAccrual]:
    return sorted(rows, key=lambda row: (row.year_starts_on, row.period, row.id))


def earned_by(hours_worked: int) -> int:
    """Hours of leave a run of worked hours earns."""
    if hours_worked <= 0:
        return 0
    return round_half_up(hours_worked * ACCRUAL_RATE / 10000)


def earned_in_year(rows: list[LeaveAccrual], employee_id: str,
                   year_starts_on: str) -> int:
    """Everything earned so far in one leave year."""
    return sum(row.hours_earned for row in rows
               if row.employee_id == employee_id
               and row.year_starts_on == year_starts_on)


def worked_in_year(rows: list[LeaveAccrual], employee_id: str,
                   year_starts_on: str) -> int:
    return sum(row.hours_worked for row in rows
               if row.employee_id == employee_id
               and row.year_starts_on == year_starts_on)


def as_days(hours: int) -> int:
    """Hours of leave read back as whole days, rounded down.

    Half a day of leave is not a day, and the remainder stays as hours.
    """
    return hours // HOURS_IN_A_DAY
