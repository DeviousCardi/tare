"""Building a year's statement, and checking it against the payslips."""

from tare.common.types import Payslip, YearEndStatement


def sort_by_year(rows: list[YearEndStatement]) -> list[YearEndStatement]:
    return sorted(rows, key=lambda row: (row.year_starts_on, row.employee_id, row.id))


def is_issued(row: YearEndStatement) -> bool:
    return row.issued_on is not None


def totals_from(slips: list[Payslip]) -> dict[str, int]:
    """What a run of payslips comes to across the year."""
    return {name: sum(getattr(row, name) for row in slips)
            for name in ("gross", "levy", "contributions", "net")}


def agrees_with(row: YearEndStatement, slips: list[Payslip]) -> bool:
    """Whether the statement still matches the payslips behind it."""
    totals = totals_from(slips)
    return all(getattr(row, name) == value for name, value in totals.items())


def take_home_share(row: YearEndStatement) -> int:
    """What share of the year's gross was actually paid, in basis points."""
    if row.gross <= 0:
        return 0
    return round(row.net * 10000 / row.gross)
