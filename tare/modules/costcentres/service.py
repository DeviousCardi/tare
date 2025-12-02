"""Cost centres, and spreading a figure over them."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import CostCentre, Operator
from tare.modules.costcentres.rules import bookable, in_department, share_across, sort_by_code
from tare.modules.costcentres.schemas import (
    CloseCostCentre, ListCostCentres, OpenCostCentre,
)
from tare.modules.departments.service import DepartmentsService
from tare.modules.employers.service import EmployersService


class CostCentresService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)
        self.departments = DepartmentsService(store)

    def list(self, operator: Operator, query: ListCostCentres) -> dict:
        rows = visible_to(operator, self.store.cost_centres.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.department_id:
            self.departments.get(operator, query.department_id)
            rows = in_department(rows, query.department_id)
        if query.bookable_only:
            rows = bookable(rows)
        return page(sort_by_code(rows), query.limit, query.offset)

    def get(self, operator: Operator, cost_centre_id: str) -> CostCentre:
        row = self.store.cost_centres.find(cost_centre_id)
        if not row:
            raise not_found("cost centre", cost_centre_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def open(self, operator: Operator, dto: OpenCostCentre) -> CostCentre:
        self.employers.assert_visible(operator, dto.employer_id)
        if self.store.cost_centres.first(
                lambda row: row.employer_id == dto.employer_id and row.code == dto.code):
            raise conflict(f"cost centre {dto.code} already exists")
        if dto.department_id:
            department = self.departments.get(operator, dto.department_id)
            if department.employer_id != dto.employer_id:
                raise refuse("a cost centre cannot sit in another employer's department")
        return self.store.cost_centres.insert(CostCentre(
            id="", employer_id=dto.employer_id, code=dto.code, name=dto.name,
            department_id=dto.department_id, closed=False))

    def close(
        self, operator: Operator, cost_centre_id: str, dto: CloseCostCentre,
    ) -> CostCentre:
        row = self.get(operator, cost_centre_id)
        if row.closed and dto.closed:
            raise conflict(f"cost centre {row.code} is already closed")
        return self.store.cost_centres.update(row.id, closed=dto.closed)

    def spread(self, operator: Operator, amount: int, centres: list[str],
               weights: list[int]) -> dict:
        if len(centres) != len(weights):
            raise refuse("every centre a cost is spread over needs a weight")
        for centre_id in centres:
            row = self.get(operator, centre_id)
            if row.closed:
                raise refuse(f"cost centre {row.code} is closed and cannot take a cost")
        return {"amount": amount, "shares": share_across(amount, weights)}
