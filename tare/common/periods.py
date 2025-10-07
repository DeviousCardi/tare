"""Pay periods, and the arithmetic of a window that a rule has to divide.

A period is an inclusive window with a name — the month, the week or the
fortnight a run pays for. Nothing here knows what is being paid; it knows how a
window is covered, split and weighted, so a rule that has to apportion across
one does not reinvent the boundary handling and get an end wrong.
"""

from dataclasses import dataclass

from tare.common.dates import compare_dates, days_inclusive, overlaps, within_window
from tare.common.errors import refuse
from tare.common.money import apportion


@dataclass(frozen=True)
class Window:
    """An inclusive span of days."""

    start: str
    end: str

    def __post_init__(self) -> None:
        if compare_dates(self.start, self.end) > 0:
            raise refuse(f"window {self.start}..{self.end} ends before it starts")


def days_in(window: Window) -> int:
    """How many days the window covers, counting both ends."""
    return days_inclusive(window.start, window.end)


def covers(window: Window, day: str) -> bool:
    return within_window(day, window.start, window.end)


def touches(window: Window, other: Window) -> bool:
    return overlaps(window.start, window.end, other.start, other.end)


def common_days(window: Window, other: Window) -> int:
    """How many days the two windows share. None shared is nothing, not a refusal."""
    if not touches(window, other):
        return 0
    start = window.start if compare_dates(window.start, other.start) >= 0 else other.start
    end = window.end if compare_dates(window.end, other.end) <= 0 else other.end
    return days_inclusive(start, end)


def split_at(window: Window, day: str) -> tuple[Window, Window]:
    """Cut the window so that `day` opens the second part.

    The day named starts the later part, never ends the earlier one — which is
    the reading every other window in the service uses. Cutting on a day the
    window does not cover is refused rather than handing back an empty half.
    """
    if not covers(window, day):
        raise refuse(f"{day} is not inside window {window.start}..{window.end}")
    if day == window.start:
        raise refuse(f"cutting at {day} would leave nothing before it")
    from tare.common.dates import add_days

    return Window(window.start, add_days(day, -1)), Window(day, window.end)


def weighted(amount: int, windows: list[Window]) -> list[int]:
    """Split `amount` across the windows in proportion to the days each covers.

    Whole minor units that sum back to `amount`, because it is the same
    largest-remainder rule the rest of the service splits money with.
    """
    if not windows:
        raise refuse("cannot weight a figure across no windows")
    return apportion(amount, [days_in(window) for window in windows])
