"""Routes for validation."""

from fastapi import APIRouter

from tare.common.deps import TheOperator, TheStore
from tare.modules.validation.schemas import CheckOut
from tare.modules.validation.service import ValidationService

router = APIRouter(prefix="/validation", tags=["validation"])


@router.get("/{run_id}")
def check_run(run_id: str, operator: TheOperator, store: TheStore) -> CheckOut:
    return CheckOut(**ValidationService(store).check(operator, run_id))


@router.get("/{run_id}/summary")
def check_summary(run_id: str, operator: TheOperator, store: TheStore) -> dict:
    return ValidationService(store).summary(operator, run_id)
