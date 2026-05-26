"""Routes for reports."""

from fastapi import APIRouter

from tare.common.deps import TheOperator, TheStore
from tare.modules.reports.schemas import WageBillOut
from tare.modules.reports.service import ReportsService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/wage-bill/{employer_id}")
def wage_bill(employer_id: str, operator: TheOperator, store: TheStore) -> WageBillOut:
    return WageBillOut(**ReportsService(store).wage_bill(operator, employer_id))
