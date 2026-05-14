"""Routes for the ledger."""

from fastapi import APIRouter

from tare.common.deps import TheOperator, TheStore
from tare.modules.ledger.schemas import AccountBalanceOut, LedgerOut
from tare.modules.ledger.service import LedgerService

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/{employer_id}")
def ledger_of(employer_id: str, operator: TheOperator, store: TheStore) -> LedgerOut:
    return LedgerOut(**LedgerService(store).of(operator, employer_id))


@router.get("/{employer_id}/account/{account}")
def ledger_account(
    employer_id: str, account: str, operator: TheOperator, store: TheStore,
) -> AccountBalanceOut:
    return AccountBalanceOut(**LedgerService(store).account(operator, employer_id, account))
