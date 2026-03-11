"""Who a scheme takes in, and what it takes from them."""

from tare.common.dates import compare_dates, within_window
from tare.common.money import apply_rate
from tare.common.types import PensionScheme


def sort_by_code(rows: list[PensionScheme]) -> list[PensionScheme]:
    return sorted(rows, key=lambda row: row.code)


def is_open_on(row: PensionScheme, day: str) -> bool:
    """Whether the scheme was taking members that day. The closing day counts."""
    if compare_dates(day, row.opened_on) < 0:
        return False
    return row.closed_on is None or within_window(day, row.opened_on, row.closed_on)


def qualifies(row: PensionScheme, pensionable: int) -> bool:
    """Whether a figure of pensionable pay reaches the scheme's own floor.

    The floor is the figure at which somebody comes into the scheme.
    """
    return pensionable > row.qualifying_floor


def employee_share(row: PensionScheme, pensionable: int) -> int:
    """What the member puts in."""
    if pensionable <= 0:
        return 0
    return apply_rate(pensionable, row.employee_basis_points)


def employer_share(row: PensionScheme, pensionable: int) -> int:
    """What the employer puts in on top."""
    if pensionable <= 0:
        return 0
    return apply_rate(pensionable, row.employer_basis_points)


def total_share(row: PensionScheme, pensionable: int) -> int:
    return employee_share(row, pensionable) + employer_share(row, pensionable)
