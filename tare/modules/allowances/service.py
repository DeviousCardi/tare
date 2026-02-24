"""Allowances, and what somebody is on."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Allowance, Operator
from tare.modules.allowances.rules import (
    by_element, comes_to, sort_by_start, standing_for, stands_on,
)
from tare.modules.allowances.schemas import (
    AwardAllowance, EndAllowance, ListAllowances,
)
from tare.modules.elements.service import ElementsService
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day


class AllowancesService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.elements = ElementsService(store)

    def list(self, operator: Operator, query: ListAllowances) -> dict:
        rows = visible_to(operator, self.store.allowances.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.element_id:
            rows = [row for row in rows if row.element_id == query.element_id]
        if query.standing_on:
            day = a_day(query.standing_on, "standing_on")
            rows = [row for row in rows if stands_on(row, day)]
        return page(sort_by_start(rows), query.limit, query.offset)

    def get(self, operator: Operator, allowance_id: str) -> Allowance:
        row = self.store.allowances.find(allowance_id)
        if not row:
            raise not_found("allowance", allowance_id)
        self.employees.get(operator, row.employee_id)
        return row

    def award(self, operator: Operator, dto: AwardAllowance) -> Allowance:
        person = self.employees.get(operator, dto.employee_id)
        element = self.elements.get(operator, dto.element_id)
        if element.kind != "payment":
            raise refuse("an allowance must be paid as a payment element")
        if element.employer_id != person.employer_id:
            raise refuse("an allowance must name an element of the person's own employer")
        starts_on = a_day(dto.starts_on, "starts_on")
        ends_on = a_day(dto.ends_on, "ends_on") if dto.ends_on else None
        if ends_on and compare_dates(ends_on, starts_on) < 0:
            raise refuse("an allowance cannot end before it starts")
        clash = self.store.allowances.first(
            lambda row: row.employee_id == person.id
            and row.element_id == dto.element_id and stands_on(row, starts_on))
        if clash:
            raise conflict(
                f"{person.reference} already has {element.code} on {starts_on}")
        return self.store.allowances.insert(Allowance(
            id="", employee_id=person.id, employer_id=person.employer_id,
            element_id=dto.element_id, amount=dto.amount, starts_on=starts_on,
            ends_on=ends_on))

    def end(self, operator: Operator, allowance_id: str, dto: EndAllowance) -> Allowance:
        row = self.get(operator, allowance_id)
        ends_on = a_day(dto.ends_on, "ends_on")
        if row.ends_on is not None:
            raise conflict("that allowance has already ended")
        if compare_dates(ends_on, row.starts_on) < 0:
            raise refuse("an allowance cannot end before it starts")
        return self.store.allowances.update(row.id, ends_on=ends_on)

    def standing(self, operator: Operator, employee_id: str, day: str) -> dict:
        self.employees.get(operator, employee_id)
        found = standing_for(self.store.allowances.all(), employee_id, a_day(day, "day"))
        return {"employee_id": employee_id, "on": day, "allowances": found,
                "comes_to": comes_to(found), "by_element": by_element(found)}
