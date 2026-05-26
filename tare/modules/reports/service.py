"""Reports, gathered from what the other areas already hold."""

from __future__ import annotations

from tare.common.store import Store
from tare.common.types import Operator
from tare.modules.employers.service import EmployersService
from tare.modules.reports.rules import (
    by_period, cost_of_employment, headcount_by_period, owed_to_revenue, paid_out,
)


class ReportsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def wage_bill(self, operator: Operator, employer_id: str) -> dict:
        self.employers.assert_visible(operator, employer_id)
        slips = [row for row in self.store.payslips.all()
                 if row.employer_id == employer_id]
        return {"employer_id": employer_id, "cost": cost_of_employment(slips),
                "revenue": owed_to_revenue(slips), "paid": paid_out(slips),
                "by_period": by_period(slips),
                "headcount_by_period": headcount_by_period(slips)}
