"""Reading a run of payslips."""

from tare.common.types import Payslip, PayslipLine


def sort_by_period(rows: list[Payslip]) -> list[Payslip]:
    return sorted(rows, key=lambda row: (row.period, row.employee_id, row.id))


def sort_lines(rows: list[PayslipLine]) -> list[PayslipLine]:
    """Payments first, then deductions, each in element order."""
    return sorted(rows, key=lambda row: (row.kind != "payment", row.element_id))


def year_to_date(rows: list[Payslip], upto_period: int) -> dict[str, int]:
    """Everything paid so far this year, up to and including one period."""
    fields = ("gross", "taxable", "levy", "contributions", "deductions", "net")
    counted = [row for row in rows if row.period <= upto_period]
    return {name: sum(getattr(row, name) for row in counted) for name in fields}


def balances(row: Payslip) -> bool:
    """Whether the payslip's own figures come back to its net."""
    return row.net == max(0, row.gross - row.levy - row.contributions - row.deductions)


def lines_come_to(rows: list[PayslipLine], kind: str) -> int:
    return sum(row.amount for row in rows if row.kind == kind)
