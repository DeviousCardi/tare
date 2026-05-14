"""What comes back when the ledger is read."""

from pydantic import BaseModel


class AccountBalanceOut(BaseModel):
    account: str
    debits: int
    credits: int
    balance: int


class LedgerOut(BaseModel):
    employer_id: str
    accounts: list[AccountBalanceOut]
    balances: bool
