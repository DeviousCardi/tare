"""Benefit classes, and what they are worth."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import BenefitClass, Operator
from tare.modules.employers.service import EmployersService
from tare.modules.valuations.rules import BASES, for_days, for_window, sort_by_code
from tare.modules.valuations.schemas import DefineClass, ListClasses, RevalueClass


class ValuationsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def list(self, operator: Operator, query: ListClasses) -> dict:
        rows = visible_to(operator, self.store.benefit_classes.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        return page(sort_by_code(rows), query.limit, query.offset)

    def get(self, operator: Operator, class_id: str) -> BenefitClass:
        row = self.store.benefit_classes.find(class_id)
        if not row:
            raise not_found("benefit class", class_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def define(self, operator: Operator, dto: DefineClass) -> BenefitClass:
        self.employers.assert_visible(operator, dto.employer_id)
        if dto.basis not in BASES:
            raise refuse(f"{dto.basis} is not a basis a benefit is valued on")
        if self.store.benefit_classes.first(
                lambda row: row.employer_id == dto.employer_id and row.code == dto.code):
            raise conflict(f"benefit class {dto.code} already exists")
        return self.store.benefit_classes.insert(BenefitClass(
            id="", employer_id=dto.employer_id, code=dto.code, name=dto.name,
            basis=dto.basis, annual_value=dto.annual_value))

    def revalue(
        self, operator: Operator, class_id: str, dto: RevalueClass,
    ) -> BenefitClass:
        row = self.get(operator, class_id)
        return self.store.benefit_classes.update(row.id, annual_value=dto.annual_value)

    def worth(self, operator: Operator, class_id: str, days: int) -> dict:
        row = self.get(operator, class_id)
        return {"class_id": row.id, "days": days, "worth": for_days(row, days)}

    def worth_over(self, operator: Operator, class_id: str, start: str, end: str) -> int:
        return for_window(self.get(operator, class_id), start, end)
