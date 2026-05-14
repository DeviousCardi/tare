"""Adding journal lines up into account balances."""

from dataclasses import dataclass

from tare.common.types import JournalLine


@dataclass(frozen=True)
class AccountBalance:
    """What one nominal account stands at."""

    account: str
    debits: int
    credits: int

    @property
    def balance(self) -> int:
        """Debits less credits. A credit balance reads below nothing."""
        return self.debits - self.credits


def balances_of(rows: list[JournalLine]) -> list[AccountBalance]:
    """One balance per account, in account order."""
    found: dict[str, list[int]] = {}
    for row in rows:
        pair = found.setdefault(row.account, [0, 0])
        pair[0] += row.debit
        pair[1] += row.credit
    return [AccountBalance(account=account, debits=pair[0], credits=pair[1])
            for account, pair in sorted(found.items())]


def balance_of(rows: list[JournalLine], account: str) -> AccountBalance:
    """One account's balance, whether or not anything was posted to it."""
    for found in balances_of(rows):
        if found.account == account:
            return found
    return AccountBalance(account=account, debits=0, credits=0)


def trial_balance(rows: list[JournalLine]) -> bool:
    """Whether the ledger as a whole comes back to nothing."""
    return sum(found.balance for found in balances_of(rows)) == 0
