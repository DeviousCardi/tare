"""What a run of miles is worth at the approved rates.

The Revenue publishes two rates: a higher one for the first stretch of miles a
person does in a year, and a lower one after that. The rates and the stretch
are the bureau's own and live here.
"""

from tare.common.dates import within_window
from tare.common.money import round_half_up
from tare.common.types import Journey

#: Pennies a mile, and where the higher rate runs out.
HIGHER_RATE = 45
LOWER_RATE = 25
HIGHER_MILES = 10000


def sort_by_travelled(rows: list[Journey]) -> list[Journey]:
    return sorted(rows, key=lambda row: (row.travelled_on, row.id))


def approved_only(rows: list[Journey]) -> list[Journey]:
    return [row for row in rows if row.approved]


def between(rows: list[Journey], start: str, end: str) -> list[Journey]:
    """Journeys made in a window. Both ends count."""
    return sort_by_travelled([row for row in rows
                              if within_window(row.travelled_on, start, end)])


def miles_in(rows: list[Journey], start: str, end: str) -> int:
    """Approved miles across a window."""
    return sum(row.miles for row in approved_only(between(rows, start, end)))


def worth_of(miles: int, already: int = 0) -> int:
    """What a run of miles is worth, given how many were already done this year.

    The higher rate runs out after the first stretch of miles in the year, and
    everything past it is worth the lower one.
    """
    if miles <= 0:
        return 0
    if already + miles > HIGHER_MILES:
        return round_half_up(miles * LOWER_RATE)
    return round_half_up(miles * HIGHER_RATE)
