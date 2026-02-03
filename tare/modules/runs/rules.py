"""What state a run is in, and what it came to."""

from tare.common.types import Payslip, PayrollRun

#: What a run can be.
DRAFT = "draft"
COMMITTED = "committed"
ABANDONED = "abandoned"
STATUSES = (DRAFT, COMMITTED, ABANDONED)


def sort_by_period(rows: list[PayrollRun]) -> list[PayrollRun]:
    return sorted(rows, key=lambda row: (row.period, row.id))


def is_open(row: PayrollRun) -> bool:
    """A run nobody has committed or abandoned yet."""
    return row.status == DRAFT


def is_committed(row: PayrollRun) -> bool:
    return row.status == COMMITTED


def run_total(rows: list[Payslip]) -> int:
    """What a run comes to: the sum of the net figures on its payslips."""
    return sum(max(0, row.net) for row in rows)


def gross_total(rows: list[Payslip]) -> int:
    return sum(row.gross for row in rows)


def revenue_total(rows: list[Payslip]) -> int:
    """What the run owes the Revenue between the levy and contributions."""
    return sum(row.levy + row.contributions for row in rows)


def headcount(rows: list[Payslip]) -> int:
    """How many people the run paid, counting each once."""
    return len({row.employee_id for row in rows})
