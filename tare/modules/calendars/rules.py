"""Where a day falls in an employer's pay year."""

from calendar import monthrange
from datetime import date

from tare.common.dates import add_days, compare_dates, days_inclusive, parse, show
from tare.common.errors import refuse
from tare.common.periods import Window
from tare.common.types import PayCalendar

#: How long a period of each frequency runs, in days. Monthly follows the
#: calendar rather than a fixed count.
RUN_OF_DAYS = {"weekly": 7, "fortnightly": 14}
PERIODS_A_YEAR = {"weekly": 52, "fortnightly": 26, "monthly": 12}
FREQUENCIES = tuple(PERIODS_A_YEAR)


def months_on(day: str, months: int) -> str:
    """The same day of the month, `months` on. A short month takes its last day."""
    when = parse(day)
    total = when.month - 1 + months
    year = when.year + total // 12
    month = total % 12 + 1
    return show(date(year, month, min(when.day, monthrange(year, month)[1])))


def period_window(row: PayCalendar, period: int) -> Window:
    """The window one period covers. Both ends count, as everywhere else."""
    if period < 1 or period > row.periods:
        raise refuse(f"period {period} is not in a year of {row.periods}")
    if row.frequency == "monthly":
        start = months_on(row.year_starts_on, period - 1)
        return Window(start, add_days(months_on(row.year_starts_on, period), -1))
    run = RUN_OF_DAYS[row.frequency]
    start = add_days(row.year_starts_on, (period - 1) * run)
    return Window(start, add_days(start, run - 1))


def year_window(row: PayCalendar) -> Window:
    """The whole pay year the calendar covers."""
    return Window(row.year_starts_on, period_window(row, row.periods).end)


def period_holding(row: PayCalendar, day: str) -> int | None:
    """Which period a day falls in, or nothing if it falls outside the year."""
    if compare_dates(day, row.year_starts_on) < 0:
        return None
    if row.frequency == "monthly":
        for period in range(1, row.periods + 1):
            window = period_window(row, period)
            if compare_dates(day, window.start) >= 0 and compare_dates(day, window.end) <= 0:
                return period
        return None
    run = RUN_OF_DAYS[row.frequency]
    elapsed = days_inclusive(row.year_starts_on, day)
    period = elapsed // run + 1
    return period if period <= row.periods else None


def pay_day_for(row: PayCalendar, period: int, pay_day: int) -> str:
    """The day a period is paid: that day of the month the period ends in."""
    window = period_window(row, period)
    ends = parse(window.end)
    last = monthrange(ends.year, ends.month)[1]
    return show(date(ends.year, ends.month, min(pay_day, last)))
