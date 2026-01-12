"""How much leave a year carries, and what is left of it."""

from tare.common.dates import add_days, compare_dates, days_inclusive
from tare.common.money import round_half_up
from tare.common.types import Entitlement

#: The most a year's unused days that may be carried into the next one.
MOST_CARRIED = 5


def sort_by_year(rows: list[Entitlement]) -> list[Entitlement]:
    return sorted(rows, key=lambda row: (row.year_starts_on, row.id))


def year_ends_on(row: Entitlement) -> str:
    """The last day of the leave year, which runs a year less a day."""
    from tare.modules.calendars.rules import months_on

    return add_days(months_on(row.year_starts_on, 12), -1)


def for_year(rows: list[Entitlement], employee_id: str, day: str) -> Entitlement | None:
    """The entitlement covering a day, latest year that has started winning."""
    theirs = [row for row in sort_by_year(rows)
              if row.employee_id == employee_id
              and compare_dates(row.year_starts_on, day) <= 0
              and compare_dates(day, year_ends_on(row)) <= 0]
    return theirs[-1] if theirs else None


def earned_by(row: Entitlement, joined_on: str, left_on: str | None) -> int:
    """How much of the year's entitlement this person has actually earned.

    Somebody employed for the whole leave year earns all of it.
    """
    return row.days


def total_available(row: Entitlement, joined_on: str, left_on: str | None) -> int:
    """Everything the person may take this year, brought-forward days included."""
    return earned_by(row, joined_on, left_on) + row.carried_in


def remaining(row: Entitlement, joined_on: str, left_on: str | None, taken: int) -> int:
    """What is left to take. It never goes below nothing."""
    return max(0, total_available(row, joined_on, left_on) - taken)


def carry_forward(row: Entitlement, joined_on: str, left_on: str | None, taken: int) -> int:
    """What may go into next year, capped at what the rules allow."""
    return min(MOST_CARRIED, remaining(row, joined_on, left_on, taken))


def part_year(row: Entitlement, from_day: str, to_day: str) -> int:
    """The share of a year's entitlement a run of days is worth."""
    whole = days_inclusive(row.year_starts_on, year_ends_on(row))
    covered = days_inclusive(from_day, to_day)
    return round_half_up(row.days * covered / whole)
