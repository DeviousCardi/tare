"""Routes for net pay."""

from fastapi import APIRouter

from tare.common.deps import TheOperator, TheStore
from tare.modules.net.schemas import NetOut
from tare.modules.net.service import NetService

router = APIRouter(prefix="/net", tags=["net"])


@router.get("/{employee_id}")
def net_for(
    employee_id: str, calendar_id: str, period: int,
    operator: TheOperator, store: TheStore,
) -> NetOut:
    return NetOut(**NetService(store).of(operator, employee_id, calendar_id, period))
