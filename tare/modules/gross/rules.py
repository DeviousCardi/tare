"""Building the payment side of a payslip.

Nothing here reads the store. It takes what the areas around it hand over —
a contract, a run of rates, a run of approved hours — and says what the
payments come to, so the arithmetic can be checked without building a payroll.
"""

from dataclasses import dataclass

from tare.common.money import round_half_up
from tare.modules.elements.rules import Entry
from tare.modules.rates.rules import amount_for, is_hours_based

#: How many periods of each frequency there are in a year.
PERIODS_A_YEAR = {"weekly": 52, "fortnightly": 26, "monthly": 12}


@dataclass(frozen=True)
class Piece:
    """One thing being paid: an element, the hours behind it, and the rate."""

    element_id: str
    hours: int
    rate: object


def periodic(annual: int, frequency: str) -> int:
    """What a year's figure comes to in one period of that frequency."""
    return round_half_up(annual / PERIODS_A_YEAR[frequency])


def piece_amount(piece: Piece, hourly_pay: int) -> int:
    """What one piece comes to."""
    hours = piece.hours if is_hours_based(piece.rate) else 0
    return amount_for(piece.rate, hours, hourly_pay)


def entries_for(pieces: list[Piece], hourly_pay: int) -> list[Entry]:
    """The payslip entries a run of pieces makes, in element order."""
    found = [Entry(element_id=piece.element_id,
                   amount=piece_amount(piece, hourly_pay))
             for piece in pieces]
    return sorted(found, key=lambda entry: entry.element_id)


def combine(entries: list[Entry]) -> list[Entry]:
    """Fold entries against the same element into one line each."""
    totals: dict[str, int] = {}
    for entry in entries:
        totals[entry.element_id] = totals.get(entry.element_id, 0) + entry.amount
    return [Entry(element_id=element_id, amount=amount)
            for element_id, amount in sorted(totals.items())]
