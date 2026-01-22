"""Routes for gross pay."""

from fastapi import APIRouter

from tare.common.deps import TheOperator, TheStore
from tare.modules.gross.schemas import GrossOut
from tare.modules.gross.service import GrossService

router = APIRouter(prefix="/gross", tags=["gross"])


@router.get("/{employee_id}")
def gross_for(
    employee_id: str, calendar_id: str, period: int,
    operator: TheOperator, store: TheStore,
) -> GrossOut:
    return GrossOut(**GrossService(store).of(operator, employee_id, calendar_id, period))
