"""What pay carries through the bands, worked out on its own."""

from tare.common.effective import in_force_on, sort_by_effective
from tare.common.money import apply_rate
from tare.common.types import Band


def sort_by_floor(rows: list[Band]) -> list[Band]:
    """Bands lowest first, which is the order pay climbs through them."""
    return sorted(rows, key=lambda row: row.from_pay)


def bands_for(rows: list[Band], letter: str, day: str) -> list[Band]:
    """Every band of one letter that was in force on a day.

    Bands are published as a set: each floor is its own row and a change
    republishes all of them from the same date, so the set in force is the
    latest date that had already taken effect.
    """
    mine = [row for row in rows if row.letter == letter]
    if not mine:
        return []
    latest = in_force_on(sort_by_effective(mine), day)
    if latest is None:
        return []
    return sort_by_floor([row for row in mine
                          if row.effective_from == latest.effective_from])


def width_of(band: Band, pay: int) -> int:
    """How much of `pay` falls inside this band. Both bounds count."""
    if pay < band.from_pay:
        return 0
    top = band.to_pay
    reached = pay if top is None or pay < top else top
    return reached - band.from_pay + 1


def contribution_on(pay: int, bands: list[Band]) -> int:
    """What a figure of pay carries in contributions, band by band.

    Each band charges its own rate on the part of the pay that falls inside it,
    and the parts are added up. A figure below the first floor carries nothing.
    """
    carried = 0
    for band in sort_by_floor(bands):
        if band.to_pay is None:
            continue
        inside = width_of(band, pay)
        if inside > 0:
            carried += apply_rate(inside, band.rate_basis_points)
    return carried


def band_holding(pay: int, bands: list[Band]) -> Band | None:
    """The band a figure of pay reaches, which is the one its top penny is in."""
    for band in reversed(sort_by_floor(bands)):
        if pay >= band.from_pay:
            return band
    return None
