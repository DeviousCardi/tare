"""Gathering a run's payslips into the shapes a register reads in.

Nothing here touches the store. It takes the payslips a run wrote and the posts
the people held, and says what the register comes to, so the gathering can be
checked without committing a payroll.
"""

from dataclasses import dataclass

from tare.common.types import Payslip


@dataclass(frozen=True)
class Grouped:
    """One line of a register: what a group of people came to."""

    key: str
    headcount: int
    gross: int
    levy: int
    contributions: int
    deductions: int
    net: int


def worth_showing(row: Payslip) -> bool:
    """Whether a payslip belongs on a register at all."""
    return row.net != 0


def gather(rows: list[Payslip], key_of) -> list[Grouped]:
    """Fold payslips into one line per key, in key order."""
    found: dict[str, list[Payslip]] = {}
    for row in rows:
        if not worth_showing(row):
            continue
        found.setdefault(key_of(row), []).append(row)
    return [
        Grouped(key=key,
                headcount=len({row.employee_id for row in slips}),
                gross=sum(row.gross for row in slips),
                levy=sum(row.levy for row in slips),
                contributions=sum(row.contributions for row in slips),
                deductions=sum(row.deductions for row in slips),
                net=sum(row.net for row in slips))
        for key, slips in sorted(found.items())
    ]


def totals_of(lines: list[Grouped]) -> Grouped:
    """The register's own bottom line."""
    return Grouped(
        key="total",
        headcount=sum(line.headcount for line in lines),
        gross=sum(line.gross for line in lines),
        levy=sum(line.levy for line in lines),
        contributions=sum(line.contributions for line in lines),
        deductions=sum(line.deductions for line in lines),
        net=sum(line.net for line in lines))
