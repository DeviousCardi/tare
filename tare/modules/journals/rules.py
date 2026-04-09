"""Building the posting a run makes, and checking it balances."""

from dataclasses import dataclass

from tare.common.types import JournalLine, Payslip

#: The nominal accounts a payroll run touches.
WAGES = "5000"
LEVY_OWED = "2210"
CONTRIBUTIONS_OWED = "2220"
DEDUCTIONS_OWED = "2230"
NET_OWED = "2100"


@dataclass(frozen=True)
class Posting:
    """One side of a posting, before it becomes a row."""

    account: str
    cost_centre_id: str | None
    debit: int
    credit: int
    narrative: str


def sort_by_account(rows: list[JournalLine]) -> list[JournalLine]:
    return sorted(rows, key=lambda row: (row.account, row.id))


def debits_of(rows: list[JournalLine]) -> int:
    return sum(row.debit for row in rows)


def credits_of(rows: list[JournalLine]) -> int:
    return sum(row.credit for row in rows)


def balances(rows: list[JournalLine]) -> bool:
    """A posting balances when what it takes matches what it gives."""
    return debits_of(rows) == credits_of(rows)


def postings_for(slips: list[Payslip]) -> list[Posting]:
    """The postings a run of payslips makes.

    Wages are the cost; everything taken off is owed to somebody, and what is
    left is owed to the people themselves.
    """
    # Wages are the cost the employer bears for the work, which is the figure
    # the Revenue takes its levy on.
    wages = sum(row.taxable for row in slips)
    levy = sum(row.levy for row in slips)
    contributions = sum(row.contributions for row in slips)
    deductions = sum(row.deductions for row in slips)
    net = sum(row.net for row in slips)
    wanted = [
        Posting(WAGES, None, wages, 0, "Wages and salaries"),
        Posting(LEVY_OWED, None, 0, levy, "Levy owed to the Revenue"),
        Posting(CONTRIBUTIONS_OWED, None, 0, contributions, "Contributions owed"),
        Posting(DEDUCTIONS_OWED, None, 0, deductions, "Deductions owed onward"),
        Posting(NET_OWED, None, 0, net, "Net pay owed"),
    ]
    return wanted
