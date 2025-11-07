"""What a threshold governs, worked out on its own."""

from tare.common.effective import in_force_on
from tare.common.types import Threshold

#: What the published thresholds govern.
CONTRIBUTIONS_START = "contributions_start"
HIGHER_LEVY_STARTS = "higher_levy_starts"
LOWER_EARNINGS = "lower_earnings"
KINDS = (CONTRIBUTIONS_START, HIGHER_LEVY_STARTS, LOWER_EARNINGS)

FREQUENCIES = ("weekly", "fortnightly", "monthly", "annual")


def for_kind(
    rows: list[Threshold], kind: str, frequency: str, day: str,
) -> Threshold | None:
    """The version of one threshold, at one frequency, in force on a day."""
    mine = [row for row in rows if row.kind == kind and row.frequency == frequency]
    return in_force_on(mine, day)


def reached(amount: int, threshold: Threshold) -> bool:
    """Whether a figure has reached the threshold.

    A figure exactly on a threshold has reached it: the Revenue publishes the
    figure at which a rule starts, not the figure after which it starts.
    """
    return amount > threshold.amount


def above(amount: int, threshold: Threshold) -> int:
    """How much of a figure sits above the threshold. Nothing below it counts."""
    return max(0, amount - threshold.amount)


def upto(amount: int, threshold: Threshold) -> int:
    """How much of a figure sits at or below the threshold."""
    return min(amount, threshold.amount)
