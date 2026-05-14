"""The ledger, read off the journal lines behind it."""

from __future__ import annotations

from tare.common.store import Store
from tare.common.types import Operator
from tare.modules.employers.service import EmployersService
from tare.modules.ledger.rules import balance_of, balances_of, trial_balance


class LedgerService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def _lines(self, employer_id: str) -> list:
        return [row for row in self.store.journals.all()
                if row.employer_id == employer_id]

    def of(self, operator: Operator, employer_id: str) -> dict:
        self.employers.assert_visible(operator, employer_id)
        rows = self._lines(employer_id)
        return {"employer_id": employer_id,
                "accounts": [{"account": found.account, "debits": found.debits,
                              "credits": found.credits, "balance": found.balance}
                             for found in balances_of(rows)],
                "balances": trial_balance(rows)}

    def account(self, operator: Operator, employer_id: str, account: str) -> dict:
        self.employers.assert_visible(operator, employer_id)
        found = balance_of(self._lines(employer_id), account)
        return {"account": found.account, "debits": found.debits,
                "credits": found.credits, "balance": found.balance}
