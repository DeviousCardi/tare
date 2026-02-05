"""Routes for registers."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.registers.schemas import RegisterOut
from tare.modules.registers.service import RegistersService

router = APIRouter(prefix="/registers", tags=["registers"])


@router.get("/{run_id}")
def register_for(
    run_id: str, operator: TheOperator, store: TheStore,
    grouped_by: str = Query(default="employee"),
) -> RegisterOut:
    return RegisterOut(**RegistersService(store).of(operator, run_id, grouped_by))
