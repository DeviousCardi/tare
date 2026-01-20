"""What a deduction takes, and what happens when the pay will not stretch."""

from dataclasses import dataclass

from tare.common.money import apply_rate
from tare.common.types import DeductionInstruction

#: How the amount on an instruction reads.
FIXED = "fixed"
SHARE = "share"
BASES = (FIXED, SHARE)


@dataclass(frozen=True)
class Taken:
    """What one instruction actually took, and what it could not."""

    instruction_id: str
    element_id: str
    asked: int
    taken: int

    @property
    def short(self) -> int:
        return self.asked - self.taken


def by_priority(rows: list[DeductionInstruction]) -> list[DeductionInstruction]:
    """Instructions in the order they are taken, earliest instruction breaking ties."""
    return sorted(rows, key=lambda row: (row.priority, row.id))


def due_in(row: DeductionInstruction, period: int, year_starts_on: str) -> bool:
    """Whether the instruction runs in one period of one year."""
    if row.year_starts_on != year_starts_on:
        return False
    if period < row.from_period:
        return False
    return row.to_period is None or period <= row.to_period


def asked_for(row: DeductionInstruction, pay: int) -> int:
    """What the instruction asks for out of a figure of pay."""
    if pay <= 0:
        return 0
    if row.basis == SHARE:
        return apply_rate(pay, row.amount)
    return row.amount


def take_from(
    rows: list[DeductionInstruction], pay: int, held_off: list[str] | None = None,
) -> list[Taken]:
    """Work through the instructions in priority order against what pay there is.

    Each takes what it asks for, or what is left if that is less. Once the pay
    is gone the rest take nothing, and what they could not take is recorded
    rather than forgotten.
    """
    withheld = set(held_off or [])
    left = max(0, pay)
    found: list[Taken] = []
    for row in by_priority(rows):
        if row.element_id in withheld:
            continue
        asked = asked_for(row, pay)
        taken = min(asked, left)
        left -= taken
        found.append(Taken(instruction_id=row.id, element_id=row.element_id,
                           asked=asked, taken=taken))
    return found


def total_taken(taken: list[Taken]) -> int:
    return sum(row.taken for row in taken)


def total_short(taken: list[Taken]) -> int:
    """What the instructions between them could not take."""
    return sum(row.short for row in taken)
